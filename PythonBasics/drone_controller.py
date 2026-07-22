"""
drone_controller.py
-------------------
Encapsulates all physical drone hardware communication and fallback handling.
"""

from djitellopy import Tello


class DroneController:

    def __init__(self, default_speed=50):
        self.tello = None
        self.is_connected = False
        self.default_speed = default_speed
        self.battery = 0
        self.init_hardware()

    def init_hardware(self):
        """Attempts to establish connection with physical Tello hardware."""
        try:
            self.tello = Tello()
            self.tello.connect()
            self.battery = self.tello.get_battery()
            self.is_connected = True
            print(
                f"[SYSTEM] Tello Connected Successfully! Battery: {self.battery}%"
            )
        except Exception as err:
            self.is_connected = False
            print(
                f"[SYSTEM WARN] Drone connection failed ({err}). Entering Visual Simulation Mode."
            )

    def takeoff(self):
        if self.is_connected and self.tello:
            try:
                self.tello.takeoff()
            except Exception as err:
                print(f"[HW ERROR] Takeoff command failed: {err}")

    def land(self):
        if self.is_connected and self.tello:
            try:
                self.tello.send_rc_control(0, 0, 0, 0)
                self.tello.land()
            except Exception as err:
                print(f"[HW ERROR] Land command failed: {err}")

    def send_rc(self, left_right: int, forward_back: int, up_down: int, yaw: int):
        """Streams real-time RC velocity commands to the Tello controller."""
        if self.is_connected and self.tello:
            try:
                self.tello.send_rc_control(
                    left_right, forward_back, up_down, yaw
                )
            except Exception as err:
                print(f"[HW ERROR] RC Stream Error: {err}")

    def disconnect(self):
        """Safely stops motion and closes connection on app exit."""
        if self.is_connected and self.tello:
            try:
                self.tello.send_rc_control(0, 0, 0, 0)
            except Exception:
                pass