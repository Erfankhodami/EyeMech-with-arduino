#include <Servo.h>

Servo servoX;  
Servo servoY;  
const int pinX = 11;
const int pinY = 10;

Servo topRight;    
Servo topLeft;     
Servo bottomRight; 
Servo bottomLeft;  

const int buttonPin = 2;
int lastButtonState = HIGH; 
bool eyesLockedClosed = false; // Tracks if the fist is holding the eyes closed

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(2); 

  servoX.attach(pinX);
  servoY.attach(pinY);
  
  servoX.write(60); 
  // Initial Y is set to 30 (the center of 50 and 10)
  servoY.write(30); 

  topRight.attach(5);
  topLeft.attach(6);
  topRight.write(100); 
  topLeft.write(100);

  bottomRight.attach(3);
  bottomLeft.attach(9);
  bottomRight.write(40); 
  bottomLeft.write(40);
  
  pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  if (Serial.available() > 0) {
    String latestCoordCommand = "";
    bool blinkRequested = false;
    
    while (Serial.available() > 0) {
      String currentLine = Serial.readStringUntil('\n');
      
      // Check for locking commands
      if (currentLine.indexOf('C') >= 0) {
        if (!eyesLockedClosed) {
          smoothClose();
          eyesLockedClosed = true;
        }
      } 
      else if (currentLine.indexOf('O') >= 0) {
        if (eyesLockedClosed) {
          smoothOpen();
          eyesLockedClosed = false;
        }
      } 
      // Check for normal blink (ignored if locked closed)
      else if (currentLine.indexOf('B') >= 0 && !eyesLockedClosed) {
        blinkRequested = true;
      } 
      // Parse coordinates
      else if (currentLine.indexOf(',') > 0) {
        latestCoordCommand = currentLine;
      }
    }
    
    if (blinkRequested) {
      performBlink();
    }
    
    if (latestCoordCommand.length() > 0) {
      int commaIndex = latestCoordCommand.indexOf(',');
      int targetX = latestCoordCommand.substring(0, commaIndex).toInt();
      int targetY = latestCoordCommand.substring(commaIndex + 1).toInt();
      
      // Updated Y-axis safety check for the new 10-to-50 range limits
      if (targetX >= 40 && targetX <= 140 && targetY >= 10 && targetY <= 50) {
        servoX.write(targetX);
        servoY.write(targetY);
      }
    }
  }

  // Handle Physical Push Button
  int currentButtonState = digitalRead(buttonPin);
  if (currentButtonState == LOW && lastButtonState == HIGH) {
    if (!eyesLockedClosed) performBlink();
  }
  lastButtonState = currentButtonState;
}

void smoothClose() {
  for (int step = 0; step <= 40; step += 2) {
    topRight.write(100 + step);     // Opens 100 -> Closes 140
    topLeft.write(100 - step);      // Opens 100 -> Closes 60
    bottomRight.write(40 - step);   // Opens 40  -> Closes 0
    bottomLeft.write(40 + step);    // Opens 40  -> Closes 80
    delay(10); 
  }
}

void smoothOpen() {
  for (int step = 0; step <= 40; step += 2) {
    topRight.write(140 - step);     // Closes 140 -> Opens 100
    topLeft.write(60 + step);       // Closes 60  -> Opens 100
    bottomRight.write(0 + step);    // Closes 0   -> Opens 40
    bottomLeft.write(80 - step);    // Closes 80  -> Opens 40
    delay(10);
  }
}

void performBlink() {
  smoothClose();
  smoothOpen();
}