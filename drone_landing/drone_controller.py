# drone_controller.py
import numpy as np
import cv2
from config import TARGET_CENTER_X, TARGET_CENTER_Y, DEADZONE_X, DEADZONE_Y, KP_YAW, KP_PITCH

def process_alignment(frame, bbox, is_flying):
    """
    Calculates error between the target center and frame center,
    returning flight speed values: (yaw, pitch, is_aligned)
    """
    x, y, w, h = [int(v) for v in bbox]
    cx, cy = x + w // 2, y + h // 2

    # Draw visual feedback box and vectors
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
    cv2.line(frame, (TARGET_CENTER_X, TARGET_CENTER_Y), (cx, cy), (255, 0, 0), 2)

    # Calculate distance error from center screen
    error_x = cx - TARGET_CENTER_X
    error_y = cy - TARGET_CENTER_Y

    yaw_speed = 0
    pitch_speed = 0

    # Calculate Yaw (Rotational alignment)
    if abs(error_x) > DEADZONE_X:
        yaw_speed = int(np.clip(KP_YAW * error_x, -40, 40))

    # Calculate Pitch (Forward/Backward alignment)
    if abs(error_y) > DEADZONE_Y:
        pitch_speed = int(np.clip(-KP_PITCH * error_y, -30, 30))

    # Check if target is perfectly centered within deadzone limits
    is_aligned = abs(error_x) <= DEADZONE_X and abs(error_y) <= DEADZONE_Y

    return yaw_speed, pitch_speed, is_aligned