"""
Hardware control modules for TENG experiments
"""

from .motor_controller import MotorController
from .oscilloscope import OscilloscopeController

__all__ = ['MotorController', 'OscilloscopeController']
