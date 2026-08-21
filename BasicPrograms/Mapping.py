from djitellopy import tello  # Library to control the Ryze Tello drone
from BasicPrograms import KeyPressModule as kp  # Custom module for key detection
import numpy as np  # Used to generate the black canvas image
from time import sleep  # Used to control loop timing
import cv2  # OpenCV for visualization and rendering the map
import math  # Math operations for calculating trigonometric coordinates

################ PARAMETERS & SPEED CONVERSIONS ################
# Converts raw drone velocities into estimated physical distances covered per tick.
fSpeed = 117 / 10  # Estimated forward speed in cm/s (~11.7 cm/s)
aSpeed = 360 / 10  # Estimated angular/rotation speed in degrees/s (~36.0 deg/s)
interval = 0.25  # Time step delay (in seconds) between command checks

# Distance & rotation moved during a single loop iteration (speed * time)
dInterval = fSpeed * interval  # Distance covered per interval (~2.925 cm)
aInterval = aSpeed * interval  # Angle rotated per interval (~9.0 degrees)

################ GLOBAL STATE & INITIALIZATION ################
# Set starting coordinates at (500, 500) to place the drone in the center of a 1000x1000 canvas
x, y = 500, 500
a = 0  # Direction angle heading for movement vector calculation
yaw = 0  # Accumulated drone orientation/yaw angle

kp.init()  # Initialize the keyboard listener module

# Connect and set up the Tello Drone
me = tello.Tello()
me.connect()
print(me.get_battery())  # Output battery level to verify successful connection

# Track history of path coordinates; seeded with two origin points
points = [(0, 0), (0, 0)]


################ KEYBOARD INPUT & ODOMETRY PROCESSING ################
def getKeyboardInput():
    """Reads keyboard inputs, computes roll/pitch/yaw/throttle values for the drone,

    and estimates the updated (x, y) coordinates using basic dead-reckoning trigonometry.

    """
    lr, fb, ud, yv = 0, 0, 0, 0  # Left/Right, Forward/Backward, Up/Down, Yaw Velocity
    speed = 15  # Movement command magnitude (-100 to 100)
    aspeed = 50  # Rotation command magnitude (-100 to 100)
    global x, y, yaw, a
    d = 0  # Distance offset for current interval step

    # --- Directional Movement (Roll / Pitch) ---
    if kp.getKey("LEFT"):
        lr = -speed
        d = dInterval
        a = -180  # Movement vector directed left
    elif kp.getKey("RIGHT"):
        lr = speed
        d = -dInterval
        a = 180  # Movement vector directed right

    if kp.getKey("UP"):
        fb = speed
        d = dInterval
        a = 270  # Movement vector directed forward/up on 2D plane
    elif kp.getKey("DOWN"):
        fb = -speed
        d = -dInterval
        a = -90  # Movement vector directed backward/down on 2D plane

    # --- Vertical Movement (Throttle) ---
    if kp.getKey("w"):
        ud = speed  # Ascend
    elif kp.getKey("s"):
        ud = -speed  # Descend

    # --- Yaw Control (Rotation) ---
    if kp.getKey("a"):
        yv = -aspeed  # Rotate counter-clockwise
        yaw -= aInterval
    elif kp.getKey("d"):
        yv = aspeed  # Rotate clockwise
        yaw += aInterval

    # --- Flight Commands ---
    if kp.getKey("q"):
        me.land()
        sleep(3)  # Land the drone safely
    if kp.getKey("e"):
        me.takeoff()  # Command drone to take off

    sleep(interval)  # Maintain stable execution speed per frame cycle

    # --- Dead Reckoning Location Estimation ---
    a += yaw  # Total directional heading incorporating active rotation

    # Convert polar vector (distance 'd', angle 'a') to Cartesian (x, y) coordinates
    x += int(d * math.cos(math.radians(a)))
    y += int(d * math.sin(math.radians(a)))

    return [lr, fb, ud, yv, x, y]


################ PATH DRAWING & MAPPING ################
def drawPoints(img, points):
    """Draws historical path markers, a current position indicator,

    and telemetry text onto the OpenCV window.

    """
    # Draw all past locations as small red circles
    for point in points:
        cv2.circle(img, point, 5, (0, 0, 255), cv2.FILLED)

    # Highlight current position (latest point) with a larger green circle
    cv2.circle(img, points[-1], 8, (0, 255, 0), cv2.FILLED)

    # Convert pixel offset from center (500, 500) into real-world meters and display text
    cv2.putText(
        img,
        f"({(points[-1][0] - 500) / 100},{(points[-1][1] - 500) / 100})m",
        (points[-1][0] + 10, points[-1][1] + 30),
        cv2.FONT_HERSHEY_PLAIN,
        1,
        (255, 0, 255),
        1,
    )


################ MAIN EXECUTION LOOP ################
while True:
    # 1. Fetch user inputs and newly calculated odometry positions
    vals = getKeyboardInput()

    # 2. Send RC values (Left/Right, Forward/Backward, Up/Down, Yaw Velocity) to Tello
    me.send_rc_control(vals[0], vals[1], vals[2], vals[3])

    # 3. Create a blank 1000x1000 black canvas for map rendering
    img = np.zeros((1000, 1000, 3), np.uint8)

    # 4. Append new coordinates to path history only if position has changed
    if points[-1][0] != vals[4] or points[-1][1] != vals[5]:
        points.append((vals[4], vals[5]))

    # 5. Render mapping data onto image canvas and display window
    drawPoints(img, points)
    cv2.imshow("Output", img)
    cv2.waitKey(1)  # Refresh display frame (1ms delay)