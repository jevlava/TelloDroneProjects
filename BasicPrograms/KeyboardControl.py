from time import sleep
from djitellopy import tello  # Library for controlling the DJI Tello drone
import KeyPressModule as kp  # Custom Pygame-based key press listener module

################ INITIALIZATION ################
kp.init()  # Creates Pygame window to capture keyboard focus

me = tello.Tello()  # Instantiate Tello controller object
me.connect()  # Establish UDP connection with the drone over Wi-Fi
print(me.get_battery())  # Output battery percentage to console


################ KEYBOARD TRANSLATION FUNCTION ################
def getKeyboardInput():
    """Polls active key states using KeyPressModule and maps them to

    RC control values: [Left/Right, Forward/Backward, Up/Down, Yaw].

    """
    lr, fb, ud, yv = 0, 0, 0, 0  # Default state: hover in place (all channels zero)
    speed = 50  # Velocity magnitude (range -100 to 100)

    # --- Roll Control (Left / Right Movement) ---
    if kp.getKey("LEFT"):
        lr = -speed  # Roll left
    elif kp.getKey("RIGHT"):
        lr = speed  # Roll right

    # --- Pitch Control (Forward / Backward Movement) ---
    if kp.getKey("UP"):
        fb = speed  # Pitch forward
    elif kp.getKey("DOWN"):
        fb = -speed  # Pitch backward

    # --- Throttle Control (Ascend / Descend) ---
    if kp.getKey("w"):
        ud = speed  # Ascend
    elif kp.getKey("s"):
        ud = -speed  # Descend

    # --- Yaw Control (Rotation) ---
    # Note: Typical Tello controls map 'a' to counter-clockwise (-yv) and 'd' to clockwise (+yv)
    if kp.getKey("a"):
        yv = speed  # Yaw control
    elif kp.getKey("d"):
        yv = -speed  # Yaw control

    # --- Flight State Commands ---
    if kp.getKey("e"):
        me.takeoff()  # Trigger automated takeoff sequence
    if kp.getKey("q"):
        me.land()  # Trigger automated landing sequence

    return [lr, fb, ud, yv]


################ FLIGHT LOGIC ################
me.takeoff()  # Automatically take off prior to entering control loop

while True:
    # 1. Read current active keys and compute direction vectors
    vals = getKeyboardInput()

    # 2. Dispatch roll, pitch, throttle, and yaw velocity commands to Tello
    me.send_rc_control(vals[0], vals[1], vals[2], vals[3])

    # 3. Pause for 50ms (20 Hz loop rate) to avoid flooding network buffer
    sleep(0.05)