import time
import os
import cv2
import numpy as np
import mediapipe as mp
from djitellopy import Tello

from config import (
    FRAME_W, FRAME_H, FB_RANGE, PID_YAW, PID_UD, DEADBAND,
    REQUIRED_LOCK_DURATION, CRITICAL_BATTERY_LEVEL, PICTURES_DIR
)
from utils import draw_hud_guide
from gesture_detector import (
    is_peace_sign, is_thumbs_up, is_shaka_sign, is_okay_sign
)
from flight_routines import (
    execute_180_panorama, execute_roll_panorama,
    execute_shaka_burst_sequence, execute_360_video_sweep
)

# PID State tracking local to main control pipeline
p_error_x = 0
p_error_y = 0

def track_face(tello, face_center, face_area, frame_w, frame_h):
    global p_error_x, p_error_y

    if face_center is None or face_area == 0:
        tello.send_rc_control(0, 0, 0, 0)
        return "HOVERING"

    cx, cy = face_center
    center_x, center_y = frame_w // 2, frame_h // 2

    error_x = cx - center_x
    error_y = cy - center_y

    if abs(error_x) < DEADBAND:
        error_x = 0
    if abs(error_y) < DEADBAND:
        error_y = 0

    speed_yaw = PID_YAW[0] * error_x + PID_YAW[1] * (error_x - p_error_x)
    speed_yaw = int(np.clip(speed_yaw, -50, 50))

    speed_ud = -(PID_UD[0] * error_y + PID_UD[1] * (error_y - p_error_y))
    speed_ud = int(np.clip(speed_ud, -50, 50))

    if FB_RANGE[0] <= face_area <= FB_RANGE[1]:
        fb = 0
        dist_text = "SAFE DISTANCE"
    elif face_area > FB_RANGE[1]:
        fb = -14
        dist_text = "TOO CLOSE -> BACKING UP"
    else:
        fb = 14
        dist_text = "TOO FAR -> APPROACHING"

    p_error_x = error_x
    p_error_y = error_y

    tello.send_rc_control(0, fb, speed_ud, speed_yaw)
    return dist_text


def main():
    global p_error_x, p_error_y

    mp_face_detection = mp.solutions.face_detection
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    tello = Tello()
    tello.connect()
    print(f"Connected! Battery: {tello.get_battery()}%")

    initial_battery = tello.get_battery()
    if initial_battery <= CRITICAL_BATTERY_LEVEL:
        print(f"CRITICAL BATTERY ({initial_battery}%): Aborting takeoff for safety.")
        tello.streamoff()
        return

    tello.streamon()
    frame_read = tello.get_frame_read()

    print("Warming up camera feed...")
    for _ in range(30):
        img = frame_read.frame
        if img is not None:
            img = cv2.resize(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), (FRAME_W, FRAME_H))
            cv2.imshow("Tello Control Center", img)
            cv2.waitKey(1)
        time.sleep(0.02)

    print("Taking off...")
    tello.takeoff()
    tello.send_rc_control(0, 0, 20, 0)
    time.sleep(2.0)

    last_capture_time = 0
    is_executing_action = False
    photo_feedback_time = 0

    face_locked = False
    face_detect_start_time = None

    try:
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6) as face_detection, \
             mp_hands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6) as hands:

            while True:
                current_battery = tello.get_battery()
                if current_battery <= CRITICAL_BATTERY_LEVEL:
                    print(f"CRITICAL BATTERY ({current_battery}%): Emergency landing initiated!")
                    break

                raw_rgb = frame_read.frame
                if raw_rgb is None or raw_rgb.size == 0:
                    continue

                bgr_frame = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2BGR)
                display_frame = cv2.resize(bgr_frame, (FRAME_W, FRAME_H))
                h, w, _ = display_frame.shape

                rgb_for_mp = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                face_results = face_detection.process(rgb_for_mp)

                face_center = None
                face_area = 0
                curr_time = time.time()
                lock_progress = 0.0

                if face_results.detections:
                    detection = face_results.detections[0]
                    bboxC = detection.location_data.relative_bounding_box
                    x = int(bboxC.xmin * w)
                    y = int(bboxC.ymin * h)
                    box_w = int(bboxC.width * w)
                    box_h = int(bboxC.height * h)

                    cx = x + box_w // 2
                    cy = y + box_h // 2
                    face_center = (cx, cy)
                    face_area = box_w * box_h

                    box_color = (0, 255, 0) if face_locked else (0, 215, 255)
                    cv2.rectangle(display_frame, (x, y), (x + box_w, y + box_h), box_color, 2)
                    cv2.circle(display_frame, (cx, cy), 3, (0, 255, 0), cv2.FILLED)

                    if not face_locked:
                        if face_detect_start_time is None:
                            face_detect_start_time = curr_time

                        elapsed = curr_time - face_detect_start_time
                        lock_progress = min(1.0, elapsed / REQUIRED_LOCK_DURATION)

                        if elapsed >= REQUIRED_LOCK_DURATION:
                            face_locked = True
                            print("--- FACE LOCKED! Hand Gestures Enabled ---")
                    else:
                        lock_progress = 1.0
                else:
                    if not face_locked:
                        face_detect_start_time = None
                        lock_progress = 0.0

                peace_detected, thumbs_up_detected, shaka_detected, ok_detected = False, False, False, False

                if face_locked:
                    hand_results = hands.process(rgb_for_mp)

                    if hand_results.multi_hand_landmarks:
                        for hand_landmarks in hand_results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(display_frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                            if is_peace_sign(hand_landmarks):
                                peace_detected = True
                            elif is_thumbs_up(hand_landmarks):
                                thumbs_up_detected = True
                            elif is_shaka_sign(hand_landmarks):
                                shaka_detected = True
                            elif is_okay_sign(hand_landmarks):
                                ok_detected = True

                key = cv2.waitKey(1) & 0xFF

                if peace_detected and not is_executing_action and (curr_time - last_capture_time > 3.0):
                    is_executing_action = True
                    filename = os.path.join(PICTURES_DIR, f"snap_{int(curr_time)}.jpg")
                    cv2.imwrite(filename, bgr_frame)
                    print(f"SUCCESS: Snapshot saved -> {filename}")

                    last_capture_time = curr_time
                    photo_feedback_time = curr_time
                    cv2.rectangle(display_frame, (0, 0), (w, h), (255, 255, 255), 14)
                    is_executing_action = False

                if curr_time - photo_feedback_time < 1.5:
                    overlay = display_frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, 30), (0, 180, 0), -1)
                    cv2.addWeighted(overlay, 0.6, display_frame, 0.4, 0, display_frame)
                    cv2.putText(display_frame, "PHOTO CAPTURED!", (w // 2 - 60, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)

                elif thumbs_up_detected and not is_executing_action and (curr_time - last_capture_time > 4.0):
                    is_executing_action = True
                    cv2.putText(display_frame, "CAPTURING BURST...", (w // 2 - 60, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)
                    cv2.imshow("Tello Control Center", display_frame)
                    cv2.waitKey(200)

                    execute_shaka_burst_sequence(tello, frame_read)
                    p_error_x, p_error_y = 0, 0
                    last_capture_time = time.time()
                    is_executing_action = False

                elif shaka_detected and not is_executing_action and (curr_time - last_capture_time > 4.0):
                    is_executing_action = True
                    cv2.putText(display_frame, "CAPTURING FISHEYE PANO...", (w // 2 - 80, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)
                    cv2.imshow("Tello Control Center", display_frame)
                    cv2.waitKey(200)

                    execute_roll_panorama(tello, frame_read)
                    p_error_x, p_error_y = 0, 0
                    last_capture_time = time.time()
                    is_executing_action = False

                elif ok_detected and not is_executing_action and (curr_time - last_capture_time > 4.0):
                    is_executing_action = True
                    cv2.putText(display_frame, "RECORDING 360 VIDEO...", (w // 2 - 70, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)
                    cv2.imshow("Tello Control Center", display_frame)
                    cv2.waitKey(200)

                    execute_360_video_sweep(tello, frame_read)
                    p_error_x, p_error_y = 0, 0
                    last_capture_time = time.time()
                    is_executing_action = False

                elif key == ord('p') and not is_executing_action and (curr_time - last_capture_time > 4.0):
                    is_executing_action = True
                    cv2.putText(display_frame, "CAPTURING 180 PANO...", (w // 2 - 65, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 2)
                    cv2.imshow("Tello Control Center", display_frame)
                    cv2.waitKey(200)

                    execute_180_panorama(tello, frame_read)
                    p_error_x, p_error_y = 0, 0
                    last_capture_time = time.time()
                    is_executing_action = False

                nav_status = "HOVERING"
                if not is_executing_action:
                    nav_status = track_face(tello, face_center, face_area, w, h)

                draw_hud_guide(display_frame, tello.get_battery(), face_center is not None, face_locked,
                               lock_progress, nav_status, face_area)

                cv2.imshow("Tello Control Center", display_frame)

                if key in (ord('q'), 27):
                    print("Landing initiated...")
                    break

    except Exception as e:
        print(f"Error occurred during flight execution: {e}")

    finally:
        tello.send_rc_control(0, 0, 0, 0)
        tello.land()
        tello.streamoff()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()