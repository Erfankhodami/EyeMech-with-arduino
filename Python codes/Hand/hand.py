import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils, HandLandmarksConnections
import serial
import time
import random

# Model paths and URLs for Tasks API
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HAND_MODEL_PATH = os.path.join(SCRIPT_DIR, "hand_landmarker.task")
FACE_MODEL_PATH = os.path.join(SCRIPT_DIR, "blaze_face_short_range.tflite")

HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"

def ensure_model(file_path, url):
    """Downloads model file if it does not already exist."""
    if not os.path.exists(file_path):
        filename = os.path.basename(file_path)
        print(f"Downloading model '{filename}'...")
        urllib.request.urlretrieve(url, file_path)
        print(f"Downloaded '{filename}'.")

ensure_model(HAND_MODEL_PATH, HAND_MODEL_URL)
ensure_model(FACE_MODEL_PATH, FACE_MODEL_URL)

# Update to your COM port
PORT = 'COM21'
BAUD_RATE = 115200 

try:
    arduino = serial.Serial(port=PORT, baudrate=BAUD_RATE, timeout=0)
    time.sleep(2) 
    print(f"Connected to Arduino on {PORT} at {BAUD_RATE} baud.")
except Exception as e:
    print(f"Failed to connect: {e}")
    exit()

# Initialize MediaPipe Tasks Detectors
hand_options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=HAND_MODEL_PATH),
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
hand_detector = vision.HandLandmarker.create_from_options(hand_options)

face_options = vision.FaceDetectorOptions(
    base_options=python.BaseOptions(model_asset_path=FACE_MODEL_PATH),
    running_mode=vision.RunningMode.IMAGE,
    min_detection_confidence=0.7
)
face_detector = vision.FaceDetector.create_from_options(face_options)

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

def is_fist(landmarks):
    """Calculates if the hand is a fist by checking if finger tips are folded below their middle joints"""
    fingers_folded = 0
    tips = [8, 12, 16, 20] # Index, Middle, Ring, Pinky tips
    pips = [6, 10, 14, 18] # Middle joints of those fingers

    for tip, pip in zip(tips, pips):
        # In OpenCV, Y increases as you go down the screen. 
        # If the tip is lower than the joint, the finger is curled.
        if landmarks[tip].y > landmarks[pip].y:
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
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Process frame with Tasks API
        hand_result = hand_detector.detect(mp_image)
        face_result = face_detector.detect(mp_image)

        track_x, track_y = None, None
        fist_detected = False

        # 1. Prioritize Hand Tracking
        if hand_result.hand_landmarks:
            for hand_landmarks in hand_result.hand_landmarks:
                drawing_utils.draw_landmarks(
                    frame,
                    hand_landmarks,
                    HandLandmarksConnections.HAND_CONNECTIONS
                )
                
                # Check for fist
                fist_detected = is_fist(hand_landmarks)
                
                # Use the center of the palm (landmark 9) for smoother eye tracking
                palm_center = hand_landmarks[9]
                track_x = int(palm_center.x * frame_width)
                track_y = int(palm_center.y * frame_height)

        # 2. Fallback to Face Tracking if no hand is visible
        elif face_result.detections:
            for detection in face_result.detections:
                bbox = detection.bounding_box
                
                # Get center of the face bounding box (pixel coordinates in Tasks API)
                track_x = int(bbox.origin_x + bbox.width / 2)
                track_y = int(bbox.origin_y + bbox.height / 2)
                
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
    if 'arduino' in locals() and arduino.is_open:
        arduino.close()
    hand_detector.close()
    face_detector.close()