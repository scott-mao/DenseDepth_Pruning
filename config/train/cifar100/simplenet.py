# -*- coding: utf-8 -*-
"""Configurations for training as baseline.

- Author: Curt-Park
- Email: jwpark@jmarple.ai
"""

import os

config = {
    "SEED": 777,
    "AUG_TRAIN": "simple_augment_train_mnist",
    "AUG_TEST": "simple_augment_test_mnist",
    "DATASET": "MNIST",
    "MODEL_NAME": "heejung",
    "MODEL_PARAMS": dict(num_classes=10),
    "CRITERION": "CrossEntropy",
    "CRITERION_PARAMS": dict(num_classes=10),
    "LR_SCHEDULER": "WarmupCosineLR",
    "LR_SCHEDULER_PARAMS": dict(warmup_epochs=3, start_lr=1e-3),
    "BATCH_SIZE": 64,
    "LR": 0.1,
    "MOMENTUM": 0.9,
    "WEIGHT_DECAY": 1e-4,
    "NESTEROV": True,
    "EPOCHS": 5,
    "N_WORKERS": os.cpu_count(),
}
