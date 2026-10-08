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

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(2); 

  servoX.attach(pinX);
  servoY.attach(pinY);
  servoX.write(60); 
  servoY.write(50); 

  topRight.attach(5);
  topLeft.attach(6);
  topRight.write(100); 
  topLeft.write(100);

  bottomRight.attach(3);
  bottomLeft.attach(9);
  bottomRight.write(40); 
  bottomLeft.write(40);
  
  // The physical button will still work perfectly alongside the keyboard!
  pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  if (Serial.available() > 0) {
    String latestCoordCommand = "";
    bool blinkRequested = false;
    
    // Rapidly read through the backlog until the buffer is empty
    while (Serial.available() > 0) {
      String currentLine = Serial.readStringUntil('\n');
      
      // Check if this specific line was a blink command
      if (currentLine.indexOf('B') >= 0) {
        blinkRequested = true;
      } 
      // Otherwise, if it has a comma, treat it as a coordinate
      else if (currentLine.indexOf(',') > 0) {
        latestCoordCommand = currentLine;
      }
    }
    
    // 1. If a blink was requested anywhere in the backlog, perform it now
    if (blinkRequested) {
      performBlink();
    }
    
    // 2. Apply the most recent coordinates parsed from the backlog
    if (latestCoordCommand.length() > 0) {
      int commaIndex = latestCoordCommand.indexOf(',');
      int targetX = latestCoordCommand.substring(0, commaIndex).toInt();
      int targetY = latestCoordCommand.substring(commaIndex + 1).toInt();
      
      if (targetX >= 40 && targetX <= 140 && targetY >= 10 && targetY <= 90) {
        servoX.write(targetX);
        servoY.write(targetY);
      }
    }
  }

  // Handle Physical Push Button
  int currentButtonState = digitalRead(buttonPin);
  if (currentButtonState == LOW && lastButtonState == HIGH) {
    performBlink();
  }
  lastButtonState = currentButtonState;
}

void performBlink() {
  for (int step = 0; step <= 40; step += 4) {
    topRight.write(100 + step);     
    topLeft.write(100 - step);      
    bottomRight.write(40 - step);   
    bottomLeft.write(40 + step);    
    delay(10); 
  }

  for (int step = 0; step <= 40; step += 4) {
    topRight.write(140 - step);     
    topLeft.write(60 + step);       
    bottomRight.write(0 + step);    
    bottomLeft.write(80 - step);    
    delay(10);
  }
}