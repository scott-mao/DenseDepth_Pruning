# -*- coding: utf-8 -*-
"""Quantizer for trained models.

- Author: Curt-Park
- Email: jwpark@jmarple.ai
"""


import os
from typing import Any, Dict

import torch
import torch.nn as nn
import torch.quantization

from src.models import utils as model_utils
from src.runners.runner import Runner
from src.runners.trainer import Trainer
import src.utils as utils

logger = utils.get_logger()


def print_datatypes(model: nn.Module, model_name: str, sep: str = "\n") -> None:
    """Print all datatypes in the model."""
    log = model_name + "'s datatypes:" + sep
    log += sep.join(str(t) for t in model_utils.get_model_tensor_datatype(model))
    logger.info(log)


class Quantizer(Runner):
    """Quantizer for trained models."""

    def __init__(
        self,
        config: Dict[str, Any],
        checkpoint_path: str,
        dir_prefix: str,
        static: bool,
        check_acc: bool,
        backend: str,
        wandb_log: bool,
        wandb_init_params: Dict[str, Any],
    ) -> None:
        """Initialize."""
        super(Quantizer, self).__init__(config, dir_prefix)
        self.mask: Dict[str, torch.Tensor] = dict()
        self.params_pruned = None
        self.check_acc = check_acc
        self.static = static
        self.backend = backend

        # create a trainer
        self.trainer = Trainer(
            config=self.config,
            dir_prefix=dir_prefix,
            checkpt_dir="qat",
            device="cpu",
            wandb_log=wandb_log,
            wandb_init_params=wandb_init_params,
            test_preprocess_hook=self._quantize,
        )

        self.model = self.trainer.model
        self.params_all = model_utils.get_params(
            self.model,
            (
                (nn.Conv2d, "weight"),
                (nn.Conv2d, "bias"),
                (nn.BatchNorm2d, "weight"),
                (nn.BatchNorm2d, "bias"),
                (nn.Linear, "weight"),
                (nn.Linear, "bias"),
            ),
        )

        # initialize the model
        self._init_model(checkpoint_path)

    def run(self, resume_info_path: str = "") -> None:
        """Run quantization."""
        # print_datatypes(self.model, "original model")
        self.trainer.warmup_one_iter()
        orig_model_path = os.path.join(self.dir_prefix, "orig_model.pth")
        torch.save(self.model.state_dict(), orig_model_path)
        size = os.path.getsize(orig_model_path) / 1e6
        logger.info(f"Acc: {self.orig_acc} %\tSize: {size:.6f} MB")

        # fuse the model
        self._prepare()
        # print_datatypes(self.model, "Fused model")

        # post training static quantization
        if self.static:
            logger.info("Post Training Static Quantization: Run calibration")
            self.trainer.warmup_one_iter()
        # quantization-aware training
        else:
            logger.info("Quantization Aware Training: Run training")
            self.trainer.run(resume_info_path)
            self.model.apply(torch.quantization.disable_observer)
            self.model.apply(torch.nn.intrinsic.qat.freeze_bn_stats)
            # load the best model
            self._load_best_model()

        # quantize the model
        quantized_model = self._quantize(self.model)
        
        if self.check_acc:
            with profiler.profile(record_shapes = True) as prof:
                with profiler.record_function("model_inference"):
                    _, acc = self.trainer.test_one_epoch()
            acc = f"{acc['model_acc']:.2f}"
            print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=10))
        else:
            self.trainer.warmup_one_iter()
            acc = "None"
        quantized_model_path = os.path.join(self.dir_prefix, "quantized_model.pth")
        torch.save(quantized_model.state_dict(), quantized_model_path)
        size = os.path.getsize(quantized_model_path) / 1e6
        logger.info(f"Acc: {acc} %\tSize: {size:.6f} MB")

        # script the model
        scripted_model = torch.jit.script(quantized_model)
        # print_datatypes(scripted_model, "Scripted model")
        
        
        if self.check_acc:
            with profiler.profile(record_shapes = True) as prof:
                with profiler.record_function("model_inference"):
                    _, acc = self.trainer.test_one_epoch_model(scripted_model)
            acc = f"{acc['scripted_model_acc']:.2f}"
            print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=10))
        else:
            self.trainer.warmup_one_iter()
            acc = "None"
        scripted_model_path = os.path.join(self.dir_prefix, "scripted_model.pth")
        torch.jit.save(scripted_model, scripted_model_path)
        size = os.path.getsize(scripted_model_path) / 1e6
        logger.info(f"Acc: {acc} %\tSize: {size:.6f} MB")

    def _init_model(self, checkpoint_path: str) -> None:
        """Create a model instance and load weights."""
        # load weights
        logger.info(f"Load weights from the checkpoint {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=torch.device("cpu"))

        state_dict = checkpoint["state_dict"]
        self.orig_acc = checkpoint["test_acc"]

        is_pruned = (
            next((name for name in state_dict if "mask" in name), None) is not None
        )

        if is_pruned:
            logger.info("Dummy prunning to load pruned weights")
            model_utils.dummy_pruning(self.params_all)

        model_utils.initialize_params(self.model, state_dict)
        logger.info("Initialized weights")

        # check the trained model is pruned

        if is_pruned:
            logger.info(
                "Get masks and remove prunning reparameterization for prepare_qat"
            )
            self.mask = model_utils.get_masks(self.model)
            model_utils.remove_pruning_reparameterization(self.params_all)

    def _prepare(self) -> None:
        """Quantize the model."""
        self.model.fuse_model()

        # configuration
        self.model.qconfig = torch.quantization.get_default_qat_qconfig(self.backend)

        # prepare
        if self.static:
            torch.quantization.prepare(self.model, inplace=True)
        else:
            torch.quantization.prepare_qat(self.model, inplace=True)

        # load masks
        self._load_masks()

    def _load_masks(self) -> None:
        """Load masks."""
        if not self.mask:
            return

        model_utils.dummy_pruning(self.params_all)
        for name, _ in self.model.named_buffers():
            if name in self.mask:
                module_name, mask_name = name.rsplit(".", 1)
                module = eval("self.model." + module_name)
                module._buffers[mask_name] = self.mask[name]

    def _load_best_model(self) -> None:
        """Load the trained model with the best accuracy."""
        self.trainer.resume()

    def _quantize(self, model: nn.Module) -> nn.Module:
        """Quantize the trained model."""
        if self.mask:
            model_utils.remove_pruning_reparameterization(self.params_all)

        # check the accuracy after each epoch
        quantized_model = torch.quantization.convert(model.eval(), inplace=False)
        quantized_model.eval()

        # set masks again
        if self.mask:
            self._load_masks()

        return quantized_model
