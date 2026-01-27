"""
Simple Static Noise Recording Script
Records 5 seconds of voltage data from Digilent oscilloscope and saves to CSV
"""

import numpy as np
import pandas as pd
import ctypes
from sys import platform
from os import sep
from datetime import datetime
import os
from scipy import signal


def _initialize_dwf_library():
    """Load the DWF library"""
    if platform.startswith("win"):
        return ctypes.cdll.dwf
    elif platform.startswith("darwin"):
        possible_paths = [
            "/Applications/WaveForms.app/Contents/Frameworks/dwf.framework/dwf",
            "/Library/Frameworks/dwf.framework/dwf",
        ]
        for lib_path in possible_paths:
            try:
                return ctypes.cdll.LoadLibrary(lib_path)
            except OSError:
                continue
        raise OSError("Could not find dwf.framework")
    else:
        return ctypes.cdll.LoadLibrary("libdwf.so")


def apply_50hz_notch_filter(voltage_data, sampling_frequency, harmonics=3):
    """
    Apply notch filter to remove 50Hz power line noise and its harmonics
    
    Parameters:
    -----------
    voltage_data : array-like
        Input voltage signal
    sampling_frequency : float
        Sampling frequency in Hz
    harmonics : int
        Number of harmonics to filter (default: 3, filters 50Hz, 100Hz, 150Hz)
    
    Returns:
    --------
    filtered_data : np.ndarray
        Filtered voltage signal
    """
    filtered_data = voltage_data.copy()
    
    # Quality factor for the notch filter (higher Q = narrower notch)
    # Lower Q = wider notch, better for catching frequency variations
    Q = 10.0
    
    # Apply notch filter for 50Hz and its harmonics
    for i in range(1, harmonics + 1):
        freq = 50.0 * i  # 50Hz, 100Hz, 150Hz, etc.
        
        # Design notch filter
        b, a = signal.iirnotch(freq, Q, sampling_frequency)
        
        # Apply filter
        filtered_data = signal.filtfilt(b, a, filtered_data)
        print(f"  Applied {freq:.0f}Hz notch filter")
    
    return filtered_data


def record_static_noise(duration_seconds=10, sampling_frequency=500e3, 
                        amplitude_range=50, channel=0):
    """Record noise from oscilloscope using record mode for long acquisitions"""
    
    dwf = _initialize_dwf_library()
    device_handle = ctypes.c_int()
    dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(device_handle))
    
    if device_handle.value == 0:
        raise ConnectionError("Failed to open Digilent device")
    
    try:
        total_samples = int(sampling_frequency * duration_seconds)
        
        # Configure channel
        dwf.FDwfAnalogInChannelEnableSet(device_handle, ctypes.c_int(channel), 
                                         ctypes.c_bool(True))
        dwf.FDwfAnalogInChannelRangeSet(device_handle, ctypes.c_int(channel), 
                                        ctypes.c_double(amplitude_range))
        dwf.FDwfAnalogInFrequencySet(device_handle, ctypes.c_double(sampling_frequency))
        
        # Use record mode (acqmodeRecord = 3)
        dwf.FDwfAnalogInAcquisitionModeSet(device_handle, ctypes.c_int(3))
        
        # Set record length
        dwf.FDwfAnalogInRecordLengthSet(device_handle, ctypes.c_double(duration_seconds))
        
        print(f"Recording {duration_seconds}s at {sampling_frequency/1e3:.0f} kHz ({total_samples:,} samples)...")
        
        # Start recording
        dwf.FDwfAnalogInConfigure(device_handle, ctypes.c_bool(False), ctypes.c_bool(True))
        
        # Collect data in chunks
        all_data = []
        samples_collected = 0
        
        while samples_collected < total_samples:
            sts = ctypes.c_byte()
            dwf.FDwfAnalogInStatus(device_handle, ctypes.c_bool(True), ctypes.byref(sts))
            
            # Check if recording is done or failed
            if sts.value == 2:  # DwfStateDone
                break
            
            # Get available samples
            available = ctypes.c_int()
            lost = ctypes.c_int()
            corrupted = ctypes.c_int()
            dwf.FDwfAnalogInStatusRecord(device_handle, ctypes.byref(available), 
                                         ctypes.byref(lost), ctypes.byref(corrupted))
            
            if lost.value:
                print(f"Warning: Lost {lost.value} samples!")
            if corrupted.value:
                print(f"Warning: Corrupted {corrupted.value} samples!")
            
            # Read available samples
            if available.value > 0:
                chunk_size = min(available.value, total_samples - samples_collected)
                data_buffer = (ctypes.c_double * chunk_size)()
                dwf.FDwfAnalogInStatusData(device_handle, channel, data_buffer, chunk_size)
                all_data.extend(data_buffer)
                samples_collected += chunk_size
                
                # Progress update
                progress = (samples_collected / total_samples) * 100
                print(f"\rProgress: {progress:.1f}% ({samples_collected:,}/{total_samples:,})", end='', flush=True)
        
        print()  # New line after progress
        print(f"✓ Recorded {len(all_data):,} samples")
        
        # Create DataFrame
        voltage_data = np.array(all_data)
        timestamp = np.arange(len(voltage_data)) / (sampling_frequency / 1000)
        df = pd.DataFrame({
            'Timestamp_ms': timestamp,
            'Voltage_V': voltage_data
        })
        
        return df
        
    finally:
        dwf.FDwfAnalogInReset(device_handle)
        dwf.FDwfDeviceClose(device_handle)


def main():
    # Record data
    df = record_static_noise(
        duration_seconds=5,
        sampling_frequency=500e3,
        amplitude_range=50,
        channel=0
    )
    
    # Apply 50Hz notch filter
    print("\nApplying 50Hz notch filter...")
    df['Voltage_V'] = apply_50hz_notch_filter(
        df['Voltage_V'].values, 
        sampling_frequency=500e3,
        harmonics=3  # Filter 50Hz, 100Hz, 150Hz
    )
    
    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.dirname(os.path.abspath(__file__))
    filename = f"PE_static_noise_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=False)
    print(f"✓ Saved: {filepath}")
    print(f"  (Filtered data only)")


if __name__ == "__main__":
    main()
