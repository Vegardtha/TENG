"""
Generate and upload Arduino firmware with custom motor parameters
"""

import os
import subprocess


def generate_arduino_code(motor_config):
    """
    Generate Arduino sketch with motor parameters from config
    
    Parameters:
        motor_config: MotorConfig object with motor settings
    """
    
    arduino_code = f'''#include <AccelStepper.h>

// Pin configuration
#define PUL_PIN 9   // Step (Pulse) pin
#define DIR_PIN 8   // Direction pin
#define ENA_PIN 7   // Enable pin (optional)
#define END_STOP_PIN_1 12  // Left end stop switch pin
#define END_STOP_PIN_2 13  // Right end stop switch pin
#define AUTO_TRIGGER_PIN 3 // Digital input to trigger autoCycle()

// Motor parameters - Auto-generated from Python config
#define MAX_SPEED {motor_config.max_speed}          // Max speed in steps per second
#define ACCELERATION {motor_config.acceleration}    // Acceleration in steps per second^2
#define SLOW_SPEED {motor_config.slow_speed}        // Slower speed for return movement
#define IMPACT_DISTANCE 104                         // Distance to travel for impact (steps)
#define DWELL_TIME {motor_config.dwell_time}        // Wait time at impact position (ms)
#define SLEEP_TIME {motor_config.sleep_time}        // Delay at the end of autoCycle (ms)

// Create stepper instance
AccelStepper stepper(AccelStepper::DRIVER, PUL_PIN, DIR_PIN);

void setup() {{
    pinMode(ENA_PIN, OUTPUT);
    digitalWrite(ENA_PIN, LOW); // Enable driver (active LOW)

    pinMode(END_STOP_PIN_1, INPUT_PULLUP);
    pinMode(END_STOP_PIN_2, INPUT_PULLUP);
    pinMode(AUTO_TRIGGER_PIN, INPUT); // Trigger pin for autoCycle()

    stepper.setPinsInverted(true, false, false);
    stepper.setMaxSpeed(MAX_SPEED);
    stepper.setAcceleration(ACCELERATION);

    Serial.begin({motor_config.baudrate});
    Serial.println("Stepper Ready. Enter steps or '1' for auto-cycle.");
}}

void moveStepper(int steps) {{
    digitalWrite(ENA_PIN, LOW); // Ensure driver is enabled

    stepper.move(steps);
    unsigned long startTime = millis();

    while (stepper.distanceToGo() != 0) {{
        if (steps < 0 && digitalRead(END_STOP_PIN_1) == HIGH) {{
            Serial.println("End stop 1 (left) triggered! Stopping.");
            stepper.stop();
            return;
        }}

        if (steps > 0 && digitalRead(END_STOP_PIN_2) == HIGH) {{
            Serial.println("End stop 2 (right) triggered! Resetting position.");
            stepper.stop();
            stepper.setCurrentPosition(0);
            return;
        }}

        stepper.run();
    }}

    unsigned long duration = millis() - startTime;
    float speed = (float)abs(steps) / (duration / 1000.0);
    Serial.print("Move completed. Speed: ");
    Serial.print(speed);
    Serial.println(" steps/sec");
}}

void autoCycle() {{
    Serial.println("Auto-cycle started: Moving to impact position...");
    digitalWrite(ENA_PIN, LOW); // Re-enable driver

    stepper.setMaxSpeed(MAX_SPEED);
    stepper.setAcceleration(ACCELERATION);
    stepper.move(-IMPACT_DISTANCE);  // Move forward to impact

    while (stepper.distanceToGo() != 0) {{
        stepper.run();
        if (digitalRead(END_STOP_PIN_1) == HIGH) {{
            Serial.println("End stop 1 reached. Stopping early.");
            stepper.stop();
            break;
        }}
    }}

    Serial.print("Waiting ");
    Serial.print(DWELL_TIME);
    Serial.println("ms...");
    delay(DWELL_TIME);

    Serial.println("Moving back slowly to end stop 2...");
    stepper.setMaxSpeed(SLOW_SPEED);
    stepper.move(100000);  // Large forward move

    while (true) {{
        stepper.run();
        if (digitalRead(END_STOP_PIN_2) == HIGH) {{
            Serial.println("End stop 2 reached. Stopping and disabling stepper.");
            stepper.stop();
            stepper.setCurrentPosition(0);
            digitalWrite(ENA_PIN, HIGH);  // Disable driver
            break;
        }}
    }}

    Serial.print("Sleeping for ");
    Serial.print(SLEEP_TIME);
    Serial.println("ms...");
    delay(SLEEP_TIME);
}}

void loop() {{
    // Trigger autoCycle from pin 3
    if (digitalRead(AUTO_TRIGGER_PIN) == HIGH) {{
        Serial.println("Digital trigger received on pin 3.");
        autoCycle();
    }}

    // Trigger autoCycle or step from serial
    if (Serial.available() > 0) {{
        int input = Serial.parseInt();

        if (input == 1) {{
            autoCycle();
        }} else if (input != 0) {{
            Serial.print("Moving ");
            Serial.print(input);
            Serial.println(" steps...");
            moveStepper(input);
        }}

        Serial.println("Enter new step count:");
    }}
}}
'''
    
    return arduino_code


def upload_firmware_with_config(motor_config, arduino_board="uno"):
    """
    Generate Arduino code from config and upload to board
    
    Parameters:
        motor_config: MotorConfig object
        arduino_board: Board type ("uno", "nano", "mega")
    
    Returns:
        True if successful
    """
    print("\n" + "="*70)
    print("GENERATING & UPLOADING ARDUINO FIRMWARE")
    print("="*70)
    
    # Get project paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    platformio_dir = os.path.join(project_root, "arduino_platformio")
    src_file = os.path.join(platformio_dir, "src", "main.cpp")
    
    # Print motor settings
    print("\nMotor Settings:")
    print(f"  Max Speed: {motor_config.max_speed} steps/sec")
    print(f"  Acceleration: {motor_config.acceleration} steps/sec²")
    print(f"  Dwell Time: {motor_config.dwell_time} ms")
    print(f"  Sleep Time: {motor_config.sleep_time} ms")
    print(f"  Board: {arduino_board}")
    
    # Generate Arduino code
    print("\n→ Generating Arduino code...")
    arduino_code = generate_arduino_code(motor_config)
    
    # Write to file
    os.makedirs(os.path.dirname(src_file), exist_ok=True)
    with open(src_file, 'w') as f:
        f.write(arduino_code)
    print(f"✓ Code written to: {src_file}")
    
    # Upload to Arduino
    print("\n→ Uploading to Arduino...")
    
    # Find PlatformIO CLI
    pio_path = os.path.expanduser("~/.platformio/penv/bin/pio")
    if not os.path.exists(pio_path):
        pio_path = "pio"  # Fallback to system PATH
    
    try:
        result = subprocess.run(
            [pio_path, "run", "-e", arduino_board, "--target", "upload"],
            cwd=platformio_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✓ Firmware uploaded successfully!")
            return True
        else:
            print("✗ Upload failed:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("✗ PlatformIO CLI not found")
        print("  Install with: pip install platformio")
        return False
    except Exception as e:
        print(f"✗ Upload error: {e}")
        return False
