"""
Simple script to run oscilloscope acquisitions using the adjustet_digilent_test module.
This is the clean file you run - it imports all functions from the module.
"""

import adjustet_digilent_test as osc
import serial

# Optional: Connect to Arduino serial port
# Uncomment and adjust the port if you're using Arduino
# ser = serial.Serial("COM4", 115200)  # Windows
# ser = serial.Serial("/dev/ttyUSB0", 115200)  # Linux
# ser = serial.Serial("/dev/cu.usbserial-XXXX", 115200)  # macOS
# ser.flush()
ser = None  # Set to None if not using Arduino

# Run the complete acquisition workflow
osc.run_acquisitions(
    num_acquisitions=5,           # Number of measurements to take
    acquisition_time_ms=30,       # Duration of each measurement (ms)
    sampling_freq=2e6,            # Sampling frequency (2 MHz)
    trigger_level=0.5,            # Trigger voltage level (V)
    trigger_channel=0,            # Channel 1 (0-indexed)
    offset=0,                     # Voltage offset (V)
    amplitude_range=50,           # Voltage range (±50V)
    ser=ser,                      # Serial connection for Arduino (or None)
    output_dir="PrimTest"         # Directory to save CSV files
)

# Close serial connection if used
if ser is not None:
    ser.close()

print("\nExperiment complete!")
