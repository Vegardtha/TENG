# Script for WaveForms Script Editor
# This runs inside WaveForms and has device access

# Configuration
sampling_frequency = 2e6  # 2 MHz
buffer_size = 8192
amplitude_range = 1  # ±1V
trigger_level = 0.5  # 0.5V
channel = 0  # Channel 1 (0-indexed)

# Configure analog input
AnalogIn.Channel.Enable.set(channel, True)
AnalogIn.Channel.Range.set(channel, amplitude_range)
AnalogIn.Channel.Offset.set(channel, 0)
AnalogIn.Frequency.set(sampling_frequency)
AnalogIn.BufferSize.set(buffer_size)

# Configure trigger
AnalogIn.Trigger.Source.set('Detector')
AnalogIn.Trigger.Channel.set(channel)
AnalogIn.Trigger.Level.set(trigger_level)
AnalogIn.Trigger.Condition.set('Rising')

print("Waiting for trigger...")

# Start acquisition
AnalogIn.Single.start()

# Wait for completion
wait(10)  # Wait up to 10 seconds

if AnalogIn.Status() == 'Done':
    print("Acquisition complete!")
    
    # Get data
    data = AnalogIn.Channel.data(channel)
    
    # Save to CSV
    import csv
    with open('waveforms_recording.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Time (s)', 'Voltage (V)'])
        for i, v in enumerate(data):
            t = i / sampling_frequency
            writer.writerow([t, v])
    
    print(f"Recorded {len(data)} samples")
    print(f"Min: {min(data):.6f}V, Max: {max(data):.6f}V")
    print("Data saved to: waveforms_recording.csv")
else:
    print("Timeout - no trigger detected")
