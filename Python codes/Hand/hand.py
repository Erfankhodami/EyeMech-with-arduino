import cv2
import mediapipe as mp
import serial
import time
import random

from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import face_detection as mp_face
from mediapipe.python.solutions import drawing_utils as mp_drawing

# Update to your new COM port
PORT = 'COM21'
BAUD_RATE = 115200 

try:
    arduino = serial.Serial(port=PORT, baudrate=BAUD_RATE, timeout=0)
    time.sleep(2) 
    print(f"Connected to Arduino on {PORT} at {BAUD_RATE} baud.")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# Initialize MediaPipe Modules
mp_hands = mp.solutions.hands
mp_face = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=1)
face_detection = mp_face.FaceDetection(min_detection_confidence=0.7)
# Open webcam
cap = cv2.VideoCapture(0)

# Get camera resolution for mapping
success, frame = cap.read()
if success:
    frame_height, frame_width, _ = frame.shape
else:
    frame_width, frame_height = 640, 480 # Fallback default

def map_value(value, in_min, in_max, out_min, out_max):
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def is_fist(hand_landmarks):
    """Calculates if the hand is a fist by checking if finger tips are folded below their middle joints"""
    fingers_folded = 0
    tips = [8, 12, 16, 20] # Index, Middle, Ring, Pinky tips
    pips = [6, 10, 14, 18] # Middle joints of those fingers

    for tip, pip in zip(tips, pips):
        # In OpenCV, Y increases as you go down the screen. 
        # If the tip is lower than the joint, the finger is curled.
        if hand_landmarks.landmark[tip].y > hand_landmarks.landmark[pip].y:
            fingers_folded += 1
            
    # If 3 or more fingers are folded, classify as a fist
    return fingers_folded >= 3

last_angleX = -1
last_angleY = -1
is_currently_fist = False

try:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue

        # Flip horizontally for selfie-view and convert colors
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame
        hand_results = hands.process(rgb_frame)
        face_results = face_detection.process(rgb_frame)

        track_x, track_y = None, None
        fist_detected = False

        # 1. Prioritize Hand Tracking
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Check for fist
                fist_detected = is_fist(hand_landmarks)
                
                # Use the center of the palm (landmark 9) for smoother eye tracking
                palm_center = hand_landmarks.landmark[9]
                track_x = int(palm_center.x * frame_width)
                track_y = int(palm_center.y * frame_height)

        # 2. Fallback to Face Tracking if no hand is visible
        elif face_results.detections:
            for detection in face_results.detections:
                bboxC = detection.location_data.relative_bounding_box
                
                # Get center of the face bounding box
                track_x = int((bboxC.xmin + bboxC.width / 2) * frame_width)
                track_y = int((bboxC.ymin + bboxC.height / 2) * frame_height)
                
                # Draw a dot on the face center
                cv2.circle(frame, (track_x, track_y), 10, (255, 0, 0), cv2.FILLED)

        # --- ARDUINO COMMUNICATION ---
        
        # A. Handle Fist State (Locking eyelids closed)
        if fist_detected and not is_currently_fist:
            arduino.write(b"C\n") # Send 'Close' command
            is_currently_fist = True
        elif not fist_detected and is_currently_fist:
            arduino.write(b"O\n") # Send 'Open' command
            is_currently_fist = False

        # B. Handle Random Blinking (Only if eyes aren't locked closed by a fist)
        if not is_currently_fist and random.random() < 0.02: # ~2% chance per frame (blinks every 1.5 - 3 seconds)
            arduino.write(b"B\n")

        # C. Handle X/Y Tracking
        if track_x is not None and track_y is not None:
            # Clamp coordinates
            track_x = max(0, min(track_x, frame_width))
            track_y = max(0, min(track_y, frame_height))

            # Map X standard (40 to 140)
            angleX = map_value(track_x, 0, frame_width, 40, 140)
            
            # Map Y inverted (50 to 10)
            angleY = map_value(track_y, 0, frame_height, 50, 10)

            if angleX != last_angleX or angleY != last_angleY:
                payload = f"{angleX},{angleY}\n"
                arduino.write(payload.encode('utf-8'))
                last_angleX = angleX
                last_angleY = angleY

        # Show the camera feed
        cv2.imshow('Eye Mech Tracker', frame)
        
        # Press ESC to exit
        if cv2.waitKey(5) & 0xFF == 27:
            break

except KeyboardInterrupt:
    pass
finally:
    print("\nCleaning up...")
    cap.release()
    cv2.destroyAllWindows()
    arduino.close()