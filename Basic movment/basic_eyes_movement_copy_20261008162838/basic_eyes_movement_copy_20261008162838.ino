#include <Servo.h>

// Eye movement servos
Servo servoX;  
Servo servoY;  
const int pinX = 11;
const int pinY = 10;

// Individual Eyelid Servos
Servo topRight;    // Pin 5
Servo topLeft;     // Pin 6
Servo bottomRight; // Pin 3
Servo bottomLeft;  // Pin 9

// Push button configuration for blinking
const int buttonPin = 2;
int lastButtonState = HIGH; 

void setup() {
  Serial.begin(9600);
  
  // Set a very fast timeout so the Arduino doesn't freeze while waiting for Python data
  Serial.setTimeout(10); 

  // Attach and initialize Eye X and Y
  servoX.attach(pinX);
  servoY.attach(pinY);
  servoX.write(60);
  servoY.write(60);

  // Attach and initialize Top Eyelids (Both open at 100)
  topRight.attach(5);
  topLeft.attach(6);
  topRight.write(100); 
  topLeft.write(100);

  // Attach and initialize Bottom Eyelids (Both open at 40)
  bottomRight.attach(3);
  bottomLeft.attach(9);
  bottomRight.write(40); 
  bottomLeft.write(40);
  
  pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  // 1. Handle Serial Data from Python (Eye Movement)
  if (Serial.available() > 0) {
    // Read the incoming string up to the comma for the X value
    String xString = Serial.readStringUntil(',');
    
    // Read the rest of the string up to the newline for the Y value
    String yString = Serial.readStringUntil('\n');
    
    // Convert the text strings into actual integers
    int targetX = xString.toInt();
    int targetY = yString.toInt();
    
    // Safety check: Only move if the numbers are within your physical limits
    if (targetX >= 40 && targetX <= 140 && targetY >= 50 && targetY <= 70) {
      servoX.write(targetX);
      servoY.write(targetY);
    }
  }

  // 2. Handle Physical Push Button for Blinking
  int currentButtonState = digitalRead(buttonPin);
  
  if (currentButtonState == LOW && lastButtonState == HIGH) {
    performBlink();
  }
  
  lastButtonState = currentButtonState;
}

// Function to animate a smooth, synchronized blink
void performBlink() {
  for (int step = 0; step <= 40; step += 2) {
    topRight.write(100 + step);     
    topLeft.write(100 - step);      
    bottomRight.write(40 - step);   
    bottomLeft.write(40 + step);    
    delay(10); 
  }

  for (int step = 0; step <= 40; step += 2) {
    topRight.write(140 - step);     
    topLeft.write(60 + step);       
    bottomRight.write(0 + step);    
    bottomLeft.write(80 - step);    
    delay(10);
  }
}