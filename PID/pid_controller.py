from config import INITIAL_GAINS


class MultiAxisPID:
    def __init__(self):
        self.gains = INITIAL_GAINS.copy()
        self.active_mode = "ALT"  # ALT, FWD, STR, YAW

        # Targets & Errors for 4 axes
        self.targets = {"ALT": 0.0, "FWD": 0.0, "STR": 0.0, "YAW": 0.0}
        self.errors = {"ALT": 0.0, "FWD": 0.0, "STR": 0.0, "YAW": 0.0}

        # Internal PID states (Integral sums, previous errors)
        self.states = {
            "ALT": {"int": 0.0, "prev_err": 0.0},
            "FWD": {"int": 0.0, "prev_err": 0.0},
            "STR": {"int": 0.0, "prev_err": 0.0},
            "YAW": {"int": 0.0, "prev_err": 0.0},
        }

    def reset_targets(self):
        for axis in self.targets:
            self.targets[axis] = 0.0

    def update_loops(self, current_vals, is_flying):
        if not is_flying:
            self.reset_targets()

        outputs = {}
        for axis in ["ALT", "FWD", "STR", "YAW"]:
            err = self.targets[axis] - current_vals[axis]
            self.errors[axis] = err

            # PID Math
            p = self.gains[axis]["kp"] * err

            # Integral clamping to prevent windup
            self.states[axis]["int"] = max(-300, min(300, self.states[axis]["int"] + err))
            i = self.gains[axis]["ki"] * self.states[axis]["int"]

            d = self.gains[axis]["kd"] * (err - self.states[axis]["prev_err"])
            self.states[axis]["prev_err"] = err

            outputs[axis] = p + i + d
        return outputs

    def cycle_axis(self):
        axes = ["ALT", "FWD", "STR", "YAW"]
        idx = axes.index(self.active_mode)
        self.active_mode = axes[(idx + 1) % len(axes)]
        print(f"[Info] Active tuning axis switched to: {self.active_mode}")

    def adjust_gain(self, param, delta):
        # param: 'kp', 'ki', or 'kd'
        current_val = self.gains[self.active_mode][param]
        new_val = max(0.0, current_val + delta)
        self.gains[self.active_mode][param] = round(new_val, 3)