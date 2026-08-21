import time
import cv2
from djitellopy import tello

# Initialize and Connect Tello
me = tello.Tello()
me.connect()
print(f"Battery: {me.get_battery()}%")

# Start Video Stream
me.streamon()
frame_read = me.get_frame_read()


def get_keyboard_input(key, speed=50):
    """
    Translates keyboard inputs to Tello RC movement commands.
    Using standard letter keys avoids OS-dependent arrow key bugs.
    """
    lr, fb, ud, yv = 0, 0, 0, 0

    if key == -1:
        return [0, 0, 0, 0]  # No key pressed -> Hover in place

    # Convert keycode to lowercase character for safe cross-platform matching
    char = chr(key & 0xFF).lower() if 0 <= (key & 0xFF) < 256 else ''

    # --- MOVEMENT CONTROLS ---
    # Pitch & Roll (I / K / J / L)
    if char == 'j':  # Roll Left
        lr = -speed
    elif char == 'l':  # Roll Right
        lr = speed
    if char == 'i':  # Pitch Forward
        fb = speed
    elif char == 'k':  # Pitch Backward
        fb = -speed

    # Altitude (W / S)
    if char == 'w':  # Up
        ud = speed
    elif char == 's':  # Down
        ud = -speed

    # Yaw / Rotation (A / D)
    if char == 'a':  # Rotate Left
        yv = -speed
    elif char == 'd':  # Rotate Right
        yv = speed

    # --- COMMAND CONTROLS ---
    if char == 'e':
        me.takeoff()
    elif char == 'q':
        me.land()

    # Save Snapshot
    if char == 'z':
        img = frame_read.frame
        cv2.imwrite(f'Resources/Images/{int(time.time())}.jpg', img)
        print("Snapshot saved!")
        time.sleep(0.2)

    return [lr, fb, ud, yv]


# Main Loop
while True:
    # 1. Fetch live camera frame
    img = frame_read.frame
    if img is None:
        continue

    img = cv2.resize(img, (720, 480))

    # 2. Add telemetry overlay on video
    battery = me.get_battery()
    cv2.putText(img, f"Battery: {battery}%", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if battery > 20 else (0, 0, 255), 2)

    cv2.putText(img, "Controls: I/K=Pitch | J/L=Roll | W/S=Alt | A/D=Yaw | E=Takeoff | Q=Land",
                (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # 3. Render video frame
    cv2.imshow("DJI Tello Live Control", img)

    # 4. Read key with 0xFF bitwise mask for platform independence
    key = cv2.waitKey(1)

    # Process movement
    vals = get_keyboard_input(key)
    me.send_rc_control(vals[0], vals[1], vals[2], vals[3])

    # Press ESC to exit cleanly
    if key == 27:
        me.land()
        break

cv2.destroyAllWindows()