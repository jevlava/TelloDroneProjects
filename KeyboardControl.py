from djitellopy import tello
import KeyPressModule as kp
from time import sleep

kp.init()
me = tello.Tello()
me.connect()
print(me.get_battery())



def getKeyboardInput():
    lr, fb, ud, yv = 0,0,0,0
    speed = 50

    # lr (left/right keys)
    if kp.getKey("LEFT"): lr = -speed
    elif kp.getKey("RIGHT"): lr = speed

    # fb (forward/backward keys)
    if kp.getKey("UP"): fb = speed
    elif kp.getKey("DOWN"): fb = -speed

    # ud (up/down keys)
    if kp.getKey("w"): ud = speed
    elif kp.getKey("s"): ud = -speed

    # ud (clockwise/counterclockwise)
    if kp.getKey("a"): yv = speed
    elif kp.getKey("d"): yv = -speed

    # drone takeoff
    if kp.getKey("e"): me.takeoff()
    # lands the drone
    if kp.getKey("q"): me.land()


    return [lr, fb, ud, yv]


me.takeoff()

while True:
    vals = getKeyboardInput() # Accepts keyboard values
    me.send_rc_control(vals[0], vals[1], vals[2], vals[3])
    sleep(0.05)

