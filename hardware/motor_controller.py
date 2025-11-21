"""
Motor Controller Module for TENG Experiments
Handles serial communication with Arduino-controlled stepper motor
"""

import serial
import time


class MotorController:
    """
    Controls the stepper motor via Arduino for TENG impact testing.
    
    The Arduino expects:
    - '1' to trigger an auto-cycle (impact sequence)
    - Integer values for manual step movements
    """
    
    def __init__(self, port=None, baudrate=115200, timeout=2):
        """
        Initialize motor controller
        
        Parameters:
            port: Serial port (e.g., '/dev/cu.usbserial-0001' for macOS, 'COM4' for Windows)
            baudrate: Communication speed (default: 115200)
            timeout: Serial timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.is_connected = False
        
    def connect(self):
        """Establish serial connection to Arduino"""
        if self.port is None:
            raise ValueError("Serial port not specified. Please set port in configuration.")
        
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Wait for Arduino to reset
            self.ser.flush()
            self.is_connected = True
            print(f"✓ Motor controller connected on {self.port}")
            
            # Read any startup messages
            time.sleep(0.5)
            while self.ser.in_waiting:
                msg = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if msg:
                    print(f"  Arduino: {msg}")
                    
        except serial.SerialException as e:
            print(f"✗ Failed to connect to motor controller: {e}")
            raise
            
    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            
    def trigger_impact_cycle(self, wait_for_completion=True):
        """
        Trigger one complete impact cycle
        
        The Arduino will:
        1. Move forward (negative steps) to impact position
        2. Wait (dwell time)
        3. Return slowly to home position
        4. Sleep for configured time
        
        Parameters:
            wait_for_completion: If True, wait for cycle to complete before returning
        """
        if not self.is_connected:
            raise ConnectionError("Motor not connected. Call connect() first.")
        
        print("→ Triggering impact cycle...")
        self.ser.write(b'1\n')
        self.ser.flush()
        
        if wait_for_completion:
            # Read Arduino output during cycle
            start_time = time.time()
            timeout = 30  # Maximum 30 seconds per cycle
            
            while time.time() - start_time < timeout:
                if self.ser.in_waiting:
                    msg = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if msg:
                        print(f"  Motor: {msg}")
                        # Check if cycle completed
                        if "Sleeping" in msg or "Enter new step count" in msg:
                            break
                time.sleep(0.1)
                
    def move_steps(self, steps):
        """
        Move motor by specified number of steps
        
        Parameters:
            steps: Number of steps (positive = forward, negative = backward)
        """
        if not self.is_connected:
            raise ConnectionError("Motor not connected. Call connect() first.")
        
        print(f"→ Moving motor {steps} steps...")
        self.ser.write(f"{steps}\n".encode())
        self.ser.flush()
        
        # Read response
        time.sleep(0.5)
        while self.ser.in_waiting:
            msg = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if msg:
                print(f"  Motor: {msg}")
                
    def run_experiment_cycles(self, num_cycles, cycle_callback=None, cycle_delay=0):
        """
        Run multiple impact cycles for an experiment
        
        Parameters:
            num_cycles: Number of impact cycles to perform
            cycle_callback: Optional function to call after each cycle (e.g., for data acquisition)
            cycle_delay: Additional delay between cycles (seconds)
        """

        for cycle_num in range(1, num_cycles + 1):
            print(f"\n--- Cycle {cycle_num}/{num_cycles} ---")
            
            # Trigger impact
            self.trigger_impact_cycle(wait_for_completion=True)
            
            # Execute callback (e.g., trigger oscilloscope acquisition)
            if cycle_callback:
                try:
                    cycle_callback(cycle_num)
                except Exception as e:
                    print(f"✗ Error in cycle callback: {e}")
            
            # Additional delay if needed
            if cycle_delay > 0 and cycle_num < num_cycles:
                print(f"  Waiting {cycle_delay}s before next cycle...")
                time.sleep(cycle_delay)
        
        print(f"\n{'='*60}")
        print(f"✓ Experiment complete: {num_cycles} cycles finished")
        print(f"{'='*60}\n")
        
    def home_position(self):
        """Move motor to home position (end stop 2)"""
        print("→ Homing motor...")
        self.move_steps(100000)  # Large forward move to hit end stop
        
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
