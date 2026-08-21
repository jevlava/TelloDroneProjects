"""
drone_renderer.py
-----------------
Visual quadcopter rendering engine with rotor thrust dynamics & vector arrow indicators.
"""

import math
import pygame

COLOR_ROTOR_NEUTRAL = (148, 163, 184)  # Grey idle
COLOR_ROTOR_FAST = (239, 68, 68)  # Red high-thrust
COLOR_ROTOR_SLOW = (34, 197, 94)  # Green low-thrust
COLOR_ARROW = (59, 130, 246)  # Dynamic blue indicator


class DroneRenderer:

    def __init__(self):
        self.rotor_angle = 0.0

    def draw_arrow(
        self, surface, start_pos, end_pos, color=COLOR_ARROW, width=10, head_size=20
    ):
        """Renders vector arrows pointing in active movement directions."""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        angle = math.atan2(dy, dx)

        pygame.draw.line(surface, color, start_pos, end_pos, width)

        p1 = (
            end_pos[0] - head_size * math.cos(angle - math.pi / 6),
            end_pos[1] - head_size * math.sin(angle - math.pi / 6),
        )
        p2 = (
            end_pos[0] - head_size * math.cos(angle + math.pi / 6),
            end_pos[1] - head_size * math.sin(angle + math.pi / 6),
        )
        pygame.draw.polygon(surface, color, [end_pos, p1, p2])

    def get_motor_thrust_colors(self, active_axis, direction_val):
        """
        Maps differential thrust colors based on drone flight physics.
        Motors: [Front-Left, Front-Right, Rear-Left, Rear-Right]
        """
        colors = [COLOR_ROTOR_NEUTRAL] * 4
        if direction_val == 0 or not active_axis:
            return colors

        if active_axis == "pitch":
            if direction_val > 0:  # Forward (Rear motors speed up, Front slow down)
                return [
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_FAST,
                ]
            else:  # Backward
                return [
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_SLOW,
                ]

        elif active_axis == "roll":
            if direction_val > 0:  # Right (Left motors speed up, Right slow down)
                return [
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_SLOW,
                ]
            else:  # Left
                return [
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_FAST,
                ]

        elif active_axis == "throttle":
            if direction_val > 0:  # Up (All motors high thrust)
                return [COLOR_ROTOR_FAST] * 4
            else:  # Down (All motors low thrust)
                return [COLOR_ROTOR_SLOW] * 4

        elif active_axis == "yaw":
            if direction_val > 0:  # Rotate Right (Diagonal CCW pairs speed up)
                return [
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_FAST,
                ]
            else:  # Rotate Left
                return [
                    COLOR_ROTOR_SLOW,
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_FAST,
                    COLOR_ROTOR_SLOW,
                ]

        return colors

    def draw_diagram(
        self, surface, center_x, center_y, active_axis=None, direction_val=0
    ):
        """Renders the central top-down quadrotor with spinning propellers."""
        self.rotor_angle = (self.rotor_angle + 0.25) % (2 * math.pi)
        thrust_colors = self.get_motor_thrust_colors(
            active_axis, direction_val
        )

        arm_length = 80
        # Motor positions relative to center: FL, FR, RL, RR
        motor_offsets = [
            (-arm_length, -arm_length),
            (arm_length, -arm_length),
            (-arm_length, arm_length),
            (arm_length, arm_length),
        ]

        # Draw Frame Arms
        for mx, my in motor_offsets:
            pygame.draw.line(
                surface,
                (100, 116, 139),
                (center_x, center_y),
                (center_x + mx, center_y + my),
                8,
            )

        # Draw Main Carbon Chassis
        body_radius = 32
        pygame.draw.circle(
            surface, (30, 41, 59), (center_x, center_y), body_radius
        )
        pygame.draw.circle(
            surface, (71, 85, 105), (center_x, center_y), body_radius - 6
        )

        # Front Heading Indicator Chevron
        chevron = [
            (center_x - 12, center_y - body_radius + 4),
            (center_x + 12, center_y - body_radius + 4),
            (center_x, center_y - body_radius - 14),
        ]
        pygame.draw.polygon(surface, (239, 68, 68), chevron)

        # Draw Motors and Propellers
        rotor_radius = 28
        for i, (mx, my) in enumerate(motor_offsets):
            cx, cy = center_x + mx, center_y + my

            # Motor Mount Base
            pygame.draw.circle(surface, (51, 65, 85), (cx, cy), 16)
            pygame.draw.circle(surface, thrust_colors[i], (cx, cy), 12)

            # Propeller Blade Spin Animation
            blade_angle = (
                self.rotor_angle if i % 2 == 0 else -self.rotor_angle
            )
            dx1 = rotor_radius * math.cos(blade_angle)
            dy1 = rotor_radius * math.sin(blade_angle)
            dx2 = rotor_radius * math.cos(blade_angle + math.pi / 2)
            dy2 = rotor_radius * math.sin(blade_angle + math.pi / 2)

            pygame.draw.line(
                surface,
                (255, 255, 255),
                (cx - dx1, cy - dy1),
                (cx + dx1, cy + dy1),
                4,
            )
            pygame.draw.line(
                surface,
                (255, 255, 255),
                (cx - dx2, cy - dy2),
                (cx + dx2, cy + dy2),
                4,
            )

        # Render Active Flight Motion Direction Vectors
        if active_axis and direction_val != 0:
            if active_axis == "pitch":
                start_y = center_y + (100 if direction_val > 0 else -100)
                end_y = center_y - (140 if direction_val > 0 else -140)
                self.draw_arrow(surface, (center_x, start_y), (center_x, end_y))

            elif active_axis == "roll":
                start_x = center_x - (100 if direction_val > 0 else -100)
                end_x = center_x + (140 if direction_val > 0 else -140)
                self.draw_arrow(surface, (start_x, center_y), (end_x, center_y))

            elif active_axis == "throttle":
                # Render dual side arrows for climb/descent
                sign = 1 if direction_val > 0 else -1
                self.draw_arrow(
                    surface,
                    (center_x + 130, center_y + sign * 60),
                    (center_x + 130, center_y - sign * 80),
                )
                self.draw_arrow(
                    surface,
                    (center_x - 130, center_y + sign * 60),
                    (center_x - 130, center_y - sign * 80),
                )

            elif active_axis == "yaw":
                # Rotation vector arc indicators
                offset = 120
                if direction_val > 0:  # Clockwise
                    self.draw_arrow(
                        surface,
                        (center_x - offset, center_y - 60),
                        (center_x + offset, center_y - 60),
                    )
                    self.draw_arrow(
                        surface,
                        (center_x + offset, center_y + 60),
                        (center_x - offset, center_y + 60),
                    )
                else:  # Counter-Clockwise
                    self.draw_arrow(
                        surface,
                        (center_x + offset, center_y - 60),
                        (center_x - offset, center_y - 60),
                    )
                    self.draw_arrow(
                        surface,
                        (center_x - offset, center_y + 60),
                        (center_x + offset, center_y + 60),
                    )