import os

# Base Directory & Category-Specific Subfolders
BASE_DIR = "tello_captures"
PICTURES_DIR = os.path.join(BASE_DIR, "pictures")
PANORAMAS_DIR = os.path.join(BASE_DIR, "panoramas")
BURSTS_DIR = os.path.join(BASE_DIR, "bursts")
VIDEOS_DIR = os.path.join(BASE_DIR, "360_videos")

for folder in [PICTURES_DIR, PANORAMAS_DIR, BURSTS_DIR, VIDEOS_DIR]:
    os.makedirs(folder, exist_ok=True)

# Frame and Motion Configuration
FRAME_W, FRAME_H = 480, 320
FB_RANGE = [6000, 9000]  # Target area range
PID_YAW = [0.22, 0.15]
PID_UD = [0.22, 0.15]
DEADBAND = 15
REQUIRED_LOCK_DURATION = 1.5
CRITICAL_BATTERY_LEVEL = 20