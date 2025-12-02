#include <AccelStepper.h>

// Pin configuration
#define PUL_PIN 9   // Step (Pulse) pin
#define DIR_PIN 8   // Direction pin
#define ENA_PIN 7   // Enable pin (optional)
#define END_STOP_PIN_1 12  // Left end stop switch pin
// #define END_STOP_PIN_2 13  // Right end stop switch pin (Removed)
#define AUTO_TRIGGER_PIN 3 // Digital input to trigger autoCycle()

// Stepper configuration
#define MAX_SPEED 2000    // Max speed in steps per second
#define ACCELERATION 4000 // Acceleration in steps per second^2
#define SLOW_SPEED 100    // Slower speed for return movement
#define SLEEP_TIME 3000   // Delay at the end of autoCycle (in ms)
#define BACKUP_STEPS 125  // Steps to move back (approx 1.5cm)

// Create stepper instance
AccelStepper stepper(AccelStepper::DRIVER, PUL_PIN, DIR_PIN);

void setup() {
    pinMode(ENA_PIN, OUTPUT);
    digitalWrite(ENA_PIN, LOW); // Enable driver (active LOW)

    pinMode(END_STOP_PIN_1, INPUT_PULLUP);
    // pinMode(END_STOP_PIN_2, INPUT_PULLUP); // Removed
    pinMode(AUTO_TRIGGER_PIN, INPUT); // Trigger pin for autoCycle()

    stepper.setPinsInverted(true, false, false);
    stepper.setMaxSpeed(MAX_SPEED);
    stepper.setAcceleration(ACCELERATION);

    Serial.begin(115200);
    Serial.println("Stepper Ready. Enter steps (positive for forward, negative for backward), or '1' for auto-cycle.");
}

void moveStepper(int steps) {
    digitalWrite(ENA_PIN, LOW); // Ensure driver is enabled

    stepper.move(steps);
    unsigned long startTime = millis();

    while (stepper.distanceToGo() != 0) {
        if (steps < 0 && digitalRead(END_STOP_PIN_1) == LOW) {
            Serial.println("End stop 1 (left) triggered! Stopping negative movement.");
            stepper.stop();
            return;
        }

        stepper.run();
    }

    unsigned long duration = millis() - startTime;
    float speed = (float)abs(steps) / (duration / 1000.0);

    Serial.print("Move completed. Speed: ");
    Serial.print(speed);
    Serial.println(" steps/sec");
}

void autoCycle() {
    Serial.println("Auto-cycle started: Moving negative 100 steps or until end stop 1...");

    digitalWrite(ENA_PIN, LOW); // Re-enable driver

    stepper.setMaxSpeed(MAX_SPEED);
    stepper.setAcceleration(ACCELERATION);
    stepper.move(-130);  // Move only ~100 steps

    while (stepper.distanceToGo() != 0) {
        stepper.run();

        if (digitalRead(END_STOP_PIN_1) == LOW) {
            Serial.println("End stop 1 reached. Stopping early.");
            stepper.setCurrentPosition(stepper.currentPosition()); // Immediate stop
            break;
        }
    }


    Serial.println("Waiting 1000ms...");
    delay(1000);

    Serial.println("Moving back slowly...");
    stepper.setMaxSpeed(SLOW_SPEED);
    stepper.move(BACKUP_STEPS);  // Move back fixed distance

    while (stepper.distanceToGo() != 0) {
        stepper.run();
    }

    Serial.println("Return complete. Resetting position and disabling stepper.");
    stepper.setCurrentPosition(0);
    digitalWrite(ENA_PIN, HIGH);  // Disable driver

    Serial.print("Sleeping for ");
    Serial.print(SLEEP_TIME);
    Serial.println("ms...");
    delay(SLEEP_TIME);
}

void loop() {
    // Trigger autoCycle from pin 3
    if (digitalRead(AUTO_TRIGGER_PIN) == HIGH) {
        Serial.println("Digital trigger received on pin 3.");
        autoCycle();
    }

    // Trigger autoCycle or step from serial
    if (Serial.available() > 0) {
        int input = Serial.parseInt();

        if (input == 1) {
            autoCycle();
        } else if (input != 0) {
            Serial.print("Moving ");
            Serial.print(input);
            Serial.println(" steps...");
            moveStepper(input);
        }

        Serial.println("Enter new step count:");
    }
}