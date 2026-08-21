import cv2
import numpy as np
import time
from djitellopy import Tello
import mediapipe as mp

# --- Setup MediaPipe Solutions (Optimized for CPU Speed) ---
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Reduced complexity to 0 and confidence to 0.60 to eliminate processing lag
pose = mp_pose.Pose(
    min_detection_confidence=0.60,
    min_tracking_confidence=0.60,
    model_complexity=0
)

# High-Visibility Drawing Styles
LANDMARK_STYLE = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3)
CONNECTION_STYLE = mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=2)

# --- Main Canvas & Control Setup ---
CAM_WIDTH, CAM_HEIGHT = 640, 480
SIDEBAR_WIDTH = 260
TOTAL_WIDTH = CAM_WIDTH + SIDEBAR_WIDTH

TARGET_LIPS_X = CAM_WIDTH // 2
TARGET_LIPS_Y = int(CAM_HEIGHT * 0.25)
OOB_Y_MARGIN = 55

TARGET_SHOULDER_WIDTH = 190
MIN_SHOULDER_WIDTH = 130
MAX_SHOULDER_WIDTH = 250

# --- Control Gains & Deadbands ---
KP_YAW = 0.15
KP_UP_DOWN = 0.30
KP_FORWARD = 0.25
DEADBAND_PIXELS = 18

smoothed_yaw = 0.0
ALPHA_YAW = 0.12
YAW_DEADBAND_PX = 45

IMPULSE_DURATION_STEP = 0.30
GESTURE_COOLDOWN = 0.8
GESTURE_HOLD_FRAMES = 4
gesture_frame_counter = 0
candidate_gesture = "NONE"

awaiting_neutral_release = False
is_flying = False
last_gesture_time = 0
impulse_end_time = 0
current_impulse_type = "NONE"
active_gesture = "NONE"
out_of_bounds = False
last_detected_display = ("NONE", 0)

# --- Initialize Tello Drone ---
tello = Tello()
tello.connect()
battery = tello.get_battery()
print(f"Battery: {battery}%")

if battery < 15:
    print("❌ Battery too low for flight. Exiting.")
    exit()

tello.streamoff()
tello.streamon()
frame_read = tello.get_frame_read()

print("🚀 Initiating Takeoff...")
tello.takeoff()
is_flying = True
takeoff_time = time.time()  # Track takeoff timestamp
GRACE_PERIOD_SEC = 3.0       # Ignore gestures for 3s after takeoff

# --- FLUSH STALE VIDEO FRAMES ---
# Clear queue accumulated during takeoff blocking call
for _ in range(20):
    _ = frame_read.frame
    time.sleep(0.01)


def detect_gestures_strict(landmarks):
    """Evaluates pose gestures on the mirrored frame."""
    l_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
    r_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
    l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    l_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
    r_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
    l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    r_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

    l_thumb = landmarks[mp_pose.PoseLandmark.LEFT_THUMB]
    r_thumb = landmarks[mp_pose.PoseLandmark.RIGHT_THUMB]
    l_pinky = landmarks[mp_pose.PoseLandmark.LEFT_PINKY]
    r_pinky = landmarks[mp_pose.PoseLandmark.RIGHT_PINKY]

    # Lowered visibility check threshold for practical tracking
    visible_pts = [l_wrist, r_wrist, l_shoulder, r_shoulder, l_elbow, r_elbow, l_hip, r_hip]
    if any(pt.visibility < 0.65 for pt in visible_pts):
        return "NONE"

    left_neutral = l_wrist.y > l_hip.y
    right_neutral = r_wrist.y > r_hip.y

    # 1. LAND_NOW: Both hands raised high
    if (l_wrist.y < l_shoulder.y - 0.28 and r_wrist.y < r_shoulder.y - 0.28) and \
       (l_elbow.y < l_shoulder.y - 0.12 and r_elbow.y < r_shoulder.y - 0.12):
        return "LAND_NOW"

    # 2. STEP_FORWARD
    shoulder_dist = np.hypot(l_shoulder.x - r_shoulder.x, l_shoulder.y - r_shoulder.y) + 1e-6
    l_span = np.hypot(l_thumb.x - l_pinky.x, l_thumb.y - l_pinky.y) / shoulder_dist
    r_span = np.hypot(r_thumb.x - r_pinky.x, r_thumb.y - r_pinky.y) / shoulder_dist

    both_raised = (l_wrist.y < l_shoulder.y - 0.08) and (r_wrist.y < r_shoulder.y - 0.08)
    fingers_spread = (l_span > 0.26) and (r_span > 0.26)

    if both_raised and fingers_spread:
        return "STEP_FORWARD"

    # 3. STEP_BACK
    l_crossed = (abs(l_wrist.y - r_shoulder.y) < 0.08) and (abs(l_wrist.x - r_shoulder.x) < 0.12)
    r_crossed = (abs(r_wrist.y - l_shoulder.y) < 0.08) and (abs(r_wrist.x - l_shoulder.x) < 0.12)
    if l_crossed and r_crossed:
        return "STEP_BACK"

    # 4. NUDGE_UP
    if (l_wrist.y < l_shoulder.y - 0.12 and l_wrist.y > l_shoulder.y - 0.25) and \
       (abs(l_wrist.x - l_shoulder.x) < 0.12) and right_neutral:
        return "NUDGE_UP"

    # 5. NUDGE_DOWN
    if (r_wrist.y < r_shoulder.y - 0.12 and r_wrist.y > r_shoulder.y - 0.25) and \
       (abs(r_wrist.x - r_shoulder.x) < 0.12) and left_neutral:
        return "NUDGE_DOWN"

    return "NONE"


def get_body_p_control(landmarks):
    global smoothed_yaw

    l_mouth = landmarks[mp_pose.PoseLandmark.MOUTH_LEFT]
    r_mouth = landmarks[mp_pose.PoseLandmark.MOUTH_RIGHT]
    l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    raw_cx = (l_mouth.x + r_mouth.x) * 0.5
    cx = int(raw_cx * CAM_WIDTH)
    cy = int(((l_mouth.y + r_mouth.y) * 0.5) * CAM_HEIGHT)

    shoulder_w = abs(int((l_shoulder.x - r_shoulder.x) * CAM_WIDTH))

    err_x = cx - TARGET_LIPS_X
    err_y = TARGET_LIPS_Y - cy
    err_w = TARGET_SHOULDER_WIDTH - shoulder_w

    if abs(err_x) < YAW_DEADBAND_PX:
        raw_yaw = 0.0
    else:
        effective_err_x = err_x - np.sign(err_x) * YAW_DEADBAND_PX
        raw_yaw = effective_err_x * KP_YAW

    smoothed_yaw = (ALPHA_YAW * raw_yaw) + ((1.0 - ALPHA_YAW) * smoothed_yaw)
    yaw = int(np.clip(smoothed_yaw, -18, 18))

    if abs(err_y) < DEADBAND_PIXELS: err_y = 0
    if abs(err_w) < DEADBAND_PIXELS: err_w = 0

    ud = int(np.clip(err_y * KP_UP_DOWN, -20, 20))
    fb = int(np.clip(err_w * KP_FORWARD, -18, 18))

    return yaw, ud, fb, cx, cy, shoulder_w


def draw_control_legend(canvas, current_gesture, is_oob):
    cv2.rectangle(canvas, (CAM_WIDTH, 0), (TOTAL_WIDTH, CAM_HEIGHT), (20, 20, 20), -1)
    cv2.line(canvas, (CAM_WIDTH, 0), (CAM_WIDTH, CAM_HEIGHT), (60, 60, 60), 2)

    header_color = (0, 0, 255) if is_oob else (255, 255, 255)
    header_text = "AUTO RE-CENTERING" if is_oob else "DISCRETE GESTURE LOCK"

    cv2.putText(canvas, header_text, (CAM_WIDTH + 15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, header_color, 2)
    cv2.line(canvas, (CAM_WIDTH + 15, 40), (TOTAL_WIDTH - 15, 40), (80, 80, 80), 1)

    guides = [
        ("LAND_NOW", "Both Hands High", "Land Drone"),
        ("STEP_FORWARD", "Both Open Hands", "Step Fwd (1x)"),
        ("STEP_BACK", "Crossed Arms (X)", "Step Back (1x)"),
        ("NUDGE_UP", "Left Hand High", "Step Up (1x)"),
        ("NUDGE_DOWN", "Right Hand High", "Step Down (1x)")
    ]

    start_y = 60
    row_height = 58

    for key, gesture_name, action in guides:
        is_active = (current_gesture == key)

        if is_active:
            cv2.rectangle(canvas, (CAM_WIDTH + 8, start_y - 14),
                          (TOTAL_WIDTH - 8, start_y + 26), (0, 140, 0), -1)
            text_color = (255, 255, 255)
            sub_color = (200, 255, 200)
        else:
            text_color = (220, 220, 220)
            sub_color = (130, 130, 130)

        cv2.putText(canvas, gesture_name, (CAM_WIDTH + 15, start_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.43, text_color, 1, cv2.LINE_AA)
        cv2.putText(canvas, f"-> {action}", (CAM_WIDTH + 15, start_y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, sub_color, 1, cv2.LINE_AA)

        start_y += row_height


try:
    while True:
        raw_frame = frame_read.frame
        if raw_frame is None:
            continue

        raw_frame = cv2.cvtColor(raw_frame, cv2.COLOR_RGB2BGR)
        frame = cv2.resize(raw_frame, (CAM_WIDTH, CAM_HEIGHT))

        display_frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb_frame)

        lr_speed, fb_speed, ud_speed, yaw_speed = 0, 0, 0, 0
        active_gesture = "NONE"
        now = time.time()

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            mp_drawing.draw_landmarks(
                display_frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=LANDMARK_STYLE,
                connection_drawing_spec=CONNECTION_STYLE
            )

            p_yaw, p_ud, p_fb, cx, cy, shoulder_w = get_body_p_control(landmarks)

            cv2.circle(display_frame, (cx, cy), 6, (0, 255, 255), -1)

            out_of_bounds = (abs(cy - TARGET_LIPS_Y) > OOB_Y_MARGIN) or \
                            (shoulder_w < MIN_SHOULDER_WIDTH or shoulder_w > MAX_SHOULDER_WIDTH)

            if out_of_bounds:
                yaw_speed = p_yaw
                ud_speed = p_ud
                fb_speed = p_fb
                current_impulse_type = "NONE"
                gesture_frame_counter = 0
                smoothed_yaw = 0.0
                awaiting_neutral_release = False
            else:
                # --- POST-TAKEOFF GRACE PERIOD CHECK ---
                if (now - takeoff_time) < GRACE_PERIOD_SEC:
                    raw_detected = "NONE"
                else:
                    raw_detected = detect_gestures_strict(landmarks)

                if awaiting_neutral_release:
                    if raw_detected == "NONE":
                        awaiting_neutral_release = False
                    candidate_gesture = "NONE"
                    gesture_frame_counter = 0
                else:
                    if raw_detected != "NONE" and raw_detected == candidate_gesture:
                        gesture_frame_counter += 1
                    else:
                        candidate_gesture = raw_detected
                        gesture_frame_counter = 1

                    confirmed_gesture = candidate_gesture if gesture_frame_counter >= GESTURE_HOLD_FRAMES else "NONE"

                    if confirmed_gesture == "LAND_NOW" and is_flying:
                        awaiting_neutral_release = True
                        last_detected_display = ("LAND_NOW", now + 2.0)
                        print("🛬 Landing Triggered by Gesture")
                        tello.land()
                        is_flying = False

                    elif confirmed_gesture != "NONE" and (now - last_gesture_time > GESTURE_COOLDOWN):
                        last_gesture_time = now
                        current_impulse_type = confirmed_gesture
                        last_detected_display = (confirmed_gesture, now + 1.5)
                        impulse_end_time = now + IMPULSE_DURATION_STEP
                        awaiting_neutral_release = True

                if now < impulse_end_time:
                    active_gesture = current_impulse_type
                    yaw_speed = 0

                    if current_impulse_type == "NUDGE_UP":
                        ud_speed = 22
                    elif current_impulse_type == "NUDGE_DOWN":
                        ud_speed = -22
                    elif current_impulse_type == "STEP_FORWARD":
                        fb_speed = 22
                    elif current_impulse_type == "STEP_BACK":
                        fb_speed = -22
                else:
                    current_impulse_type = "NONE"
                    yaw_speed = p_yaw
                    ud_speed = p_ud
                    fb_speed = p_fb

        # Clamp speed ranges
        lr_speed = int(np.clip(lr_speed, -25, 25))
        fb_speed = int(np.clip(fb_speed, -20, 20))
        ud_speed = int(np.clip(ud_speed, -20, 20))
        yaw_speed = int(np.clip(yaw_speed, -18, 18))

        combined_canvas = np.zeros((CAM_HEIGHT, TOTAL_WIDTH, 3), dtype=np.uint8)
        combined_canvas[0:CAM_HEIGHT, 0:CAM_WIDTH] = display_frame

        cv2.drawMarker(combined_canvas, (TARGET_LIPS_X, TARGET_LIPS_Y),
                       (255, 0, 0), cv2.MARKER_CROSS, 20, 2)

        cv2.line(combined_canvas, (0, TARGET_LIPS_Y - OOB_Y_MARGIN),
                 (CAM_WIDTH, TARGET_LIPS_Y - OOB_Y_MARGIN), (0, 165, 255), 1, cv2.LINE_AA)
        cv2.line(combined_canvas, (0, TARGET_LIPS_Y + OOB_Y_MARGIN),
                 (CAM_WIDTH, TARGET_LIPS_Y + OOB_Y_MARGIN), (0, 165, 255), 1, cv2.LINE_AA)

        if awaiting_neutral_release and (now >= impulse_end_time):
            cv2.rectangle(combined_canvas, (10, CAM_HEIGHT - 45), (CAM_WIDTH - 10, CAM_HEIGHT - 10), (0, 100, 200), -1)
            cv2.putText(combined_canvas, "ACTION EXECUTED - LOWER HANDS TO RESET", (20, CAM_HEIGHT - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

        elif now < last_detected_display[1]:
            gesture_text = f"GESTURE EXECUTED: {last_detected_display[0]}"
            cv2.rectangle(combined_canvas, (10, CAM_HEIGHT - 45), (CAM_WIDTH - 10, CAM_HEIGHT - 10), (0, 180, 0), -1)
            cv2.putText(combined_canvas, gesture_text, (20, CAM_HEIGHT - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        status_color = (0, 0, 255) if out_of_bounds else (0, 255, 0)
        status_label = "RE-CENTERING LOCK" if out_of_bounds else ("FLYING" if is_flying else "LANDED")

        cv2.putText(combined_canvas, f"Status: {status_label} | Bat: {tello.get_battery()}%",
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)

        draw_control_legend(combined_canvas, active_gesture, out_of_bounds)

        # Always send RC control while flying to maintain keep-alive
        if is_flying:
            tello.send_rc_control(lr_speed, fb_speed, ud_speed, yaw_speed)

        cv2.imshow("Tello Body-Centric Control Center", combined_canvas)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            if is_flying:
                tello.land()
            break

finally:
    tello.streamoff()
    cv2.destroyAllWindows()