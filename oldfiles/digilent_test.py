import time
import numpy as np
import csv
import matplotlib.pyplot as plt
from dwfconstants import *
import ctypes
import sys
import serial
import pandas as pd

# Load the DWF library
if sys.platform.startswith("win"):
    dwf = ctypes.cdll.LoadLibrary("dwf.dll")
elif sys.platform.startswith("darwin"):
    dwf = ctypes.cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = ctypes.cdll.LoadLibrary("libdwf.so")

g_hdwf = ctypes.c_int()
dwf.FDwfDeviceOpen(ctypes.c_int(-1), ctypes.byref(g_hdwf))
if g_hdwf.value == 0:
    print("Failed to open device")
    sys.exit()

# Connect to serial port and flush
ser = serial.Serial("/dev/ttyACM0", 115200)
ser.flush()
time.sleep(0.1)
arduino_data=np.empty((160,4))

# Set up the oscilloscope
dwf.FDwfAnalogInFrequencySet(g_hdwf, ctypes.c_double(1e6))  # 1 MHz sample rate
dwf.FDwfAnalogInChannelEnableSet(g_hdwf, 0, ctypes.c_bool(True))  # Enable channel 1
dwf.FDwfAnalogInChannelRangeSet(g_hdwf, 0, ctypes.c_double(5.0))  # Set range to 5V

# Set trigger conditions
dwf.FDwfAnalogInTriggerSourceSet(g_hdwf, trigsrcDetectorAnalogIn)  # Use channel trigger
dwf.FDwfAnalogInTriggerChannelSet(g_hdwf, ctypes.c_int(0))  # Channel 1
dwf.FDwfAnalogInTriggerLevelSet(g_hdwf, ctypes.c_double(0.3))  # Trigger at 1V
dwf.FDwfAnalogInTriggerConditionSet(g_hdwf, trigcondRisingPositive)  # Trigger on rising edge

# Set DIO as output
dwf.FDwfDigitalIOOutputEnableSet(g_hdwf, ctypes.c_int(0b00000010))  # Enable DIO 1 as output

# Configure acquisition time (30ms -> 30,000 samples at 1 MHz)
num_samples = int(1e6 * 0.03)
dwf.FDwfAnalogInBufferSizeSet(g_hdwf, ctypes.c_int(num_samples))

# Set number of acquisitions
num_acquisitions = 5  # Change this value to set the number of loops

for acquisition in range(1, num_acquisitions + 1):
    # Start acquisition
    dwf.FDwfAnalogInConfigure(g_hdwf, ctypes.c_bool(False), ctypes.c_bool(True))
    print(f"Waiting for trigger... (Acquisition {acquisition}/{num_acquisitions})")
    
    # Wait for acquisition to complete
    sts = ctypes.c_byte()
    dwf.FDwfDigitalIOOutputSet(g_hdwf, ctypes.c_int(0b00000010))  # Set DIO 1 HIGH
    while True:
        dwf.FDwfAnalogInStatus(g_hdwf, ctypes.c_bool(True), ctypes.byref(sts))
        if sts.value == DwfStateDone.value:
            break
        time.sleep(0.01)  # Wait a bit before checking again

    print(f"Acquisition {acquisition} complete!")
    
    # Retrieve data
    data = (ctypes.c_double * num_samples)()
    dwf.FDwfAnalogInStatusData(g_hdwf, 0, data, num_samples)
    numpy_data = np.array(data)
    print(numpy_data)

    # Retrive data from arduino
    for i in range(160):
        data = ser.readline()
        decoded = data.decode().strip()  # Decode bytes and remove trailing characters
        values = np.array(decoded.split(','))  # Split by tab character
        try:
            arduino_data[i]=values
        except:
            pass
        #arduino_data = np.append(arduino_data, values, axis=0)

    arduino_data = np.delete(arduino_data, (0), axis=0)

    df2 = pd.DataFrame({'Index': arduino_data[:,0], 'Timestamp': arduino_data[:,1], 'Loadcell(g)': arduino_data[:,2], 'Position': arduino_data[:,3],})

    timestamp = np.array([])
    for i in range(num_samples):
        timestamp = np.append(timestamp, i/1000)

    df1 = pd.DataFrame({'Timestamp(ms)': timestamp[::], 'Voltage(V)': numpy_data[::]})
    
    df=pd.concat([df1,df2],axis=1)
    df.to_csv(f"PrimTest/Run_{acquisition}.csv", index=False)
    #df.plot(x="Timestamp(ms)",y="Voltage(V)")

    # Save to CSV
    #csv_filename = f"captured_data_{acquisition}.csv"
    #with open(csv_filename, "w", newline='') as f:
    #    writer = csv.writer(f)
    #    writer.writerow(["Time (ms)", "Voltage (V)"])
    #    for i in range(num_samples):
    #        writer.writerow([i / 1000, numpy_data[i]])
    
    dwf.FDwfDigitalIOOutputSet(g_hdwf, ctypes.c_int(0b00000000))  # Set DIO 1 LOW
    print(f"Data saved to file: PrimTest/Run_{acquisition}.csv")
    
    # Plot the captured waveform
    time_values = np.arange(num_samples) / 1000  # Convert to ms
    plt.figure(figsize=(10, 5))
    plt.plot(time_values, numpy_data, label='Captured Signal')
    plt.axhline(y=0.5, color='r', linestyle='--', label='Trigger Level')
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (V)")
    plt.title(f"Oscilloscope Capture with Trigger (Acquisition {acquisition})")
    plt.legend()
    plt.grid()
    plt.show()

# Close the device
dwf.FDwfDeviceClose(g_hdwf)