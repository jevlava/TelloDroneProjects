import time
import cv2
import numpy as np
from djitellopy import Tello

# --- Initialize Real Tello & Video Stream ---
tello = Tello()

# Explicitly attempt connection with error handling
try:
    tello.connect()
    print(f"[Info] Battery life: {tello.get_battery()}%")
except Exception as e:
    print(f"[Error] Failed to connect to Tello: {e}")
    print("[Tip] Ensure you are connected to the Tello Wi-Fi network and your firewall allows UDP ports 8889/8890.")
    exit(1)

tello.streamon()
frame_read = tello.get_frame_read()

is_flying = False
last_key = "None"

# History buffers for 4 Axes (Altitude, Forward, Strafe, Yaw)
history_length = 60
alt_history = [0] * history_length
alt_target = [0] * history_length

fwd_history = [0] * history_length
fwd_target = [0] * history_length

strafe_history = [0] * history_length
strafe_target = [0] * history_length

yaw_history = [0] * history_length
yaw_target = [0] * history_length

# Target State Variables (Commanded values)
target_alt_val = 0.0
target_fwd_val = 0.0
target_strafe_val = 0.0
target_yaw_val = 0.0

# PID Gains & States for each axis
# 1. Altitude PID
kp_alt, ki_alt, kd_alt = 0.6, 0.1, 0.05
err_alt, int_alt, prev_err_alt, p_alt, i_alt, d_alt = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

# 2. Forward/Back PID
kp_fwd, ki_fwd, kd_fwd = 0.5, 0.05, 0.02
err_fwd, int_fwd, prev_err_fwd, p_fwd, i_fwd, d_fwd = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

# 3. Strafe PID
kp_str, ki_str, kd_str = 0.5, 0.05, 0.02
err_str, int_str, prev_err_str, p_str, i_str, d_str = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

# 4. Yaw PID
kp_yaw, ki_yaw, kd_yaw = 0.4, 0.02, 0.01
err_yaw, int_yaw, prev_err_yaw, p_yaw, i_yaw, d_yaw = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

# Active tuning target selection (1-6 for Alt, 7-9 for Fwd, etc. Or cycle globally)
active_gain_mode = "ALT"  # ALT, FWD, STR, YAW


def update_all_pid_loops(current_alt, current_fwd, current_strafe, current_yaw):
    global err_alt, int_alt, prev_err_alt, p_alt, i_alt, d_alt
    global err_fwd, int_fwd, prev_err_fwd, p_fwd, i_fwd, d_fwd
    global err_str, int_str, prev_err_str, p_str, i_str, d_str
    global err_yaw, int_yaw, prev_err_yaw, p_yaw, i_yaw, d_yaw

    if not tello.is_flying:
        # Reset targets when landed
        global target_alt_val, target_fwd_val, target_strafe_val, target_yaw_val
        target_alt_val = 0.0
        target_fwd_val = 0.0
        target_strafe_val = 0.0
        target_yaw_val = 0.0

    # --- 1. Altitude Loop ---
    err_alt = target_alt_val - current_alt
    p_alt = kp_alt * err_alt
    int_alt = max(-300, min(300, int_alt + err_alt))
    i_alt = ki_alt * int_alt
    d_alt = kd_alt * (err_alt - prev_err_alt)
    prev_err_alt = err_alt

    # --- 2. Forward/Back Loop ---
    err_fwd = target_fwd_val - current_fwd
    p_fwd = kp_fwd * err_fwd
    int_fwd = max(-300, min(300, int_fwd + err_fwd))
    i_fwd = ki_fwd * int_fwd
    d_fwd = kd_fwd * (err_fwd - prev_err_fwd)
    prev_err_fwd = err_fwd

    # --- 3. Strafe Loop ---
    err_str = target_strafe_val - current_strafe
    p_str = kp_str * err_str
    int_str = max(-300, min(300, int_str + err_str))
    i_str = ki_str * int_str
    d_str = kd_str * (err_str - prev_err_str)
    prev_err_str = err_str

    # --- 4. Yaw Loop ---
    err_yaw = target_yaw_val - current_yaw
    p_yaw = kp_yaw * err_yaw
    int_yaw = max(-300, min(300, int_yaw + err_yaw))
    i_yaw = ki_yaw * int_yaw
    d_yaw = kd_yaw * (err_yaw - prev_err_yaw)
    prev_err_yaw = err_yaw


def draw_mini_graph(canvas, x, y, w, h, history, target_history, label, max_val):
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (50, 50, 50), 1)
    cv2.putText(canvas, label, (x + 4, y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (200, 200, 200), 1)

    for i in range(len(history) - 1):
        # Normalize values to box height
        act_y1 = int(y + h - (min(max(history[i], -max_val), max_val) + max_val) / (2 * max_val) * h)
        act_y2 = int(y + h - (min(max(history[i + 1], -max_val), max_val) + max_val) / (2 * max_val) * h)

        tgt_y1 = int(y + h - (min(max(target_history[i], -max_val), max_val) + max_val) / (2 * max_val) * h)
        tgt_y2 = int(y + h - (min(max(target_history[i + 1], -max_val), max_val) + max_val) / (2 * max_val) * h)

        step_x = w // history_length
        x1 = x + (i * step_x)
        x2 = x + ((i + 1) * step_x)

        cv2.line(canvas, (x1, tgt_y1), (x2, tgt_y2), (0, 255, 0), 1)  # Target (Green)
        cv2.line(canvas, (x1, act_y1), (x2, act_y2), (255, 100, 0), 1)  # Actual (Blue)


def draw_dashboard(frame, alt, fwd, strafe, yaw, battery, current_key):
    frame = cv2.resize(frame, (960, 480))
    # Swap color channels to match OpenCV display expectations
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    canvas = np.zeros((720, 960, 3), dtype=np.uint8)
    canvas[0:480, 0:960] = frame

    cv2.putText(canvas, f"Battery: {battery}%", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(canvas, f"Alt: {alt}cm | Fwd: {fwd}cm | Str: {strafe}cm | Yaw: {yaw}deg", (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    # ==========================================
    # BOTTOM LEFT: Quad-Axis Telemetry & Gains Panel
    # ==========================================
    cv2.rectangle(canvas, (0, 480), (480, 720), (30, 30, 30), -1)
    cv2.putText(canvas, "Multi-Axis PID Telemetry (Green:Target | Blue:Actual)", (10, 500), cv2.FONT_HERSHEY_SIMPLEX,
                0.42, (255, 255, 255), 2)

    # Update History Buffers
    alt_history.pop(0);
    alt_history.append(alt)
    alt_target.pop(0);
    alt_target.append(target_alt_val)

    fwd_history.pop(0);
    fwd_history.append(fwd)
    fwd_target.pop(0);
    fwd_target.append(target_fwd_val)

    strafe_history.pop(0);
    strafe_history.append(strafe)
    strafe_target.pop(0);
    strafe_target.append(target_strafe_val)

    yaw_history.pop(0);
    yaw_history.append(yaw)
    yaw_target.pop(0);
    yaw_target.append(target_yaw_val)

    # Draw 4 Mini Graphs in a 2x2 Grid
    gw, gh = 215, 65
    draw_mini_graph(canvas, 15, 515, gw, gh, alt_history, alt_target, f"ALT (Kp:{kp_alt:.2f}) Err:{err_alt:.1f}", 200)
    draw_mini_graph(canvas, 245, 515, gw, gh, fwd_history, fwd_target, f"FWD (Kp:{kp_fwd:.2f}) Err:{err_fwd:.1f}", 200)
    draw_mini_graph(canvas, 15, 595, gw, gh, strafe_history, strafe_target, f"STR (Kp:{kp_str:.2f}) Err:{err_str:.1f}",
                    200)
    draw_mini_graph(canvas, 245, 595, gw, gh, yaw_history, yaw_target, f"YAW (Kp:{kp_yaw:.2f}) Err:{err_yaw:.1f}", 180)

    # Active Mode indicator for tuning keys
    cv2.putText(canvas, f"Tuning Mode: [TAB to cycle] -> {active_gain_mode} (Keys 1-6)", (15, 680),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
    cv2.putText(canvas, "1/2:Kp-|+ | 3/4:Ki-|+ | 5/6:Kd-|+", (15, 702), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200),
                1)

    # ==========================================
    # BOTTOM RIGHT: Keyboard Layout Grid
    # ==========================================
    cv2.rectangle(canvas, (480, 480), (960, 720), (40, 40, 40), -1)

    cv2.putText(canvas, "Flight (QWE/ASD)", (495, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    cv2.putText(canvas, "Translation (I / JKL)", (730, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
    cv2.line(canvas, (715, 490), (715, 710), (70, 70, 70), 1)

    bw, bh = 65, 45
    buttons = [
        ("Q:Takeoff", 'q', 495, 515, bw, bh),
        ("W:Up", 'w', 565, 515, bw, bh),
        ("E:Land", 'e', 635, 515, bw, bh),
        ("A:Rot-L", 'a', 495, 565, bw, bh),
        ("S:Down", 's', 565, 565, bw, bh),
        ("D:Rot-R", 'd', 635, 565, bw, bh),

        ("I:Fwd", 'i', 800, 515, bw, bh),
        ("J:Left", 'j', 730, 565, bw, bh),
        ("K:Back", 'k', 800, 565, bw, bh),
        ("L:Right", 'l', 870, 565, bw, bh),

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


# --- Main Control Loop ---
try:
    print("[Info] Multi-axis Tello station active.")
    # Mock states for local coordinate tracking since Tello position estimation relies on optical flow integration
    mock_fwd_tracker = 0
    mock_strafe_tracker = 0
    mock_yaw_tracker = 0

    frame_count = 0
    battery = tello.get_battery()  # Initial battery fetch

    while True:
        frame = frame_read.frame
        if frame is None or frame.size == 0:
            continue

        # Query battery every 100 frames (~3-5 seconds) to stop video lag
        frame_count += 1
        if frame_count % 100 == 0:
            battery = tello.get_battery()

        alt = tello.get_height()

        update_all_pid_loops(alt, mock_fwd_tracker, mock_strafe_tracker, mock_yaw_tracker)

        ui_canvas = draw_dashboard(frame, alt, mock_fwd_tracker, mock_strafe_tracker, mock_yaw_tracker, battery,
                                   last_key)
        cv2.imshow("Tello Multi-Axis Command Station", ui_canvas)

        key = cv2.waitKey(20) & 0xFF
        if key == 255:
            last_key = "None"
            continue

        last_key = chr(key).lower() if key < 128 else str(key)

        # Flight & Command Handling
        if key == ord('q'):
            tello.takeoff()
            is_flying = True
            target_alt_val = 100.0
        elif key == ord('e'):
            tello.land()
            is_flying = False
            target_alt_val = 0.0
            target_fwd_val = 0.0
            target_strafe_val = 0.0
            target_yaw_val = 0.0
        elif key == ord('w'):
            tello.move_up(30)
            target_alt_val += 30.0
        elif key == ord('s'):
            tello.move_down(30)
            target_alt_val = max(0.0, target_alt_val - 30.0)
        elif key == ord('a'):
            tello.rotate_counter_clockwise(30)
            target_yaw_val -= 30.0
            mock_yaw_tracker -= 30.0
        elif key == ord('d'):
            tello.rotate_clockwise(30)
            target_yaw_val += 30.0
            mock_yaw_tracker += 30.0
        elif key == ord('i'):
            tello.move_forward(30)
            target_fwd_val += 30.0
            mock_fwd_tracker += 30.0
        elif key == ord('k'):
            tello.move_back(30)
            target_fwd_val -= 30.0
            mock_fwd_tracker -= 30.0
        elif key == ord('j'):
            tello.move_left(30)
            target_strafe_val -= 30.0
            mock_strafe_tracker -= 30.0
        elif key == ord('l'):
            tello.move_right(30)
            target_strafe_val += 30.0
            mock_strafe_tracker += 30.0
        elif key == 9:  # TAB key to cycle active tuning axis
            if active_gain_mode == "ALT":
                active_gain_mode = "FWD"
            elif active_gain_mode == "FWD":
                active_gain_mode = "STR"
            elif active_gain_mode == "STR":
                active_gain_mode = "YAW"
            else:
                active_gain_mode = "ALT"
            print(f"[Info] Active tuning axis switched to: {active_gain_mode}")
        # Dynamic Gain Tuning Keys (1 through 6) targeting the currently active axis
        elif key == ord('1'):
            if active_gain_mode == "ALT":
                kp_alt = max(0.0, kp_alt - 0.05)
            elif active_gain_mode == "FWD":
                kp_fwd = max(0.0, kp_fwd - 0.05)
            elif active_gain_mode == "STR":
                kp_str = max(0.0, kp_str - 0.05)
            elif active_gain_mode == "YAW":
                kp_yaw = max(0.0, kp_yaw - 0.05)
        elif key == ord('2'):
            if active_gain_mode == "ALT":
                kp_alt += 0.05
            elif active_gain_mode == "FWD":
                kp_fwd += 0.05
            elif active_gain_mode == "STR":
                kp_str += 0.05
            elif active_gain_mode == "YAW":
                kp_yaw += 0.05
        elif key == ord('3'):
            if active_gain_mode == "ALT":
                ki_alt = max(0.0, ki_alt - 0.01)
            elif active_gain_mode == "FWD":
                ki_fwd = max(0.0, ki_fwd - 0.01)
            elif active_gain_mode == "STR":
                ki_str = max(0.0, ki_str - 0.01)
            elif active_gain_mode == "YAW":
                ki_yaw = max(0.0, ki_yaw - 0.01)
        elif key == ord('4'):
            if active_gain_mode == "ALT":
                ki_alt += 0.01
            elif active_gain_mode == "FWD":
                ki_fwd += 0.01
            elif active_gain_mode == "STR":
                ki_str += 0.01
            elif active_gain_mode == "YAW":
                ki_yaw += 0.01
        elif key == ord('5'):
            if active_gain_mode == "ALT":
                kd_alt = max(0.0, kd_alt - 0.01)
            elif active_gain_mode == "FWD":
                kd_fwd = max(0.0, kd_fwd - 0.01)
            elif active_gain_mode == "STR":
                kd_str = max(0.0, kd_str - 0.01)
            elif active_gain_mode == "YAW":
                kd_yaw = max(0.0, kd_yaw - 0.01)
        elif key == ord('6'):
            if active_gain_mode == "ALT":
                kd_alt += 0.01
            elif active_gain_mode == "FWD":
                kd_fwd += 0.01
            elif active_gain_mode == "STR":
                kd_str += 0.01
            elif active_gain_mode == "YAW":
                kd_yaw += 0.01
        elif key == 27:  # ESC key
            break

finally:
    print("[Info] Landing drone...")
    tello.land()
    tello.streamoff()
    cv2.destroyAllWindows()