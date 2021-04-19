# -*- coding: utf-8 -*-
"""Configurations for training micronet (cifar100).

- Author: Curt-Park
- Email: jwpark@jmarple.ai
"""

import os

config = {
    "SEED": 777,
    "AUG_TRAIN": "randaugment_train_cifar100",
    "AUG_TRAIN_PARAMS": dict(n_select=2, level=None),
    "AUG_TEST": "simple_augment_test_cifar100",
    "CUTMIX": dict(beta=1.0, prob=0.5),
    "DATASET": "CIFAR100",
    "MODEL_NAME": "mixnet",
    "MODEL_PARAMS": dict(num_classes=100, model_type="MICRONET", dataset="CIFAR100"),
    "CRITERION": "CrossEntropy",
    "CRITERION_PARAMS": dict(num_classes=100, label_smoothing=0.1),
    "LR_SCHEDULER": "WarmupCosineLR",
    "LR_SCHEDULER_PARAMS": dict(
        warmup_epochs=10, start_lr=1e-3, min_lr=1e-4, n_rewinding=1, decay=0.0
    ),
    "BATCH_SIZE": 32,
    "LR": 0.1,
    "MOMENTUM": 0.9,
    "WEIGHT_DECAY": 1e-5,
    "NESTEROV": True,
    "EPOCHS": 600,
    "N_WORKERS": os.cpu_count(),
}
