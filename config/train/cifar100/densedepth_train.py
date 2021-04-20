# -*- coding: utf-8 -*-
"""Configurations for training as baseline.

- Author: Curt-Park
- Email: jwpark@jmarple.ai
"""

import os

config = {
    "SEED": 777,
    "AUG_TRAIN": "simple_augment_train_nyu",
    "AUG_TEST": "simple_augment_test_nyu",
    "DATASET": "",
    "MODEL_NAME": "PTModel",
    "MODEL_PARAMS": None,#dict(num_classes=1664),
    "CRITERION": "Densedepth_loss",
    "CRITERION_PARAMS": dict(num_classes=1),
    "LR_SCHEDULER": "WarmupCosineLR",
    "LR_SCHEDULER_PARAMS": dict(warmup_epochs=0, start_lr=1e-3),
    "BATCH_SIZE": 2,
    "LR": 0.1,
    "MOMENTUM": 0.9,
    "WEIGHT_DECAY": 1e-4,
    "NESTEROV": True,
    "EPOCHS": 1,
    "N_WORKERS": os.cpu_count(),
}
