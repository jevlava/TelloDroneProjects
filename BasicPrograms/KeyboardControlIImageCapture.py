import time
import cv2
from djitellopy import tello

# -----------------------------------------------------------------------------
# 1. INITIALIZATION & CONNECTION
# -----------------------------------------------------------------------------
# Instantiate the main Tello object from djitellopy.
me = tello.Tello()

# Connects over Wi-Fi (UDP sockets) to the Tello drone.
# Note: Ensure your computer is connected to the drone's Wi-Fi network before running.
me.connect()

# me.get_battery() sends an engine state request via SDK to retrieve remaining power (0-100%).
print(f"Battery: {me.get_battery()}%")

# -----------------------------------------------------------------------------
# 2. VIDEO STREAM SETUP
# -----------------------------------------------------------------------------
# me.streamon() sends the command to start sending H.264 video packets over UDP port 11111.
me.streamon()

# me.get_frame_read() spawns a background thread that continuously grabs and
# decodes raw camera frames so the main loop doesn't block waiting for video.
frame_read = me.get_frame_read()


def get_keyboard_input(key, speed=50):
    """
    Translates OpenCV keycode integers into Tello RC movement values (-100 to 100).
    Maps keys to 4 movement axes:
      lr = Left/Right (Roll)
      fb = Forward/Backward (Pitch)
      ud = Up/Down (Throttle/Altitude)
      yv = Yaw Velocity (Rotation)
    """
    lr, fb, ud, yv = 0, 0, 0, 0

    # cv2.waitKey() returns -1 if no key was pressed during the time delay window
    if key == -1:
        return [0, 0, 0, 0]  # Send neutral zero speeds so drone hovers in place

    # KEYCODE EXTRACTION (CROSS-PLATFORM FIX):
    # 'key & 0xFF' performs a bitwise AND mask to extract the lowest 8 bits.
    # This strips OS-specific modifiers (like NumLock or CapsLock state on Linux/Windows)
    # to yield a standard ASCII keycode usable by python's chr() function.
    char = chr(key & 0xFF).lower() if 0 <= (key & 0xFF) < 256 else ''

    # --- MOVEMENT AXES CONTROL ---
    # Roll (Left / Right panning)
    if char == 'j':
        lr = -speed
    elif char == 'l':
        lr = speed

    # Pitch (Forward / Backward tilt)
    if char == 'i':
        fb = speed
    elif char == 'k':
        fb = -speed

    # Throttle / Altitude (Vertical movement)
    if char == 'w':
        ud = speed
    elif char == 's':
        ud = -speed

    # Yaw (360-degree rotation around vertical axis)
    if char == 'a':
        yv = -speed
    elif char == 'd':
        yv = speed

    # --- FLIGHT & RECORDING COMMANDS ---
    # Takeoff triggers automated motor spin-up and auto-hover at ~1-1.2 meters height
    if char == 'e':
        me.takeoff()

    # Land triggers automated descent and motor cutoff upon landing detection
    elif char == 'q':
        me.land()

    # Save video frame snapshot to local directory
    if char == 'z':
        # frame_read.frame accesses the latest decoded BGR numpy array frame from the video thread
        img = frame_read.frame

        # cv2.imwrite(filename, image_array) encodes and saves the array to a JPEG image file
        # Note: The 'Resources/Images/' directory must already exist on your file system
        cv2.imwrite(f'Resources/Images/{int(time.time())}.jpg', img)
        print("Snapshot saved!")

        # Small delay to prevent rapid-fire repeated snapshot triggers while key is held down
        time.sleep(0.2)

    return [lr, fb, ud, yv]


# -----------------------------------------------------------------------------
# 3. MAIN APPLICATION & STREAMING LOOP
# -----------------------------------------------------------------------------
while True:
    # Fetch the current frame buffer (BGR image represented as a NumPy NDArray)
    img = frame_read.frame

    # Safety guard: Skip loop iteration if frame capture failed or is starting up
    if img is None:
        continue

    # cv2.resize(src, (width, height)): Normalizes frame dimension for visual rendering UI
    img = cv2.resize(img, (720, 480))

    # --- TELEMETRY OVERLAY GENERATION ---
    battery = me.get_battery()

    # cv2.putText(image, text, position_tuple, font_face, font_scale, color_bgr, thickness)
    # Dynamically toggles battery text color: Green (0, 255, 0) if >20%, Red (0, 0, 255) if low
    cv2.putText(img, f"Battery: {battery}%", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if battery > 20 else (0, 0, 255), 2)

    # Render key mapping legend on screen footer in white (255, 255, 255)
    cv2.putText(img, "Controls: I/K=Pitch | J/L=Roll | W/S=Alt | A/D=Yaw | E=Takeoff | Q=Land",
                (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # --- RENDERING & CONTROL UPDATE ---
    # cv2.imshow(winname, image): Displays the image array inside a GUI window
    cv2.imshow("DJI Tello Live Control", img)

    # cv2.waitKey(1) pauses for 1 millisecond to handle window drawing events
    # and listens for keyboard input. Returns keycode integer (or -1 if no key)
    key = cv2.waitKey(1)

    # Calculate velocity vector from input
    vals = get_keyboard_input(key)

    # me.send_rc_control(lr, fb, ud, yv) sends raw RC values from -100 to 100 over UDP socket.
    # Must be sent periodically to maintain continuous drone velocity; otherwise Tello hovers.
    me.send_rc_control(vals[0], vals[1], vals[2], vals[3])

    # ESC key (ASCII value 27) breaks the control loop for a clean exit
    if key == 27:
        me.land()  # Safely trigger auto-landing before closing window
        break

# -----------------------------------------------------------------------------
# 4. CLEANUP
# -----------------------------------------------------------------------------
# Closes all OpenCV UI windows created by cv2.imshow() to release window/graphics handles
cv2.destroyAllWindows()