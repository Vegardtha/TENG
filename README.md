# TENG Experiment Control System

Automated control system for Triboelectric Nanogenerator (TENG) impact testing with synchronized motor control and oscilloscope data acquisition.

## Overview

This system integrates:
- **Arduino-controlled stepper motor** for impact testing
- **Digilent Analog Discovery oscilloscope** for voltage measurements
- **Automated experiment workflow** with data collection and analysis

## Project Structure

```
TENG/
├── run_experiment.py          # Main experiment runner
├── hardware/                  # Hardware control modules
│   ├── motor_controller.py   # Arduino stepper motor interface
│   └── oscilloscope.py       # Digilent oscilloscope interface
├── config/                    # Configuration management
│   └── experiment_config.py  # Experiment settings and presets
├── arduino/                   # Arduino firmware
│   └── main.cpp              # Stepper motor control code
├── experiments/               # Output data directory
├── dwfconstants.py           # Digilent WaveForms constants
└── requirements.txt          # Python dependencies
```

## Hardware Requirements

### 1. Stepper Motor System
- Arduino board (tested with compatible boards)
- Stepper motor driver (connected to pins 7, 8, 9)
- End stop switches (pins 12, 13)
- Auto-trigger input (pin 3)

### 2. Oscilloscope
- Digilent Analog Discovery (or compatible device)
- Digilent WaveForms software installed

## Software Installation

### 1. Install Digilent WaveForms
Download and install from: https://digilent.com/shop/software/digilent-waveforms/

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Upload Arduino Firmware
Upload `arduino/main.cpp` to your Arduino using PlatformIO or Arduino IDE.

### 4. Configure Serial Port
Find your Arduino's serial port:

**macOS:**
```bash
ls /dev/cu.*
```

**Linux:**
```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

**Windows:**
Check Device Manager for COM port number.

Update the port in your configuration (see Usage section).

## Usage

### Quick Start

1. **Connect Hardware:**
   - Connect Arduino via USB
   - Connect Digilent Analog Discovery
   - Ensure motor system is powered and safe

2. **Edit Configuration:**
   Open `run_experiment.py` and update the serial port:
   ```python
   config = ExperimentConfig(
       name="MyTest",
       motor=MotorConfig(
           port="/dev/cu.usbserial-0001",  # YOUR ARDUINO PORT
           num_cycles=5
       )
   )
   ```

3. **Run Experiment:**
   ```bash
   python run_experiment.py
   ```

### Configuration Options

#### Predefined Configurations

```python
from config import quick_test_config, standard_experiment_config, high_resolution_config

# Quick test: 3 cycles
config = quick_test_config()

# Standard: 10 cycles
config = standard_experiment_config()

# High resolution: longer acquisition
config = high_resolution_config()

# Endurance: 100 cycles
config = endurance_test_config()
```

#### Custom Configuration

```python
from config import ExperimentConfig, MotorConfig, OscilloscopeConfig

config = ExperimentConfig(
    name="CustomTest",
    description="My custom experiment",
    
    motor=MotorConfig(
        port="/dev/cu.usbserial-0001",
        num_cycles=10,           # Number of impact cycles
        cycle_delay=0.5          # Additional delay between cycles (s)
    ),
    
    oscilloscope=OscilloscopeConfig(
        sampling_frequency=2e6,  # 2 MHz
        acquisition_time_ms=30,  # 30 ms per acquisition
        amplitude_range=50,      # ±50V range
        trigger_level=0.5,       # Trigger at 0.5V
        trigger_edge="rising"    # Rising edge trigger
    ),
    
    save_plots=True,
    plot_during_acquisition=False
)
```

### Motor Configuration (Arduino)

Motor parameters are configured in the Arduino firmware (`arduino/main.cpp`):

```cpp
#define MAX_SPEED 2000           // Max speed (steps/sec)
#define ACCELERATION 4000        // Acceleration (steps/sec²)
#define SLOW_SPEED 100          // Return speed (steps/sec)
#define SLEEP_TIME 3000         // Delay after cycle (ms)
```

To modify motor behavior (impact speed, dwell time):
1. Edit `arduino/main.cpp`
2. Re-upload firmware to Arduino

## Output Data

Each experiment creates a timestamped folder in `experiments/` containing:

```
experiments/YourExperiment_20231121_143022/
├── experiment_config.txt           # Configuration record
├── cycle_001.csv                   # Raw voltage data (cycle 1)
├── cycle_002.csv                   # Raw voltage data (cycle 2)
├── ...
├── experiment_summary.csv          # Peak voltages per cycle
├── experiment_summary.png          # Statistical plots
└── all_waveforms_overlay.png      # All waveforms overlaid
```

### CSV Format

**Individual cycle files** (`cycle_XXX.csv`):
```csv
Timestamp_ms,Voltage_V
0.0,0.123
0.0005,0.145
...
```

**Summary file** (`experiment_summary.csv`):
```csv
Cycle,Peak_Voltage_V
1,45.2
2,46.1
...
```

## Troubleshooting

### Motor not responding
- Check serial port configuration
- Verify Arduino is connected and powered
- Check end stop switches
- Ensure firmware is uploaded correctly

### Oscilloscope connection failed
- Verify Digilent WaveForms is installed
- Check USB connection
- Try reconnecting the device

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Make sure you're running from the project root directory

### Serial port permission denied (Linux/macOS)
```bash
# Add your user to the dialout group (Linux)
sudo usermod -a -G dialout $USER

# macOS - may need to allow in System Preferences
# System Preferences > Security & Privacy > Privacy
```

## Safety Notes

⚠️ **Important Safety Considerations:**
- Ensure motor system has proper end stops
- Keep clear of moving parts during operation
- Monitor first run carefully
- Emergency stop: Press Ctrl+C or disconnect power

## Advanced Usage

### Using as Library

```python
from hardware import MotorController, OscilloscopeController
from config import ExperimentConfig

# Create custom experiment class
class MyCustomExperiment(TENGExperiment):
    def run_single_acquisition(self, cycle_num):
        # Custom data processing
        data = super().run_single_acquisition(cycle_num)
        # Add your analysis here
        return data
```

### Manual Control

```python
# Motor control only
from hardware import MotorController

with MotorController(port="/dev/cu.usbserial-0001") as motor:
    motor.trigger_impact_cycle()  # Single impact
    motor.move_steps(100)         # Move 100 steps
    motor.home_position()         # Return to home

# Oscilloscope only
from hardware import OscilloscopeController

with OscilloscopeController() as scope:
    scope.configure(sampling_frequency=2e6, amplitude_range=50)
    scope.setup_trigger(trigger_level=0.5)
    data = scope.acquire_single(num_samples=60000)
```

## Contributing

When modifying the system:
1. Test with `quick_test_config()` first (3 cycles)
2. Document changes in configuration
3. Update this README if adding features

## License

Research project - Vegard Haugerud, 2024

## Contact

For questions or issues, contact the project maintainer.
