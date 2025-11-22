"""
TENG Experiment Runner - SIMPLE VERSION
Just configure your experiment settings and run!
"""

from utils import TENGExperiment, find_arduino_port, upload_firmware_with_config
from config import ExperimentConfig, MotorConfig, OscilloscopeConfig


# ============================================================================
# CONFIGURE YOUR EXPERIMENT HERE
# ============================================================================

def main():
    # Auto-detect Arduino port
    print("Searching for Arduino...")
    arduino_port = find_arduino_port()
    
    if not arduino_port:
        print("⚠ Could not auto-detect Arduino port")
        arduino_port = "/dev/cu.usbserial-0001"  # Change this if auto-detect fails
    else:
        print(f"✓ Found Arduino: {arduino_port}\n")
    
    # Configure your experiment
    config = ExperimentConfig(
        name="Testingsaving",
        description="TENG impact testing",
        
        motor=MotorConfig(
            port=arduino_port,          # Auto-detected!
            num_cycles=5,               # How many impacts
            max_speed=4000,             # Impact speed (steps/sec)
            acceleration=4000,          # Acceleration (steps/sec²)
            dwell_time=0,            # Wait at impact position (ms)
            slow_speed=100,             # Return speed (steps/sec)
            sleep_time=3000             # Delay between cycles (ms)
        ),
        
        oscilloscope=OscilloscopeConfig(
            sampling_frequency=2e6,     # 2 MHz
            acquisition_time_ms=30,     # 30 ms recording
            amplitude_range=5,         # ±5V
            trigger_level=0.4           # Start recording at 0.2V
        ),
        
        save_plots=True,
        plot_during_acquisition=False
    )
    
    # OPTIONAL: Upload firmware with these motor settings
    # Uncomment to generate Arduino code and upload before running experiment
    upload_firmware_with_config(config.motor, arduino_board="uno")
    
    # Run the experiment
    print("="*70)
    print("STARTING EXPERIMENT")
    print("="*70)
    print(f"Name: {config.name}")
    print(f"Cycles: {config.motor.num_cycles}")
    print(f"Arduino: {config.motor.port}")
    print("="*70 + "\n")
    
    experiment = TENGExperiment(config)
    experiment.run()


if __name__ == "__main__":
    main()

