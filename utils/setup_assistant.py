"""
Quick Setup and Port Detection Script
Run this to find your Arduino port and test connections
"""

import serial.tools.list_ports
import sys


def find_arduino_port():
    """
    Automatically find Arduino serial port (simple version for auto-detection)
    Returns: port string or None if not found
    """
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # Look for common Arduino identifiers
        description = str(port.description).lower()
        manufacturer = str(port.manufacturer).lower() if port.manufacturer else ""
        
        if any(keyword in description or keyword in manufacturer 
               for keyword in ['arduino', 'usb', 'serial', 'ch340', 'cp210', 'ftdi']):
            return port.device
    
    return None


def find_arduino_ports():
    """Find potential Arduino serial ports"""
    ports = serial.tools.list_ports.comports()
    arduino_ports = []
    
    print("\n" + "="*70)
    print("AVAILABLE SERIAL PORTS")
    print("="*70)
    
    if not ports:
        print("No serial ports found!")
        return []
    
    for i, port in enumerate(ports, 1):
        print(f"\n{i}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Manufacturer: {port.manufacturer}")
        
        # Identify likely Arduino ports
        if any(keyword in str(port.description).lower() for keyword in ['arduino', 'usb', 'serial', 'ch340', 'cp210']):
            arduino_ports.append(port.device)
            print(f"   ⭐ Likely Arduino port")
    
    return arduino_ports


def test_serial_connection(port):
    """Test connection to a serial port"""
    print(f"\nTesting connection to {port}...")
    try:
        ser = serial.Serial(port, 115200, timeout=2)
        print(f"✓ Successfully opened {port}")
        
        # Try to read from Arduino
        print("  Waiting for Arduino response (5 seconds)...")
        import time
        time.sleep(2)  # Wait for Arduino reset
        
        if ser.in_waiting:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"  Arduino says: {response}")
        else:
            print("  No response yet (this is normal)")
        
        ser.close()
        print(f"✓ Connection test successful")
        return True
        
    except serial.SerialException as e:
        print(f"✗ Failed to connect: {e}")
        return False


def generate_config_code(port):
    """Generate configuration code snippet"""
    print("\n" + "="*70)
    print("CONFIGURATION CODE")
    print("="*70)
    print("\nAdd this to your run_experiment.py:\n")
    
    config_code = f"""
config = ExperimentConfig(
    name="MyTest",
    motor=MotorConfig(
        port="{port}",  # Auto-detected Arduino port
        num_cycles=5
    ),
    oscilloscope=OscilloscopeConfig(
        sampling_frequency=2e6,
        acquisition_time_ms=30,
        amplitude_range=50,
        trigger_level=0.5
    )
)
"""
    print(config_code)


def check_dependencies():
    """Check if required packages are installed"""
    print("\n" + "="*70)
    print("CHECKING DEPENDENCIES")
    print("="*70)
    
    missing = []
    
    packages = {
        'numpy': 'numpy',
        'pandas': 'pandas', 
        'matplotlib': 'matplotlib.pyplot',
        'serial': 'pyserial'
    }
    
    for name, import_name in packages.items():
        try:
            __import__(import_name if '.' not in import_name else import_name.split('.')[0])
            print(f"✓ {name}")
        except ImportError:
            print(f"✗ {name} - NOT INSTALLED")
            missing.append(name if name != 'serial' else 'pyserial')
    
    # Check for dwf library
    try:
        import ctypes
        from sys import platform
        if platform.startswith("darwin"):
            ctypes.cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
        print(f"✓ Digilent WaveForms (dwf)")
    except:
        print(f"⚠ Digilent WaveForms (dwf) - NOT FOUND")
        print("  Download from: https://digilent.com/shop/software/digilent-waveforms/")
    
    if missing:
        print(f"\n⚠ Missing packages. Install with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def main():
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Find ports
    arduino_ports = find_arduino_ports()
    
    if not arduino_ports:
        print("\n⚠ No Arduino ports detected")
        print("Make sure your Arduino is connected via USB")
        return
    
    print("\n" + "="*70)
    print("RECOMMENDED ARDUINO PORT")
    print("="*70)
    
    best_port = arduino_ports[0]
    print(f"\n⭐ {best_port}")
    
    # Test connection
    if input("\nTest connection? (y/n): ").lower() == 'y':
        test_serial_connection(best_port)
    
    # Generate config
    generate_config_code(best_port)
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Update run_experiment.py with the configuration above")
    print("2. Ensure Arduino has the motor control firmware uploaded")
    print("3. Connect the Digilent Analog Discovery")
    print("4. Run: python run_experiment.py")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(0)
