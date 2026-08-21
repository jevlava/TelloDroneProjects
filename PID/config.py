# --- Configuration & Initial Parameters ---
HISTORY_LENGTH = 60

# Initial PID Gains
INITIAL_GAINS = {
    "ALT": {"kp": 0.6, "ki": 0.1, "kd": 0.05},
    "FWD": {"kp": 0.5, "ki": 0.05, "kd": 0.02},
    "STR": {"kp": 0.5, "ki": 0.05, "kd": 0.02},
    "YAW": {"kp": 0.4, "ki": 0.02, "kd": 0.01},
}