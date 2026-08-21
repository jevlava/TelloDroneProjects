import cv2
import numpy as np
import time
import mediapipe as mp
from djitellopy import tello

# ---------------------------------------------------------
# 1. INITIALIZE DRONE & VIDEO FEED (Prevents Display Lag)
# ---------------------------------------------------------
me = tello.Tello()
me.connect()
print(f"Battery: {me.get_battery()}%")

# Start video stream BEFORE takeoff to initialize camera pipeline immediately
me.streamon()
frame_read = me.get_frame_read()

# Frame dimensions
w, h = 360, 240

# Safe target distance range (Face area in pixels at 360x240 resolution)
# Area ~6000-7500 keeps the drone at a safe distance (~1.5m - 2m away)
fbRange = [6000, 7500]

# Gains: [Proportional, Derivative]
pid_yaw = [0.4, 0.3]
pid_ud = [0.4, 0.3]
pError_x = 0
pError_y = 0

# Warm up camera feed so window opens immediately
print("Warming up camera feed...")
for _ in range(30):
    img = frame_read.frame
    if img is not None:
        img = cv2.resize(img, (w, h))
        cv2.imshow("Tello Face Tracking HUD", img)
        cv2.waitKey(1)
    time.sleep(0.02)

# Take off once video feed is stable
print("Taking off...")
me.takeoff()
me.send_rc_control(0, 0, 20, 0)  # Gentle initial elevation rise
time.sleep(2.0)

# ---------------------------------------------------------
# 2. MEDIAPIPE FACE DETECTION SETUP
# ---------------------------------------------------------
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(
    model_selection=0,  # Short-range model (within 2 meters)
    min_detection_confidence=0.6  # Reduced false positives
)


def findFace(img):
    """
    Detects faces using MediaPipe.
    Fixes color channel issues by converting BGR -> RGB for detection,
    then keeping the image in BGR for OpenCV display.
    """
    # Convert BGR (OpenCV format) to RGB (MediaPipe format)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_detector.process(img_rgb)

    myFaceListC = []
    myFaceListArea = []

    if results.detections:
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = img.shape

            x = int(bboxC.xmin * iw)
            y = int(bboxC.ymin * ih)
            box_w = int(bboxC.width * iw)
            box_h = int(bboxC.height * ih)

            cx = x + box_w // 2
            cy = y + box_h // 2
            area = box_w * box_h

            # Draw shapes directly on original BGR image
            cv2.rectangle(img, (x, y), (x + box_w, y + box_h), (0, 255, 0), 2)
            cv2.circle(img, (cx, cy), 4, (0, 255, 0), cv2.FILLED)

            myFaceListC.append([cx, cy])
            myFaceListArea.append(area)

    if len(myFaceListArea) != 0:
        i = myFaceListArea.index(max(myFaceListArea))
        return img, [myFaceListC[i], myFaceListArea[i]]
    else:
        return img, [[0, 0], 0]



def trackFace(info, w, h, pid_yaw, pid_ud, pError_x, pError_y, img):
    """
    Calculates Yaw, Vertical (Up/Down), and Forward/Backward controls.
    Overlays flight status telemetry onto the screen.
    """
    area = info[1]
    x, y = info[0]

    fb = 0
    ud = 0
    speed_yaw = 0
    center_x, center_y = w // 2, h // 2

    # Draw Center Target Crosshair
    cv2.drawMarker(img, (center_x, center_y), (255, 255, 255),
                   markerType=cv2.MARKER_CROSS, markerSize=12, thickness=1)

    # SEARCH MODE (No face detected)
    if x == 0 and y == 0:
        me.send_rc_control(0, 0, 0, 0)

        # HUD overlays
        cv2.putText(img, "STATUS: SEARCHING", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
        cv2.putText(img, "ACTION: HOVERING", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(img, f"BATTERY: {me.get_battery()}%", (w - 110, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255),
                    1)
        return 0, 0

    # TRACKING MODE: Calculate errors
    error_x = x - center_x
    error_y = y - center_y

    # Yaw (Left/Right rotation) Control
    speed_yaw = pid_yaw[0] * error_x + pid_yaw[1] * (error_x - pError_x)
    speed_yaw = int(np.clip(speed_yaw, -80, 80))

    # Vertical (Up/Down altitude) Control
    speed_ud = -(pid_ud[0] * error_y + pid_ud[1] * (error_y - pError_y))
    ud = int(np.clip(speed_ud, -70, 70))

    # Distance (Forward/Backward) Control via Bounding Box Area
    if fbRange[0] <= area <= fbRange[1]:
        fb = 0
        dist_text = "SAFE DISTANCE"
    elif area > fbRange[1]:
        fb = -18  # Back up safely
        dist_text = "TOO CLOSE -> BACKING UP"
    elif area < fbRange[0] and area != 0:
        fb = 18  # Approach safely
        dist_text = "TOO FAR -> APPROACHING"

    # Line connecting frame center to face target center
    cv2.line(img, (center_x, center_y), (x, y), (0, 255, 255), 2)

    # Send RC Commands: (left_right, forward_backward, up_down, yaw)
    me.send_rc_control(0, fb, ud, speed_yaw)

    # ---------------------------------------------------------
    # HUD DISPLAY RENDER
    # ---------------------------------------------------------
    cv2.putText(img, "STATUS: TRACKING", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
    cv2.putText(img, f"NAV: {dist_text}", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(img, f"AREA: {area} px", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(img, f"BATTERY: {me.get_battery()}%", (w - 110, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    return error_x, error_y


# ---------------------------------------------------------
# 3. MAIN EXECUTION LOOP
# ---------------------------------------------------------
try:
    while True:
        img = frame_read.frame
        if img is None:
            continue

        img = cv2.resize(img, (w, h))

        # Detect face & calculate controls
        img, info = findFace(img)
        pError_x, pError_y = trackFace(info, w, h, pid_yaw, pid_ud, pError_x, pError_y, img)

        # Show HUD Frame
        cv2.imshow("Tello Face Tracking HUD", img)

        # Emergency Stop / Land on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Landing initiated...")
            me.send_rc_control(0, 0, 0, 0)
            me.land()
            break

except Exception as e:
    print(f"Error occurred: {e}")
    me.send_rc_control(0, 0, 0, 0)
    me.land()

finally:
    face_detector.close()
    cv2.destroyAllWindows()