import time
import numpy as np
import csv
import matplotlib.pyplot as plt
from dwfconstants import *
import ctypes
from sys import platform, path 
from os import sep
import serial
import pandas as pd
import dwfconstants as constants

# Load the DWF library based on platform
def _initialize_dwf_library():
    """Load the DWF library based on the current platform"""
    if platform.startswith("win"):
        # on Windows
        return ctypes.cdll.dwf
    elif platform.startswith("darwin"):
        # on macOS - try multiple possible locations
        possible_paths = [
            "/Applications/WaveForms.app/Contents/Frameworks/dwf.framework/dwf",
            "/Library/Frameworks/dwf.framework/dwf",
            sep + "Library" + sep + "Frameworks" + sep + "dwf.framework" + sep + "dwf"
        ]
        
        for lib_path in possible_paths:
            try:
                return ctypes.cdll.LoadLibrary(lib_path)
            except OSError:
                continue
        
        # If none of the paths work, raise an error with helpful message
        raise OSError(
            "Could not find dwf.framework. Please install Digilent WaveForms from:\n"
            "https://digilent.com/shop/software/digilent-waveforms/\n"
            f"Searched locations: {possible_paths}"
        )
    else:
        # on Linux
        return ctypes.cdll.LoadLibrary("libdwf.so")

dwf = _initialize_dwf_library()

class DeviceData:
    """
        stores the device handle and the device name
    """
    def __init__(self):
        self.handle = ctypes.c_int(0)
        self.name = ""
 
def open_device():
    """
        open the first available device
        returns: DeviceData object with handle to the connected device
    """
    # this is the device handle - it will be used by all functions to "address" the connected device
    device_data = DeviceData()
    device_handle = ctypes.c_int()
    # connect to the first available device
    dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(device_handle))
    device_data.handle = device_handle
    return device_data


def initialize_oscilloscope(device_data, sampling_frequency=2e06, buffer_size=10, offset=0, amplitude_range=1):
    """
        initialize the oscilloscope
        parameters: - device data
                    - sampling frequency in Hz, default is 2MHz
                    - buffer size, default is 10
                    - offset voltage in Volts, default is 0V
                    - amplitude range in Volts, default is ±1V
    """
    # enable all channels !! Set to channel 1
    dwf.FDwfAnalogInChannelEnableSet(device_data.handle, ctypes.c_int(0), ctypes.c_bool(True))
 
    # set offset voltage (in Volts)
    dwf.FDwfAnalogInChannelOffsetSet(device_data.handle, ctypes.c_int(0), ctypes.c_double(offset))
 
    # set range (maximum signal amplitude in Volts)
    dwf.FDwfAnalogInChannelRangeSet(device_data.handle, ctypes.c_int(0), ctypes.c_double(amplitude_range))
 
    # set the buffer size (data point in a recording)
    dwf.FDwfAnalogInBufferSizeSet(device_data.handle, ctypes.c_int(buffer_size))
 
    # set the acquisition frequency (in Hz)
    dwf.FDwfAnalogInFrequencySet(device_data.handle, ctypes.c_double(sampling_frequency))
 
    # disable averaging (for more info check the documentation)
    dwf.FDwfAnalogInChannelFilterSet(device_data.handle, ctypes.c_int(-1), constants.filterDecimate)
    return

def setup_trigger(device_data, trigger_channel=0, trigger_level=0.5, trigger_condition=trigcondRisingPositive):
    """
        setup trigger conditions for the oscilloscope
        parameters: - device data
                    - trigger channel, default is 0 (Channel 1)
                    - trigger level in Volts, default is 0.5V
                    - trigger condition, default is rising edge
    """
    # Set trigger source to analog input
    dwf.FDwfAnalogInTriggerSourceSet(device_data.handle, trigsrcDetectorAnalogIn)
    
    # Set trigger channel
    dwf.FDwfAnalogInTriggerChannelSet(device_data.handle, ctypes.c_int(trigger_channel))
    
    # Set trigger level (in Volts)
    dwf.FDwfAnalogInTriggerLevelSet(device_data.handle, ctypes.c_double(trigger_level))
    
    # Set trigger condition (rising edge, falling edge, etc.)
    dwf.FDwfAnalogInTriggerConditionSet(device_data.handle, trigger_condition)
    return

def acquire_single(device_data, num_samples):
    """
        perform a single triggered acquisition
        parameters: - device data
                    - num_samples: number of samples to acquire
        returns: numpy array of voltage data
    """
    # Start acquisition
    dwf.FDwfAnalogInConfigure(device_data.handle, ctypes.c_bool(False), ctypes.c_bool(True))
    
    # Set DIO 1 HIGH (trigger signal)
    dwf.FDwfDigitalIOOutputSet(device_data.handle, ctypes.c_int(0b00000010))
    
    # Wait for acquisition to complete
    sts = ctypes.c_byte()
    while True:
        dwf.FDwfAnalogInStatus(device_data.handle, ctypes.c_bool(True), ctypes.byref(sts))
        if sts.value == DwfStateDone.value:
            break
        time.sleep(0.01)
    
    # Retrieve data
    data_buffer = (ctypes.c_double * num_samples)()
    dwf.FDwfAnalogInStatusData(device_data.handle, 0, data_buffer, num_samples)
    numpy_data = np.array(data_buffer)
    
    # Set DIO 1 LOW
    dwf.FDwfDigitalIOOutputSet(device_data.handle, ctypes.c_int(0b00000000))
    
    return numpy_data

def collect_arduino_data(ser, num_readings=160):
    """
        collect data from Arduino via serial connection
        parameters: - ser: serial connection object
                    - num_readings: number of readings to collect, default is 160
        returns: pandas DataFrame with Arduino data
    """
    arduino_data = np.empty((num_readings, 4))
    
    for i in range(num_readings):
        data = ser.readline()
        decoded = data.decode().strip()
        values = np.array(decoded.split(','))
        try:
            arduino_data[i] = values
        except:
            pass
    
    arduino_data = np.delete(arduino_data, (0), axis=0)
    df = pd.DataFrame({
        'Index': arduino_data[:, 0], 
        'Timestamp': arduino_data[:, 1], 
        'Loadcell(g)': arduino_data[:, 2], 
        'Position': arduino_data[:, 3]
    })
    
    return df

def save_and_plot_acquisition(voltage_data, sampling_freq, acquisition_num, output_dir="PrimTest", arduino_df=None, trigger_level=0.5):
    """
        save acquisition data to CSV and plot the waveform
        parameters: - voltage_data: numpy array of voltage measurements
                    - sampling_freq: sampling frequency in Hz
                    - acquisition_num: acquisition number for labeling
                    - output_dir: directory to save CSV files
                    - arduino_df: optional pandas DataFrame with Arduino data
                    - trigger_level: trigger level for plotting, default is 0.5V
    """
    num_samples = len(voltage_data)
    
    # Create timestamp array (in milliseconds)
    timestamp = np.arange(num_samples) / (sampling_freq / 1000)
    df_scope = pd.DataFrame({'Timestamp(ms)': timestamp, 'Voltage(V)': voltage_data})
    
    # Combine with Arduino data if available
    if arduino_df is not None:
        df = pd.concat([df_scope, arduino_df], axis=1)
    else:
        df = df_scope
    
    # Save to CSV
    csv_path = f"{output_dir}/Run_{acquisition_num}.csv"
    df.to_csv(csv_path, index=False)
    print(f"Data saved to file: {csv_path}")
    
    # Plot the captured waveform
    plt.figure(figsize=(10, 5))
    plt.plot(timestamp, voltage_data, label='Captured Signal')
    plt.axhline(y=trigger_level, color='r', linestyle='--', label='Trigger Level')
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (V)")
    plt.title(f"Oscilloscope Capture with Trigger (Acquisition {acquisition_num})")
    plt.legend()
    plt.grid()
    plt.show()

def configure_acquisition(device_data, acquisition_time_ms, sampling_freq):
    """
        configure device for acquisition
        parameters: - device data
                    - acquisition_time_ms: acquisition time in milliseconds
                    - sampling_freq: sampling frequency in Hz
        returns: number of samples that will be acquired
    """
    # Set DIO as output
    dwf.FDwfDigitalIOOutputEnableSet(device_data.handle, ctypes.c_int(0b00000010))
    
    # Configure acquisition time
    num_samples = int(sampling_freq * (acquisition_time_ms / 1000))
    dwf.FDwfAnalogInBufferSizeSet(device_data.handle, ctypes.c_int(num_samples))
    
    return num_samples

# Close the device
def close(device_data):
    """
        reset the scope
    """
    dwf.FDwfAnalogInReset(device_data.handle)
    return

def run_acquisitions(num_acquisitions=5, acquisition_time_ms=30, sampling_freq=2e6, 
                     trigger_level=0.5, trigger_channel=0, offset=0, amplitude_range=50,
                     ser=None, output_dir="PrimTest"):
    """
        complete acquisition workflow: open device, configure, acquire data, and close
        parameters: - num_acquisitions: number of acquisitions to perform, default is 5
                    - acquisition_time_ms: acquisition time in milliseconds, default is 30ms
                    - sampling_freq: sampling frequency in Hz, default is 2 MHz
                    - trigger_level: trigger voltage level, default is 0.5V
                    - trigger_channel: trigger channel (0 = Channel 1), default is 0
                    - offset: offset voltage in Volts, default is 0V
                    - amplitude_range: amplitude range in Volts, default is ±50V
                    - ser: serial connection for Arduino data (optional)
                    - output_dir: directory to save CSV files, default is "PrimTest"
    """
    # Step 1: Open device
    print("Opening device...")
    device_data = open_device()
    
    try:
        # Step 2: Initialize the oscilloscope
        print("Initializing oscilloscope...")
        initialize_oscilloscope(device_data, sampling_frequency=sampling_freq, buffer_size=10, 
                               offset=offset, amplitude_range=amplitude_range)
        
        # Step 3: Setup trigger
        print(f"Setting up trigger (level: {trigger_level}V, channel: {trigger_channel})...")
        setup_trigger(device_data, trigger_channel=trigger_channel, 
                     trigger_level=trigger_level, trigger_condition=trigcondRisingPositive)
        
        # Step 4: Configure acquisition parameters
        print(f"Configuring acquisition ({acquisition_time_ms}ms at {sampling_freq/1e6}MHz)...")
        num_samples = configure_acquisition(device_data, acquisition_time_ms, sampling_freq)
        
        # Step 5: Run acquisitions
        print(f"Starting {num_acquisitions} acquisitions...\n")
        for acquisition in range(1, num_acquisitions + 1):
            print(f"Waiting for trigger... (Acquisition {acquisition}/{num_acquisitions})")
            
            # Perform single acquisition
            voltage_data = acquire_single(device_data, num_samples)
            print(f"Acquisition {acquisition} complete!")
            print(voltage_data)
            
            # Collect Arduino data if available
            arduino_df = None
            if ser is not None:
                arduino_df = collect_arduino_data(ser)
            
            # Save and plot
            save_and_plot_acquisition(voltage_data, sampling_freq, acquisition, 
                                     output_dir, arduino_df, trigger_level)
        
        print("\nAll acquisitions completed successfully!")
        
    finally:
        # Step 6: Close and reset the device
        print("Closing device...")
        close(device_data)
    
    return


