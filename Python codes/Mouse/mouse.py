import pyautogui
import serial
import time
import keyboard  # New import for detecting keystrokes

PORT = 'COM21'
BAUD_RATE = 115200 

try:
    arduino = serial.Serial(port=PORT, baudrate=BAUD_RATE, timeout=0)
    time.sleep(2) 
    print(f"Connected to Arduino on {PORT} at {BAUD_RATE} baud.")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

screen_width, screen_height = pyautogui.size()
print(f"Tracking active. Screen resolution: {screen_width}x{screen_height}")

def map_value(value, in_min, in_max, out_min, out_max):
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

last_angleX = -1
last_angleY = -1
last_b_state = False  # Tracks if the 'b' key is currently being held down

try:
    while True:
        # --- 1. KEYBOARD BLINK LOGIC ---
        # Read the current state of the 'b' key
        current_b_state = keyboard.is_pressed('b')
        
        # Only send the command exactly when the key is first pressed
        if current_b_state and not last_b_state:
            arduino.write(b"B\n")
            print("Keyboard blink triggered!")
            
        last_b_state = current_b_state

        # --- 2. MOUSE TRACKING LOGIC ---
        mouseX, mouseY = pyautogui.position()
        mouseX = max(0, min(mouseX, screen_width))
        mouseY = max(0, min(mouseY, screen_height))

        angleX = map_value(mouseX, 0, screen_width, 40, 140)
        angleY = map_value(mouseY, 0, screen_height, 50, 10)

        if angleX != last_angleX or angleY != last_angleY:
            payload = f"{angleX},{angleY}\n"
            arduino.write(payload.encode('utf-8'))
            
            last_angleX = angleX
            last_angleY = angleY
        
        time.sleep(0.015) 

except KeyboardInterrupt:
    print("\nTracking stopped.")
    arduino.close()