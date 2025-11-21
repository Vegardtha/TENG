"""
Configuration module for TENG experiments
"""

from .experiment_config import (
    ExperimentConfig,
    MotorConfig,
    OscilloscopeConfig,
    quick_test_config,
    standard_experiment_config,
    high_resolution_config,
    endurance_test_config
)

__all__ = [
    'ExperimentConfig',
    'MotorConfig', 
    'OscilloscopeConfig',
    'quick_test_config',
    'standard_experiment_config',
    'high_resolution_config',
    'endurance_test_config'
]
