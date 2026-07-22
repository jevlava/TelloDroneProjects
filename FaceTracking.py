"""
Project: MediaPipe Tasks Face & Peace Sign Detector
Description: Real-time face tracking and peace sign gesture photo trigger
             using the MediaPipe Tasks Vision API (MediaPipe 0.10+).
"""

import os
import time
import urllib.request
import cv2
import mediapipe as mp

# MediaPipe Tasks Imports
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Model paths and direct download URLs
FACE_MODEL_PATH = "face_landmarker.task"
HAND_MODEL_PATH = "hand_landmarker.task"

FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

# Standard hand skeleton connections for drawing lines between joints
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),    # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),  # Ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky & Palm
]

# Output directory for captured photos
output_dir = "peace_sign_captures"
os.makedirs(output_dir, exist_ok=True)


def download_models_if_missing():
    """Downloads required MediaPipe model task files if not present locally."""
    models = {
        FACE_MODEL_PATH: FACE_MODEL_URL,
        HAND_MODEL_PATH: HAND_MODEL_URL,
    }
    for path, url in models.items():
        if not os.path.exists(path):
            print(f"[INFO] Model '{path}' not found. Downloading...")
            urllib.request.urlretrieve(url, path)
            print(f"[INFO] Successfully downloaded '{path}'.")


def is_peace_sign(hand_landmarks):
    """Checks if the detected hand gesture is a peace sign.

    Index (8) and Middle (12) extended; Ring (16) and Pinky (20) curled.
    """
    index_extended = hand_landmarks[8].y < hand_landmarks[6].y
    middle_extended = hand_landmarks[12].y < hand_landmarks[10].y
    ring_curled = hand_landmarks[16].y > hand_landmarks[14].y
    pinky_curled = hand_landmarks[20].y > hand_landmarks[18].y

    return index_extended and middle_extended and ring_curled and pinky_curled


def draw_hand_skeleton(frame, hand_landmarks, width, height):
    """Draws skeleton lines and joint keypoints over detected hands."""
    coords = [(int(lm.x * width), int(lm.y * height)) for lm in hand_landmarks]

    # Draw connection lines
    for p1, p2 in HAND_CONNECTIONS:
        cv2.line(frame, coords[p1], coords[p2], (0, 255, 0), 2)

    # Draw joint points
    for cx, cy in coords:
        cv2.circle(frame, (cx, cy), 4, (0, 215, 255), -1)


def create_detectors():
    """Builds Face and Hand landmarker tasks using RunningMode.VIDEO."""
    # 1. Face Landmarker setup
    base_options_face = python.BaseOptions(model_asset_path=FACE_MODEL_PATH)
    options_face = vision.FaceLandmarkerOptions(
        base_options=base_options_face,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
    )
    face_landmarker = vision.FaceLandmarker.create_from_options(options_face)

    # 2. Hand Landmarker setup
    base_options_hand = python.BaseOptions(model_asset_path=HAND_MODEL_PATH)
    options_hand = vision.HandLandmarkerOptions(
        base_options=base_options_hand,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
    )
    hand_landmarker = vision.HandLandmarker.create_from_options(options_hand)

    return face_landmarker, hand_landmarker


def main():
    # Ensure task models exist before starting
    download_models_if_missing()

    cap = cv2.VideoCapture(0)
    last_capture_time = 0
    cooldown_seconds = 2.0

    face_landmarker, hand_landmarker = create_detectors()

    print("Camera active. Show a peace sign (✌️) to take a picture! Press 'q' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Failed to grab camera frame.")
            break

        # Mirror frame for intuitive interaction
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Clean copy for raw picture saving (no overlays)
        clean_frame = frame.copy()

        # Convert BGR to RGB MediaPipe Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Monotonic timestamp required by RunningMode.VIDEO
        frame_timestamp_ms = time.monotonic_ns() // 1_000_000

        # Run inference using Tasks API
        face_result = face_landmarker.detect_for_video(mp_image, frame_timestamp_ms)
        hand_result = hand_landmarker.detect_for_video(mp_image, frame_timestamp_ms)

        # --- Draw Face Bounding Box ---
        if face_result.face_landmarks:
            for face_landmarks in face_result.face_landmarks:
                x_coords = [lm.x * w for lm in face_landmarks]
                y_coords = [lm.y * h for lm in face_landmarks]

                xmin, xmax = int(min(x_coords)), int(max(x_coords))
                ymin, ymax = int(min(y_coords)), int(max(y_coords))

                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    "Face Tracked",
                    (xmin, max(ymin - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

        # --- Track Hands & Detect Peace Sign ---
        peace_detected = False
        if hand_result.hand_landmarks:
            for hand_landmarks in hand_result.hand_landmarks:
                draw_hand_skeleton(frame, hand_landmarks, w, h)

                if is_peace_sign(hand_landmarks):
                    peace_detected = True

        # --- Trigger Photo Capture ---
        current_time = time.time()
        if peace_detected:
            cv2.putText(
                frame,
                "PEACE SIGN DETECTED!",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                3,
            )

            if current_time - last_capture_time > cooldown_seconds:
                last_capture_time = current_time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(output_dir, f"peace_capture_{timestamp}.jpg")

                # Save raw clean frame
                cv2.imwrite(filename, clean_frame)
                print(f"[CAPTURED] Picture saved to: {filename}")

        # Display output window
        cv2.imshow("MediaPipe Tasks Tracker", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Cleanup resources
    face_landmarker.close()
    hand_landmarker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()