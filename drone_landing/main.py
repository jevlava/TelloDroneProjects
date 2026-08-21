# program is still in progress




# main.py
import cv2
from djitellopy import Tello

# Import internal modules
from config import FRAME_WIDTH, FRAME_HEIGHT, DEFAULT_MODE
from tracker import create_tracker
from gestures import GestureAnalyzer
from hud import draw_hud
from drone_controller import process_alignment

# Global Variables for Mouse Callback Events
selecting_roi = False
roi_start = (0, 0)
roi_end = (0, 0)
new_mouse_bbox = None


def mouse_callback(event, x, y, flags, param):
    """Mouse Event Handler for interactive box selection."""
    global roi_start, roi_end, selecting_roi, new_mouse_bbox

    if event == cv2.EVENT_LBUTTONDOWN:
        selecting_roi = True
        roi_start = (x, y)
        roi_end = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE and selecting_roi:
        roi_end = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        selecting_roi = False
        roi_end = (x, y)
        w = abs(roi_start[0] - roi_end[0])
        h = abs(roi_start[1] - roi_end[1])
        x_min = min(roi_start[0], roi_end[0])
        y_min = min(roi_start[1], roi_end[1])

        if w > 10 and h > 10:
            new_mouse_bbox = (x_min, y_min, w, h)


def main():
    global new_mouse_bbox

    # 1. Initialize Drone
    drone = Tello()
    drone.connect()
    drone.streamoff()
    drone.streamon()
    print(f"[INFO] Drone Connected! Battery: {drone.get_battery()}%")

    # 2. Initialize Helper Class Instances
    gesture_analyzer = GestureAnalyzer()

    # 3. GUI Window Setup
    window_name = "Tello Landing Control Center"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    # State Variables
    current_mode = DEFAULT_MODE
    tracker = None
    tracking_active = False
    is_flying = False
    auto_descending = False

    frame_read = drone.get_frame_read()

    try:
        while True:
            frame = frame_read.frame
            if frame is None:
                continue

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            lr, fb, ud, yv = 0, 0, 0, 0

            # -------------------------------------------------------------
            # MODE 1: MOUSE SELECTION HANDLING
            # -------------------------------------------------------------
            if current_mode == 1:
                if new_mouse_bbox is not None:
                    tracker = create_tracker()
                    tracker.init(frame, new_mouse_bbox)
                    tracking_active = True
                    new_mouse_bbox = None
                    print("[MODE 1] Target locked via mouse drag.")

                if selecting_roi:
                    cv2.rectangle(frame, roi_start, roi_end, (255, 0, 0), 2)

            # -------------------------------------------------------------
            # MODE 2: HAND GESTURE HANDLING
            # -------------------------------------------------------------
            elif current_mode == 2:
                gesture, coords = gesture_analyzer.process_frame(frame)

                if coords:
                    cv2.putText(frame, f"GESTURE: {gesture}", (FRAME_WIDTH - 220, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                    # Pointing / Open Palm -> Shows Target Indicator
                    if gesture in ["OPEN_PALM", "POINTING"] and not auto_descending:
                        cv2.circle(frame, coords, 10, (255, 0, 255), -1)

                    # Fist Gesture -> Lock Target Box on Pointing finger location
                    elif gesture == "FIST" and not tracking_active:
                        w, h = 80, 80
                        x_min = max(0, coords[0] - w // 2)
                        y_min = max(0, coords[1] - h // 2)
                        bbox = (x_min, y_min, w, h)

                        tracker = create_tracker()
                        tracker.init(frame, bbox)
                        tracking_active = True
                        print(f"[MODE 2] Lock Gesture detected! Target locked at {bbox}")

            # -------------------------------------------------------------
            # AUTONOMOUS ALIGNMENT & DESCENT CONTROL
            # -------------------------------------------------------------
            if tracking_active and tracker is not None:
                success, bbox = tracker.update(frame)

                if success:
                    yv, fb, is_aligned = process_alignment(frame, bbox, is_flying)

                    if is_aligned:
                        cv2.putText(frame, "TARGET ALIGNED! DESCENDING...", (FRAME_WIDTH // 2 - 150, 40),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        if is_flying:
                            auto_descending = True
                            ud = -20  # Descend speed

                            # Execute final landing at low altitude
                            if drone.get_height() <= 30:
                                drone.land()
                                is_flying = False
                                tracking_active = False
                                auto_descending = False
                else:
                    cv2.putText(frame, "TRACKING LOST", (15, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    tracking_active = False

            # Render HUD Overlays
            draw_hud(frame, drone, current_mode, tracking_active, auto_descending)

            # Send Control Signals to Drone
            if is_flying:
                drone.send_rc_control(lr, fb, ud, yv)

            cv2.imshow(window_name, frame)

            # Keybindings
            key = cv2.waitKey(1) & 0xFF
            if key == ord('1'):
                current_mode = 1
                tracking_active = False
                print("[MODE SWITCH] Mode 1 Activated")
            elif key == ord('2'):
                current_mode = 2
                tracking_active = False
                print("[MODE SWITCH] Mode 2 Activated")
            elif key == ord('t') and not is_flying:
                drone.takeoff()
                is_flying = True
            elif key == ord('l') and is_flying:
                drone.land()
                is_flying = False
                tracking_active = False
            elif key == ord('r'):
                tracking_active = False
                tracker = None
                auto_descending = False
            elif key == 27 or key == ord('q'):  # ESC or 'Q'
                if is_flying:
                    drone.land()
                break

    finally:
        gesture_analyzer.close()
        drone.streamoff()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()