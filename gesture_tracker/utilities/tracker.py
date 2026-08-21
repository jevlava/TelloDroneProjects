# utils/tracker.py

import numpy as np
import mediapipe as mp
import config

mp_pose = mp.solutions.pose


def get_body_p_control(landmarks):
    """Calculates RC velocities to center the drone on the user's body."""
    l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]

    # Calculate pixel position of central torso
    cx = int(((l_shoulder.x + r_shoulder.x) / 2) * config.WIDTH)
    cy = int(((l_shoulder.y + l_hip.y) / 2) * config.HEIGHT)
    shoulder_w = abs(int((l_shoulder.x - r_shoulder.x) * config.WIDTH))

    # Calculate tracking speeds
    yaw_speed = int(np.clip((cx - config.FRAME_CENTER_X) * config.KP_YAW, -40, 40))
    ud_speed = int(np.clip((config.FRAME_CENTER_Y - cy) * config.KP_UP_DOWN, -40, 40))
    fb_speed = int(np.clip((config.TARGET_SHOULDER_WIDTH - shoulder_w) * config.KP_FORWARD, -35, 35))

    return yaw_speed, ud_speed, fb_speed, cx, cy