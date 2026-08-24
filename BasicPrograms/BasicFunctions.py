import time
from djitellopy import Tello  # Import the official Tello library wrapper

# Initialize drone object
tello = Tello()

# Connect to the drone over Wi-Fi
tello.connect()

# Check battery status before flight (safety best practice)
print(f"Battery Level: {tello.get_battery()}%")

# Take off into hover position
tello.takeoff()

# =========================================================================
# TYPE 1: BLOCKING / DISTANCE-BASED MOVEMENTS
# Code pauses execution until each exact distance or rotation is complete.
# Distance range: 20 to 500 cm. Yaw rotation range: 1 to 360 degrees.
# =========================================================================

# Set default speed for movement methods ( range: 10 to 100 cm/s )
tello.set_speed(30)

# Direct linear movements
tello.move_forward(50)   # Move forward 50 cm
tello.move_back(50)      # Move backward 50 cm
tello.move_left(30)      # Move left 30 cm
tello.move_right(30)     # Move right 30 cm
tello.move_up(40)        # Move up 40 cm
tello.move_down(40)      # Move down 40 cm

# Rotational movements (Yaw)
tello.rotate_clockwise(90)          # Rotate right 90 degrees
tello.rotate_counter_clockwise(90)  # Rotate left 90 degrees

# Advanced spatial movement (x, y, z relative to drone, speed cm/s)
tello.go_xyz_speed(30, 0, 20, 20)  # Move (+x forward/back, +y left/right, +z up/down)

# Flips (Parameters: 'l' left, 'r' right, 'f' forward, 'b' back)
tello.flip("f")

time.sleep(2)  # Pause in hover before switching control modes

# =========================================================================
# TYPE 2: CONTINUOUS / RC VELOCITY CONTROL
# Sends real-time speed values (-100 to 100) across 4 axes.
# Useful for joystick input, computer vision tracking, or smooth maneuvers.
# =========================================================================

# Syntax: send_rc_control(left_right_vel, forward_back_vel, up_down_vel, yaw_vel)

# Move forward at 30% speed for 2 seconds
tello.send_rc_control(0, 30, 0, 0)
time.sleep(2)

# Move right while ascending simultaneously
tello.send_rc_control(25, 0, 20, 0)
time.sleep(2)

# Spin clockwise while moving backward
tello.send_rc_control(0, -20, 0, 40)
time.sleep(2)

# IMPORTANT: Always reset velocity to 0 to stop movement!
tello.send_rc_control(0, 0, 0, 0)
time.sleep(1)

# Land safely
tello.land()