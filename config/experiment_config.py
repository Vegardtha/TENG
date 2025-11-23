"""
Experiment Configuration for TENG Testing
Centralized configuration for motor control and oscilloscope settings
"""

from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class MotorConfig:
    """Motor control configuration"""
    # Serial connection
    port: str = "/dev/cu.usbserial-0001"  # Update with your Arduino port
    baudrate: int = 115200
    
    # Experiment parameters
    num_cycles: int = 5  # Number of impact cycles
    cycle_delay: float = 0.0  # Additional delay between cycles (seconds)
    
    # Motor physical settings (will be written to Arduino)
    max_speed: int = 2000          # Maximum speed (steps/sec)
    acceleration: int = 4000       # Acceleration (steps/sec²)
    slow_speed: int = 100          # Return speed (steps/sec)
    dwell_time: int = 1000         # Wait time at impact position (ms)
    sleep_time: int = 3000         # Delay after cycle completes (ms)


@dataclass
class OscilloscopeConfig:
    """Oscilloscope configuration"""
    # Acquisition settings
    sampling_frequency: float = 2e6  # 2 MHz
    acquisition_time_ms: float = 30  # Duration per acquisition (ms)
    
    # Channel settings
    channel: int = 0  # 0 = Channel 1, 1 = Channel 2
    offset: float = 0.0  # Voltage offset (V)
    amplitude_range: float = 50.0  # ±50V range
    
    # Trigger settings
    trigger_channel: int = 0  # Channel to trigger on
    trigger_level: float = 0.5  # Trigger voltage threshold (V)
    trigger_edge: str = "rising"  # "rising" or "falling"


@dataclass
class ExperimentConfig:
    """Complete experiment configuration"""
    # Experiment identification
    name: str = "TENG_Test"
    description: str = "Triboelectric nanogenerator impact testing"
    
    # Hardware configurations
    motor: MotorConfig = None
    oscilloscope: OscilloscopeConfig = None
    
    # Data output
    output_dir: str = "experiments"
    save_plots: bool = True
    plot_during_acquisition: bool = False  # Real-time plotting (slower)
    trim_trailing_zeros: bool = True  # Remove trailing zeros from saved data
    
    def __post_init__(self):
        """Initialize sub-configurations if not provided"""
        if self.motor is None:
            self.motor = MotorConfig()
        if self.oscilloscope is None:
            self.oscilloscope = OscilloscopeConfig()
    
    def get_output_directory(self):
        """
        Create and return timestamped output directory for this experiment
        
        Returns:
            path: Path to the experiment output directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_dir = os.path.join(self.output_dir, f"{self.name}_{timestamp}")
        os.makedirs(exp_dir, exist_ok=True)
        return exp_dir
    
    def save_config_to_file(self, directory):
        """
        Save configuration to a text file for documentation
        
        Parameters:
            directory: Directory to save the config file
        """
        config_path = os.path.join(directory, "experiment_config.txt")
        
        with open(config_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write(f"TENG EXPERIMENT CONFIGURATION\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Experiment: {self.name}\n")
            f.write(f"Description: {self.description}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("-"*70 + "\n")
            f.write("MOTOR SETTINGS\n")
            f.write("-"*70 + "\n")
            f.write(f"Serial Port: {self.motor.port}\n")
            f.write(f"Baudrate: {self.motor.baudrate}\n")
            f.write(f"Number of Cycles: {self.motor.num_cycles}\n")
            f.write(f"Cycle Delay: {self.motor.cycle_delay} s\n\n")
            
            f.write("-"*70 + "\n")
            f.write("OSCILLOSCOPE SETTINGS\n")
            f.write("-"*70 + "\n")
            f.write(f"Sampling Frequency: {self.oscilloscope.sampling_frequency/1e6:.1f} MHz\n")
            f.write(f"Acquisition Time: {self.oscilloscope.acquisition_time_ms} ms\n")
            f.write(f"Channel: {self.oscilloscope.channel + 1}\n")
            f.write(f"Voltage Range: ±{self.oscilloscope.amplitude_range} V\n")
            f.write(f"Voltage Offset: {self.oscilloscope.offset} V\n")
            f.write(f"Trigger Channel: {self.oscilloscope.trigger_channel + 1}\n")
            f.write(f"Trigger Level: {self.oscilloscope.trigger_level} V\n")
            f.write(f"Trigger Edge: {self.oscilloscope.trigger_edge}\n\n")
            
            f.write("-"*70 + "\n")
            f.write("DATA OUTPUT\n")
            f.write("-"*70 + "\n")
            f.write(f"Output Directory: {directory}\n")
            f.write(f"Save Plots: {self.save_plots}\n")
            f.write(f"Real-time Plotting: {self.plot_during_acquisition}\n")
            
        print(f"✓ Configuration saved to: {config_path}")
    
    def __str__(self):
        """String representation for printing"""
        return (
            f"Experiment: {self.name}\n"
            f"Cycles: {self.motor.num_cycles}\n"
            f"Sampling: {self.oscilloscope.sampling_frequency/1e6:.1f} MHz\n"
            f"Acquisition: {self.oscilloscope.acquisition_time_ms} ms\n"
            f"Voltage Range: ±{self.oscilloscope.amplitude_range} V"
        )

