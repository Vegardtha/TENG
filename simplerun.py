import ctypes                     # import the C compatible data types
from sys import platform, path    # this is needed to check the OS type and get the PATH
from os import sep                # OS specific file path separators
 
# load the dynamic library, get constants path (the path is OS specific)
if platform.startswith("win"):
    # on Windows
    dwf = ctypes.cdll.dwf
    constants_path = "C:" + sep + "Program Files (x86)" + sep + "Digilent" + sep + "WaveFormsSDK" + sep + "samples" + sep + "py"
elif platform.startswith("darwin"):
    # on macOS - try multiple paths
    possible_paths = [
        "/Library/Frameworks/dwf.framework/dwf",
        "/Applications/WaveForms.app/Contents/Frameworks/dwf.framework/Versions/A/dwf",
        "/Applications/WaveForms.app/Contents/Frameworks/dwf.framework/dwf"
    ]
    
    dwf = None
    for lib_path in possible_paths:
        try:
            dwf = ctypes.cdll.LoadLibrary(lib_path)
            print(f"Loaded DWF library from: {lib_path}")
            break
        except OSError as e:
            print(f"Failed to load from {lib_path}: {e}")
            continue
    
    if dwf is None:
        raise OSError(
            "Could not load dwf.framework. Please install Digilent WaveForms Runtime from:\n"
            "https://digilent.com/reference/software/waveforms/waveforms-sdk/start"
        )
    
    constants_path = sep + "Applications" + sep + "WaveForms.app" + sep + "Contents" + sep + "Resources" + sep + "SDK" + sep + "samples" + sep + "py"
else:
    # on Linux
    dwf = ctypes.cdll.LoadLibrary("libdwf.so")
    constants_path = sep + "usr" + sep + "share" + sep + "digilent" + sep + "waveforms" + sep + "samples" + sep + "py"
 
# import constants
path.append(constants_path)
import dwfconstants as constants


class data:
    """
        stores the device handle and the device name
    """
    handle = ctypes.c_int(0)
    name = ""
    sampling_frequency = 2e04
    buffer_size = 8192
 
def open_device():
    """
        open the first available device
    """
    # First, check how many devices are connected
    num_devices = ctypes.c_int()
    dwf.FDwfEnum(constants.enumfilterAll, ctypes.byref(num_devices))
    print(f"Found {num_devices.value} device(s)")
    
    if num_devices.value == 0:
        print("\nNo Digilent devices found. Please check:")
        print("1. Is your device plugged in via USB?")
        print("2. Is the WaveForms application closed?")
        print("3. Try unplugging and replugging the device")
        raise RuntimeError("No Digilent device found")
    
    # List available devices
    for i in range(num_devices.value):
        device_name = ctypes.create_string_buffer(32)
        device_serial = ctypes.create_string_buffer(32)
        dwf.FDwfEnumDeviceName(ctypes.c_int(i), device_name)
        dwf.FDwfEnumSN(ctypes.c_int(i), device_serial)
        print(f"Device {i}: {device_name.value.decode('utf-8')} (S/N: {device_serial.value.decode('utf-8')})")
    
    # this is the device handle - it will be used by all functions to "address" the connected device
    device_handle = ctypes.c_int()
    # connect to the first available device
    dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(device_handle))
    
    # Check if device opened successfully
    if device_handle.value == 0:
        error = ctypes.create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(error)
        print(f"Failed to open device: {error.value.decode('utf-8')}")
        raise RuntimeError("Could not open Digilent device")
    
    print(f"Device opened successfully with handle: {device_handle.value}")
    data.handle = device_handle
    return data

 
def initialize(device_data, sampling_frequency=2e04, buffer_size=8192, offset=0, amplitude_range=5):
    """
        initialize the oscilloscope
        parameters: - device data
                    - sampling frequency in Hz, default is 20MHz
                    - buffer size, default is 8192
                    - offset voltage in Volts, default is 0V
                    - amplitude range in Volts, default is ±5V
    """
    # enable all channels
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
    data.sampling_frequency = sampling_frequency
    data.buffer_size = buffer_size
    return


def measure(device_data, channel):
    """
        measure a voltage
        parameters: - device data
                    - the selected oscilloscope channel (1-2, or 1-4)
 
        returns:    - the measured voltage in Volts
    """
    # set up the instrument
    dwf.FDwfAnalogInConfigure(device_data.handle, ctypes.c_bool(False), ctypes.c_bool(False))
 
    # read data to an internal buffer
    dwf.FDwfAnalogInStatus(device_data.handle, ctypes.c_bool(False), ctypes.c_int(0))
 
    # extract data from that buffer
    voltage = ctypes.c_double()   # variable to store the measured voltage
    dwf.FDwfAnalogInStatusSample(device_data.handle, ctypes.c_int(channel - 1), ctypes.byref(voltage))
 
    # store the result as float
    voltage = voltage.value
    return voltage


def record(device_data, channel):
    """
        record an analog signal
        parameters: - device data
                    - the selected oscilloscope channel (1-2, or 1-4)
        returns:    - buffer - a list with the recorded voltages
                    - time - a list with the time moments for each voltage in seconds (with the same index as "buffer")
    """
    import time
    
    # Check for errors helper function
    def check_error():
        error = ctypes.create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(error)
        if error.value:
            print(f"DWF Error: {error.value.decode('utf-8')}")
            return False
        return True
    
    # Re-enable channel (ensure it's on)
    dwf.FDwfAnalogInChannelEnableSet(device_data.handle, ctypes.c_int(channel - 1), ctypes.c_bool(True))
    check_error()
    
    # Configure trigger
    # Set trigger source to detector analog in (same as working example)
    dwf.FDwfAnalogInTriggerSourceSet(device_data.handle, constants.trigsrcDetectorAnalogIn)
    check_error()
    
    # Set which channel to use for triggering
    dwf.FDwfAnalogInTriggerChannelSet(device_data.handle, ctypes.c_int(channel - 1))
    check_error()
    
    # Set trigger level to 0.5V
    dwf.FDwfAnalogInTriggerLevelSet(device_data.handle, ctypes.c_double(0.5))
    check_error()
    
    # Set trigger condition to rising edge
    dwf.FDwfAnalogInTriggerConditionSet(device_data.handle, constants.trigcondRisingPositive)
    check_error()
    
    print(f"Starting acquisition with buffer size: {data.buffer_size}, sampling freq: {data.sampling_frequency}")
    
    # Start acquisition (reconfigure=False, start=True)
    dwf.FDwfAnalogInConfigure(device_data.handle, ctypes.c_bool(False), ctypes.c_bool(True))
    check_error()
 
    # read data to an internal buffer
    timeout_counter = 0
    max_timeout = 100  # 10 seconds timeout
    while True:
        status = ctypes.c_byte()    # variable to store buffer status
        dwf.FDwfAnalogInStatus(device_data.handle, ctypes.c_bool(True), ctypes.byref(status))
        
        if timeout_counter % 10 == 0:  # Print every second
            print(f"Status: {status.value} (Ready={constants.DwfStateReady.value}, Armed={constants.DwfStateArmed.value}, Triggered={constants.DwfStateTriggered.value}, Done={constants.DwfStateDone.value})")
 
        # check internal buffer status
        if status.value == constants.DwfStateDone.value:
                # exit loop when ready
                print("Acquisition complete!")
                break
        
        # Timeout protection
        timeout_counter += 1
        if timeout_counter > max_timeout:
            print(f"Timeout waiting for data acquisition! Final status: {status.value}")
            break
            
        time.sleep(0.1)
 
    # copy buffer
    buffer = (ctypes.c_double * data.buffer_size)()   # create an empty buffer
    dwf.FDwfAnalogInStatusData(device_data.handle, ctypes.c_int(channel - 1), buffer, ctypes.c_int(data.buffer_size))
    
    # Get actual number of samples acquired
    samples_available = ctypes.c_int()
    dwf.FDwfAnalogInStatusSamplesValid(device_data.handle, ctypes.byref(samples_available))
    print(f"Samples available: {samples_available.value}")
 
    # calculate aquisition time
    time = range(0, data.buffer_size)
    time = [moment / data.sampling_frequency for moment in time]
 
    # convert into list
    buffer = [float(element) for element in buffer]
    
    # Debug: Print data statistics
    if len(buffer) > 0:
        print(f"Buffer stats - Min: {min(buffer):.6f}V, Max: {max(buffer):.6f}V, Mean: {sum(buffer)/len(buffer):.6f}V")
        print(f"First 10 samples: {buffer[:10]}")
    
    return buffer, time

def close(device_data):
    """
        reset the scope
    """
    dwf.FDwfAnalogInReset(device_data.handle)
    return


# ===== MAIN CODE TO RECORD ONE TRY =====
if __name__ == "__main__":
    import csv
    
    # Open device
    print("Opening device...")
    device = open_device()
    
    # Initialize oscilloscope with settings
    print("Initializing oscilloscope...")
    initialize(device, sampling_frequency=2e06, buffer_size=8192, offset=0, amplitude_range=1)
    
    # Record one try on channel 1
    print("Recording...")
    buffer, time = record(device, channel=1)
    
    # Save to CSV
    print("Saving data...")
    with open('recording.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Time (s)', 'Voltage (V)'])
        for t, v in zip(time, buffer):
            writer.writerow([t, v])
    
    print(f"Recorded {len(buffer)} samples")
    print(f"Duration: {time[-1]:.4f} seconds")
    print("Data saved to: recording.csv")
    
    # Close device
    close(device)
    print("Done!")