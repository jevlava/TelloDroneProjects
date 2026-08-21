# config.py

# --- Camera & Display ---
WIDTH = 640
HEIGHT = 480
FRAME_CENTER_X = WIDTH // 2
FRAME_CENTER_Y = HEIGHT // 2

# --- P-Controller Gains ---
KP_YAW = 0.25
KP_UP_DOWN = 0.35
KP_FORWARD = 0.40

# --- Target Distance Metrics ---
TARGET_SHOULDER_WIDTH = 130  # Target width in pixels for forward/backward tracking

# --- Gesture Timers (seconds) ---
TAKEOFF_LAND_COOLDOWN = 2.5
PANORAMA_COOLDOWN = 3.0