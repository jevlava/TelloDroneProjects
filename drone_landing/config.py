# config.py

# Video Stream Settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_CENTER_X = FRAME_WIDTH // 2
TARGET_CENTER_Y = FRAME_HEIGHT // 2

# Deadzones (in pixels) - Drone ignores errors smaller than these values to avoid jittering
DEADZONE_X = 30
DEADZONE_Y = 30

# Proportional Controller Gains (P-Gains for adjusting reaction speed)
KP_YAW = 0.25    # Controls rotational responsiveness
KP_PITCH = 0.20  # Controls forward/backward responsiveness

# Initial Settings
DEFAULT_MODE = 1  # 1: Mouse/Laptop Mode | 2: Hand Gesture Mode