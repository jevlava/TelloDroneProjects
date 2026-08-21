# utils/gestures.py

import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose


def detect_gestures(landmarks):
    """Parses pose landmarks into flight command strings."""
    l_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
    r_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
    l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    l_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
    r_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
    l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]

    # 1. Takeoff / Land Toggle (Both wrists high above shoulders)
    if l_wrist.y < l_shoulder.y - 0.15 and r_wrist.y < r_shoulder.y - 0.15:
        return "BOTH_HIGH"

    # 2. 360 Video Capture (Crossed wrists in front of chest)
    wrist_distance = np.hypot(l_wrist.x - r_wrist.x, l_wrist.y - r_wrist.y)
    if wrist_distance < 0.08 and l_wrist.y > l_shoulder.y and l_wrist.y < l_hip.y:
        return "CROSSED_WRISTS"

    # 3. T-Pose (Arms flat horizontal)
    left_arm_flat = abs(l_wrist.y - l_shoulder.y) < 0.08 and abs(l_elbow.y - l_shoulder.y) < 0.08
    right_arm_flat = abs(r_wrist.y - r_shoulder.y) < 0.08 and abs(r_elbow.y - r_shoulder.y) < 0.08
    if left_arm_flat and right_arm_flat:
        return "T_POSE"

    # 4. Altitude Controls
    if l_wrist.y < l_shoulder.y - 0.2:
        return "HIGH_LEFT_HAND"
    if l_wrist.y > l_hip.y:
        return "LOW_LEFT_HAND"

    # 5. Roll Controls
    if l_wrist.y < l_shoulder.y:
        return "LEFT_RAISED"
    if r_wrist.y < r_shoulder.y:
        return "RIGHT_RAISED"

    return "NONE"