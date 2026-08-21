import cv2
import numpy as np
from config import HISTORY_LENGTH

class DashboardUI:
    def __init__(self):
        # History buffers for telemetry graphs
        self.histories = {
            "ALT": {"act": [0] * HISTORY_LENGTH, "tgt": [0] * HISTORY_LENGTH},
            "FWD": {"act": [0] * HISTORY_LENGTH, "tgt": [0] * HISTORY_LENGTH},
            "STR": {"act": [0] * HISTORY_LENGTH, "tgt": [0] * HISTORY_LENGTH},
            "YAW": {"act": [0] * HISTORY_LENGTH, "tgt": [0] * HISTORY_LENGTH},
        }

    def _draw_mini_graph(self, canvas, x, y, w, h, history, target_history, label, max_val):
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (50, 50, 50), 1)
        cv2.putText(canvas, label, (x + 4, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 200, 200), 1)

        for i in range(len(history) - 1):
            act_y1 = int(y + h - (min(max(history[i], -max_val), max_val) + max_val) / (2 * max_val) * h)
            act_y2 = int(y + h - (min(max(history[i + 1], -max_val), max_val) + max_val) / (2 * max_val) * h)

            tgt_y1 = int(y + h - (min(max(target_history[i], -max_val), max_val) + max_val) / (2 * max_val) * h)
            tgt_y2 = int(y + h - (min(max(target_history[i + 1], -max_val), max_val) + max_val) / (2 * max_val) * h)

            step_x = w // HISTORY_LENGTH
            x1 = x + (i * step_x)
            x2 = x + ((i + 1) * step_x)

            cv2.line(canvas, (x1, tgt_y1), (x2, tgt_y2), (0, 255, 0), 1)  # Target (Green)
            cv2.line(canvas, (x1, act_y1), (x2, act_y2), (255, 100, 0), 1)  # Actual (Blue)

    def draw(self, frame, current_vals, targets, errors, gains, active_mode, battery, current_key):
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        frame = cv2.resize(frame, (960, 480))
        # Convert frame color channels before copying to the canvas
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        canvas = np.zeros((720, 960, 3), dtype=np.uint8)
        canvas[0:480, 0:960] = frame

        cv2.putText(canvas, f"Battery: {battery}%", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(canvas, f"Alt: {current_vals['ALT']}cm | Fwd: {current_vals['FWD']}cm | Str: {current_vals['STR']}cm | Yaw: {current_vals['YAW']}deg", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        # Update History Buffers
        for axis in ["ALT", "FWD", "STR", "YAW"]:
            self.histories[axis]["act"].pop(0)
            self.histories[axis]["act"].append(current_vals[axis])
            self.histories[axis]["tgt"].pop(0)
            self.histories[axis]["tgt"].append(targets[axis])

        # Bottom Left: Telemetry Panel
        cv2.rectangle(canvas, (0, 480), (480, 720), (30, 30, 30), -1)
        cv2.putText(canvas, "Multi-Axis PID Telemetry (Green:Target | Blue:Actual)", (10, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 2)

        gw, gh = 215, 65
        self._draw_mini_graph(canvas, 15, 515, gw, gh, self.histories["ALT"]["act"], self.histories["ALT"]["tgt"], f"ALT (Kp:{gains['ALT']['kp']:.2f}) Err:{errors['ALT']:.1f}", 200)
        self._draw_mini_graph(canvas, 245, 515, gw, gh, self.histories["FWD"]["act"], self.histories["FWD"]["tgt"], f"FWD (Kp:{gains['FWD']['kp']:.2f}) Err:{errors['FWD']:.1f}", 200)
        self._draw_mini_graph(canvas, 15, 595, gw, gh, self.histories["STR"]["act"], self.histories["STR"]["tgt"], f"STR (Kp:{gains['STR']['kp']:.2f}) Err:{errors['STR']:.1f}", 200)
        self._draw_mini_graph(canvas, 245, 595, gw, gh, self.histories["YAW"]["act"], self.histories["YAW"]["tgt"], f"YAW (Kp:{gains['YAW']['kp']:.2f}) Err:{errors['YAW']:.1f}", 180)

        cv2.putText(canvas, f"Tuning Mode: [TAB to cycle] -> {active_mode} (Keys 1-6)", (15, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
        cv2.putText(canvas, "1/2:Kp-|+ | 3/4:Ki-|+ | 5/6:Kd-|+", (15, 702), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        # Bottom Right: Keyboard Grid
        cv2.rectangle(canvas, (480, 480), (960, 720), (40, 40, 40), -1)
        cv2.putText(canvas, "Flight (QWE/ASD)", (495, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        cv2.putText(canvas, "Translation (I / JKL)", (730, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
        cv2.line(canvas, (715, 490), (715, 710), (70, 70, 70), 1)

        bw, bh = 65, 45
        buttons = [
            ("Q:Takeoff", 'q', 495, 515, bw, bh), ("W:Up", 'w', 565, 515, bw, bh), ("E:Land", 'e', 635, 515, bw, bh),
            ("A:Rot-L", 'a', 495, 565, bw, bh), ("S:Down", 's', 565, 565, bw, bh), ("D:Rot-R", 'd', 635, 565, bw, bh),
            ("I:Fwd", 'i', 800, 515, bw, bh), ("J:Left", 'j', 730, 565, bw, bh), ("K:Back", 'k', 800, 565, bw, bh), ("L:Right", 'l', 870, 565, bw, bh),
            ("Tab:Switch Axis | Exit: [ESC]", 'none', 495, 625, 440, 28)
        ]

        for label, key_id, bx, by, bw_sz, bh_sz in buttons:
            if key_id == 'none':
                cv2.rectangle(canvas, (bx, by), (bx + bw_sz, by + bh_sz), (50, 50, 50), -1)
                cv2.putText(canvas, label, (bx + 70, by + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)
                continue

            is_pressed = (str(current_key).lower() == str(key_id).lower())
            color = (0, 200, 0) if is_pressed else (70, 70, 70)
            text_color = (0, 0, 0) if is_pressed else (255, 255, 255)

            cv2.rectangle(canvas, (bx, by), (bx + bw_sz, by + bh_sz), color, -1)
            cv2.rectangle(canvas, (bx, by), (bx + bw_sz, by + bh_sz), (200, 200, 200), 1)

            parts = label.split(':')
            cv2.putText(canvas, parts[0], (bx + 22, by + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
            cv2.putText(canvas, parts[1], (bx + 6, by + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.33, text_color, 1)

        return canvas