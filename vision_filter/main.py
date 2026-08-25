import cv2
import numpy as np
import math
from djitellopy import tello
from cvzone.HandTrackingModule import HandDetector
from cvzone.PoseModule import PoseDetector

# -------------------------------------------------------------------------
# 1. INITIALIZATION
# -------------------------------------------------------------------------
me = tello.Tello()
me.connect(wait_for_state=False)
print(f"Battery: {me.get_battery()}%")

me.streamon()

# Initialize Hand Detector and Pose Detector
hand_detector = HandDetector(detectionCon=0.7, maxHands=1)
pose_detector = PoseDetector(detectionCon=0.7, trackCon=0.7)

# Active filter mode state
# 0: Original, 1: Dynamic Blur, 2: Heart Filter, 3: Cyberpunk HUD, 4: Thermal/Jet
active_filter = 0
hearts = []

print("\n--- TELLO ARM-ANGLE DYNAMIC FILTERS ---")
print("Press '0': Normal Feed")
print("Press '1': Dynamic Blur (Arm straightens = heavier blur)")
print("Press '2': Heart Filter (Arm straightens = bigger & faster hearts)")
print("Press '3': Cyberpunk HUD (Arm straightens = HUD expands)")
print("Press '4': Simulated Thermal (Arm straightens = intensity boost)")
print("Press 'f': Cycle Filters")
print("Press 'q': Quit\n")


# Helper function to draw hearts
def draw_heart(img, center, size, color):
    x, y = center
    pts = []
    for i in range(0, 360, 10):
        rad = math.radians(i)
        hx = 16 * (math.sin(rad) ** 3)
        hy = -(13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad))
        pts.append([int(x + hx * size), int(y + hy * size)])
    pts = np.array(pts, np.int32)
    cv2.fillPoly(img, [pts], color)


# -------------------------------------------------------------------------
# 2. MAIN PROCESSING LOOP
# -------------------------------------------------------------------------
while True:
    img = me.get_frame_read().frame
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = cv2.resize(img, (640, 480))
    h, w, _ = img.shape

    # -------------------------------------------------------------------------
    # ARM ANGLE DETECTION (MediaPipe Pose)
    # -------------------------------------------------------------------------
    # Find pose without drawing full body skeleton overlay
    img = pose_detector.findPose(img, draw=False)
    lmList, bboxInfo = pose_detector.findPosition(img, draw=False)

    # Default intensity multiplier if no arm is detected
    intensity = 0.5
    elbow_angle = 90

    if lmList:
        # Landmark indices for Right Arm: Shoulder (12), Elbow (14), Wrist (16)
        # (You can also use Left Arm: 11, 13, 15)
        angle, img = pose_detector.findAngle(12, 14, 16, img, draw=False)
        elbow_angle = angle

        # Map elbow angle (~40 degrees bent to ~170 degrees straight) -> (0.05 to 1.20 intensity)
        intensity = np.interp(elbow_angle, [40, 170], [0.05, 1.20])
        intensity = float(np.clip(intensity, 0.05, 1.20))

    # -------------------------------------------------------------------------
    # HAND GESTURE DETECTION (MediaPipe Hands)
    # -------------------------------------------------------------------------
    hands, _ = hand_detector.findHands(img, draw=False)
    fingertip_pos = None

    if hands:
        hand = hands[0]
        fingers = hand_detector.fingersUp(hand)

        # Gesture mode switches:
        if fingers == [0, 1, 0, 0, 0]:  # Pointing Index -> Heart Filter
            active_filter = 2
            fingertip_pos = (hand["lmList"][8][0], hand["lmList"][8][1])
        elif fingers == [0, 1, 1, 0, 0]:  # Peace Sign -> HUD Filter
            active_filter = 3
        elif fingers == [1, 1, 1, 1, 1]:  # Open Palm -> Thermal Filter
            active_filter = 4

    # -------------------------------------------------------------------------
    # FILTER RENDERING WITH DYNAMIC INTENSITY
    # -------------------------------------------------------------------------
    processed_img = img.copy()

    # MODE 0: Original RGB
    if active_filter == 0:
        filter_name = "Original"

    # MODE 1: Dynamic Gaussian Blur (Intensity scales kernel size)
    elif active_filter == 1:
        # Kernel size must be an odd integer (e.g., 3x3 up to 61x61)
        ksize = int(intensity * 50)
        if ksize % 2 == 0:
            ksize += 1
        ksize = max(3, ksize)
        processed_img = cv2.GaussianBlur(img, (ksize, ksize), 0)
        filter_name = f"Dynamic Blur ({int(intensity * 100)}%)"

    # MODE 2: Heart Filter (Intensity scales heart size & spawn speed)
    elif active_filter == 2:
        overlay = processed_img.copy()

        # Spawn heart at fingertip or background
        if fingertip_pos:
            hearts.append({"x": fingertip_pos[0], "y": fingertip_pos[1], "size": intensity * 1.5})
        elif len(hearts) < 10:
            hearts.append({"x": np.random.randint(50, w - 50), "y": h + 20, "size": intensity * 1.2})

        for heart in hearts[:]:
            draw_heart(overlay, (int(heart["x"]), int(heart["y"])), heart["size"], (147, 20, 255))
            heart["y"] -= int(5 * intensity) + 1  # Float speed scales with arm extension
            if heart["y"] < -30:
                hearts.remove(heart)

        cv2.addWeighted(overlay, min(1.0, 0.4 + intensity * 0.5), processed_img, 0.5, 0, processed_img)
        filter_name = f"Hearts ({int(intensity * 100)}% Size/Speed)"

    # MODE 3: Cyberpunk HUD (Intensity scales crosshair & reticle radius)
    elif active_filter == 3:
        cx, cy = w // 2, h // 2
        radius = int(30 * intensity) + 10
        line_len = int(60 * intensity) + 20

        cv2.circle(processed_img, (cx, cy), radius, (255, 255, 0), 2)
        cv2.line(processed_img, (cx - line_len, cy), (cx + line_len, cy), (255, 255, 0), 1)
        cv2.line(processed_img, (cx, cy - line_len), (cx, cy + line_len), (255, 255, 0), 1)

        if hands:
            bbox = hands[0]['bbox']
            cv2.rectangle(processed_img, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 0, 255), 2)

        filter_name = f"Cyberpunk HUD (Scale: {int(intensity * 100)}%)"

    # MODE 4: Simulated Thermal Color Map (Intensity blends thermal with raw image)
    elif active_filter == 4:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

        # Blend factor driven by arm extension (5% to 120% full effect)
        blend_factor = min(1.0, intensity)
        processed_img = cv2.addWeighted(thermal, blend_factor, img, 1.0 - blend_factor, 0)
        filter_name = f"Thermal Blend ({int(intensity * 100)}%)"

    # -------------------------------------------------------------------------
    # OSD OVERLAY
    # -------------------------------------------------------------------------
    # Visual intensity bar on screen
    bar_y = int(np.interp(intensity, [0.05, 1.20], [400, 150]))
    cv2.rectangle(processed_img, (580, 150), (610, 400), (50, 50, 50), 2)
    cv2.rectangle(processed_img, (580, bar_y), (610, 400), (0, 255, 0), -1)

    cv2.putText(processed_img, f"Filter: {filter_name}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(processed_img, f"Arm Angle: {int(elbow_angle)}deg", (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(processed_img, f"Intensity: {int(intensity * 100)}%", (520, 420),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow("Tello Arm & Gesture Camera Feed", processed_img)

    # -------------------------------------------------------------------------
    # KEYBOARD CONTROLS
    # -------------------------------------------------------------------------
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in [ord('0'), ord('1'), ord('2'), ord('3'), ord('4')]:
        active_filter = int(chr(key))
    elif key == ord('f'):
        active_filter = (active_filter + 1) % 5

# -------------------------------------------------------------------------
# CLEANUP
# -------------------------------------------------------------------------
cv2.destroyAllWindows()
me.streamoff()