import collections
import time
import cv2
import numpy as np
from djitellopy import Tello


class PIDController:

    def __init__(self, kp: float, ki: float, kd: float, limit: float = 100.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.limit = limit

        self.last_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()

        # Telemetry storage
        self.p_out = 0.0
        self.i_out = 0.0
        self.d_out = 0.0
        self.total_out = 0.0

    def update(self, error: float) -> int:
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0.0:
            dt = 1e-4

        self.p_out = self.kp * error

        self.integral += error * dt
        self.integral = max(-self.limit, min(self.limit, self.integral))
        self.i_out = self.ki * self.integral

        self.d_out = self.kd * ((error - self.last_error) / dt)

        self.total_out = self.p_out + self.i_out + self.d_out

        self.last_error = error
        self.last_time = current_time

        clamped = max(-self.limit, min(self.limit, self.total_out))
        return int(clamped)


def main():
    drone = Tello()
    drone.connect()
    drone.streamon()

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    pid_yaw = PIDController(kp=0.25, ki=0.001, kd=0.1, limit=50)
    pid_ud = PIDController(kp=0.25, ki=0.001, kd=0.1, limit=50)

    # History buffer to draw a live rolling error graph (last 100 frames)
    error_history = collections.deque(maxlen=100)

    flying = False

    while True:
        frame = drone.get_frame_read().frame
        if frame is None:
            continue

        frame = cv2.resize(frame, (640, 480))
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5)

        yaw_velocity = 0
        ud_velocity = 0
        current_error_x = 0

        if len(faces) > 0:
            faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
            (x, y, face_w, face_h) = faces[0]

            face_cx = x + (face_w // 2)
            face_cy = y + (face_h // 2)

            current_error_x = face_cx - center_x
            error_y = center_y - face_cy

            yaw_velocity = pid_yaw.update(current_error_x)
            ud_velocity = pid_ud.update(error_y)

            # Draw visual targets
            cv2.rectangle(
                frame, (x, y), (x + face_w, y + face_h), (0, 255, 0), 2
            )
            cv2.line(
                frame,
                (center_x, center_y),
                (face_cx, face_cy),
                (255, 255, 0),
                2,
            )
        else:
            pid_yaw.integral = 0
            pid_ud.integral = 0

        # Save current error to rolling graph history
        error_history.append(current_error_x)

        if flying:
            drone.send_rc_control(0, 0, ud_velocity, yaw_velocity)

        # -------------------------------------------------------------
        # ON-SCREEN DISPLAY (OSD) TELEMETRY
        # -------------------------------------------------------------

        # 1. Overlay Live Text Metrics
        cv2.putText(
            frame,
            f"Error X: {current_error_x} px",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"P Output: {pid_yaw.p_out:.1f}",
            (20, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"I Output: {pid_yaw.i_out:.1f}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"D Output: {pid_yaw.d_out:.1f}",
            (20, 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"Yaw Command: {yaw_velocity}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

        # 2. Draw Live Rolling Graph along bottom frame (Error over time)
        graph_box_y = 400
        cv2.rectangle(
            frame, (20, graph_box_y), (320, 470), (30, 30, 30), -1
        )  # Dark background box
        cv2.line(
            frame,
            (20, graph_box_y + 35),
            (320, graph_box_y + 35),
            (100, 100, 100),
            1,
        )  # Zero line

        if len(error_history) > 1:
            for i in range(1, len(error_history)):
                x1 = 20 + (i - 1) * 3
                y1 = int(
                    graph_box_y + 35 + (error_history[i - 1] / 320.0) * 35
                )

                x2 = 20 + i * 3
                y2 = int(graph_box_y + 35 + (error_history[i] / 320.0) * 35)

                # Clamp values inside graph box bounds
                y1 = max(graph_box_y, min(graph_box_y + 70, y1))
                y2 = max(graph_box_y, min(graph_box_y + 70, y2))

                cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        cv2.imshow("Tello PID Live Dashboard", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("t") and not flying:
            drone.takeoff()
            flying = True
        elif key == ord("l") and flying:
            drone.land()
            flying = False
        elif key == ord("q"):
            if flying:
                drone.land()
            break

    cv2.destroyAllWindows()
    drone.streamoff()


if __name__ == "__main__":
    main()