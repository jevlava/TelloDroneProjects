import cv2
import time
import numpy as np
import mediapipe as mp
from djitellopy import Tello
from ultralytics import YOLO

# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------
# Load YOLO model for object detection
yolo_model = YOLO("yolov8n.pt")  # Lightweight nano model

# Initialize MediaPipe Pose and Hands
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
hands = mp_hands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# Connect to Tello Drone
tello = Tello()
tello.connect()
print(f"Battery: {tello.get_battery()}%")
tello.streamon()

# Safety setup
tello.takeoff()
tello.move_up(40)  # Move up initially to safe starting height

FRAME_WIDTH, FRAME_HEIGHT = 640, 480
CENTER_X, CENTER_Y = FRAME_WIDTH // 2, FRAME_HEIGHT // 2

# Control Gains (Simple Proportional Control)
PID_YAW = 0.4
PID_THROTTLE = 0.4
PID_PITCH = 0.3

# Target height ratio: upper body should take ~50% of vertical frame height
TARGET_UPPER_BODY_RATIO = 0.45

# State Machine
STATE_TRACKING = "TRACKING"
STATE_INSPECT_OBJECT = "INSPECT_OBJECT"
current_state = STATE_TRACKING
detected_object_name = ""


def is_thumbs_up(hand_landmarks, handedness_label):
    """Detects thumbs up gesture specifically on the Left Hand."""
    # Note: Handedness in MediaPipe can be mirrored depending on frame flipping
    if handedness_label != "Left":
        return False

    lm = hand_landmarks.landmark
    # Check if Thumb tip is above Thumb IP joint
    thumb_is_up = lm[4].y < lm[3].y and lm[3].y < lm[2].y

    # Check if other fingers are folded (tips below PIP joints)
    fingers_folded = (
            lm[8].y > lm[6].y and  # Index
            lm[12].y > lm[10].y and  # Middle
            lm[16].y > lm[14].y and  # Ring
            lm[20].y > lm[18].y  # Pinky
    )

    return thumb_is_up and fingers_folded


try:
    while True:
        frame = tello.get_frame_read().frame
        if frame is None:
            continue

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process Pose and Hand tracking
        pose_results = pose.process(rgb_frame)
        hand_results = hands.process(rgb_frame)

        # Base speeds
        lr, fb, ud, yv = 0, 0, 0, 0

        if current_state == STATE_TRACKING:
            if pose_results.pose_landmarks:
                landmarks = pose_results.pose_landmarks.landmark

                # 1. Lip Level Altitude Control
                # Lips keypoints: 9 (mouth_left), 10 (mouth_right)
                lip_left = landmarks[mp_pose.PoseLandmark.MOUTH_LEFT]
                lip_right = landmarks[mp_pose.PoseLandmark.MOUTH_RIGHT]

                lip_y = int(((lip_left.y + lip_right.y) / 2) * FRAME_HEIGHT)
                lip_x = int(((lip_left.x + lip_right.x) / 2) * FRAME_WIDTH)

                # Vertical Error (Lip altitude vs Center of Frame)
                error_y = CENTER_Y - lip_y
                ud = int(np.clip(error_y * PID_THROTTLE, -40, 40))

                # Yaw Error (Keep face horizontally centered)
                error_x = lip_x - CENTER_X
                yv = int(np.clip(error_x * PID_YAW, -40, 40))

                # 2. Upper Body Distance/Framing Control (Panning)
                # Shoulders to Hips distance gives upper body bounding ratio
                left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
                right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

                shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
                hip_y = (left_hip.y + right_hip.y) / 2
                upper_body_height = abs(hip_y - shoulder_y)

                # Distance Error (Adjust forward/backward to pan for upper body)
                error_dist = TARGET_UPPER_BODY_RATIO - upper_body_height
                fb = int(np.clip(error_dist * 100 * PID_PITCH, -35, 35))

                # Visual overlay
                cv2.circle(frame, (lip_x, lip_y), 6, (0, 255, 0), -1)
                cv2.putText(frame, "Lips Locked", (lip_x + 10, lip_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Send movement commands
            tello.send_rc_control(lr, fb, ud, yv)

            # 3. Check for Trigger (Left hand thumbs up)
            if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
                for hand_lms, handedness in zip(hand_results.multi_hand_landmarks, hand_results.multi_handedness):
                    label = handedness.classification[0].label
                    if is_thumbs_up(hand_lms, label):
                        print("Trigger Detected: Left Hand Thumbs Up!")
                        current_state = STATE_INSPECT_OBJECT
                        tello.send_rc_control(0, 0, 0, 0)  # Pause movement
                        time.sleep(0.5)

        elif current_state == STATE_INSPECT_OBJECT:
            # 4. Position Near Right Hand and Detect Object
            if pose_results.pose_landmarks:
                landmarks = pose_results.pose_landmarks.landmark
                right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

                rw_x = int(right_wrist.x * FRAME_WIDTH)
                rw_y = int(right_wrist.y * FRAME_HEIGHT)

                # Define Bounding Box around Right Hand area
                box_size = 140
                x1 = max(0, rw_x - box_size)
                y1 = max(0, rw_y - box_size)
                x2 = min(FRAME_WIDTH, rw_x + box_size)
                y2 = min(FRAME_HEIGHT, rw_y + box_size)

                hand_crop = frame[y1:y2, x1:x2]

                if hand_crop.size > 0:
                    # Run YOLO Object Detector on cropped region
                    results = yolo_model(hand_crop, verbose=False)
                    for r in results:
                        for box in r.boxes:
                            cls_id = int(box.cls[0])
                            detected_object_name = yolo_model.names[cls_id]
                            print(f"Identified Object: {detected_object_name}")
                            break

                # Draw ROI box around Right Hand
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"Object: {detected_object_name}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

                # Pulse forward slightly to simulate "moving closer"
                tello.send_rc_control(0, 15, 0, 0)
                time.sleep(1.0)
                tello.send_rc_control(0, 0, 0, 0)

            # Display result for 3 seconds, then return to tracking
            cv2.imshow("Tello Feed", frame)
            cv2.waitKey(3000)
            current_state = STATE_TRACKING

        # Render display window
        cv2.putText(frame, f"State: {current_state}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("Tello Feed", frame)

        # Emergency Land on 'q' or 'ESC'
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

finally:
    # Safe Landing Sequence
    tello.send_rc_control(0, 0, 0, 0)
    tello.land()
    tello.streamoff()
    cv2.destroyAllWindows()