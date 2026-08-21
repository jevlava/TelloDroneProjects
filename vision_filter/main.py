



import cv2
from djitellopy import tello
from hand_tracker import GestureEngine
from filters import AestheticFilters

# Initialize modules
me = tello.Tello()
me.connect(wait_for_state=False)
me.streamon()

gesture_engine = GestureEngine()
active_filter = "NORMAL"

while True:
    img = me.get_frame_read().frame
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = cv2.resize(img, (640, 480))

    # Detect Gestures
    hand, gesture = gesture_engine.analyze(img)

    # Mode Switching based on Gesture
    if gesture == "PEACE":
        active_filter = "HUD"
    elif gesture == "POINT":
        active_filter = "THERMAL"
    elif gesture == "PALM":
        active_filter = "NORMAL"

    # Render Selected Filter
    if active_filter == "HUD":
        bbox = hand['bbox'] if hand else None
        img = AestheticFilters.apply_cyberpunk_hud(img, bbox)
    elif active_filter == "THERMAL":
        img = AestheticFilters.apply_simulated_thermal(img)

    cv2.imshow("Tello Feed", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
me.streamoff()