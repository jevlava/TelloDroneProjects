"""
views.py
--------
Encapsulates UI screen layouts for Home Selection and Movement Control sub-views.
"""

import pygame
from ui_elements import (
    CLR_BG,
    CLR_BORDER,
    CLR_DANGER,
    CLR_NEUTRAL,
    CLR_PANEL,
    CLR_PRIMARY,
    CLR_SUCCESS,
    CLR_TEXT_DARK,
    Button,
)


class HomeScreen:

    def __init__(self, screen_width, screen_height):
        self.btn_takeoff = Button(
            (40, 25, 140, 42),
            "TAKEOFF",
            base_color=CLR_SUCCESS,
            hover_color=(5, 150, 105),
        )
        self.btn_land = Button(
            (190, 25, 140, 42),
            "LAND",
            base_color=CLR_DANGER,
            hover_color=(220, 38, 38),
        )

        # 2x2 Grid Layout Dimensions
        grid_x, grid_y = 120, 130
        w, h = 260, 140
        gap_x, gap_y = 40, 30

        self.axis_buttons = {
            "pitch": Button(
                (grid_x, grid_y, w, h),
                "PITCH",
                font_size=22,
                base_color=CLR_PRIMARY,
            ),
            "roll": Button(
                (grid_x + w + gap_x, grid_y, w, h),
                "ROLL",
                font_size=22,
                base_color=CLR_PRIMARY,
            ),
            "throttle": Button(
                (grid_x, grid_y + h + gap_y, w, h),
                "THROTTLE (ALT)",
                font_size=20,
                base_color=CLR_PRIMARY,
            ),
            "yaw": Button(
                (grid_x + w + gap_x, grid_y + h + gap_y, w, h),
                "YAW (ROTATE)",
                font_size=20,
                base_color=CLR_PRIMARY,
            ),
        }

        self.font_title = pygame.font.SysFont(
            "Inter, Helvetica, Arial", 22, bold=True
        )

    def render(self, surface, mouse_pos, is_mouse_held, battery_lvl, is_connected):
        surface.fill(CLR_BG)

        # Header Title
        title_surf = self.font_title.render(
            "Tello Flight Station", True, CLR_TEXT_DARK
        )
        surface.blit(title_surf, (350, 30))

        # Battery Status Pill
        status_text = (
            f"Battery: {battery_lvl}%"
            if is_connected
            else "SIMULATION MODE (NO DRONE)"
        )
        status_color = CLR_SUCCESS if is_connected else CLR_NEUTRAL
        lbl_status = pygame.font.SysFont(
            "Inter, Helvetica", 14, bold=True
        ).render(status_text, True, status_color)
        surface.blit(lbl_status, (550, 35))

        # Draw Global Buttons
        self.btn_takeoff.draw(surface, mouse_pos, is_mouse_held)
        self.btn_land.draw(surface, mouse_pos, is_mouse_held)

        # Render 2x2 Grid
        for btn in self.axis_buttons.values():
            btn.draw(surface, mouse_pos, is_mouse_held)


class MovementScreen:

    def __init__(self, screen_width, screen_height):
        self.btn_back = Button(
            (30, 25, 110, 40),
            "← BACK",
            base_color=CLR_NEUTRAL,
            hover_color=(71, 85, 105),
        )

        # Directional control buttons
        self.btn_left = Button(
            (120, 480, 260, 60),
            "FORWARD",
            font_size=20,
            base_color=CLR_PRIMARY,
        )
        self.btn_right = Button(
            (420, 480, 260, 60),
            "BACKWARD",
            font_size=20,
            base_color=CLR_PRIMARY,
        )

        self.labels = {
            "pitch": ("FORWARD (+Pitch)", "BACKWARD (-Pitch)"),
            "roll": ("LEFT (-Roll)", "RIGHT (+Roll)"),
            "throttle": ("CLIMB UP (+Throttle)", "DESCENT DOWN (-Throttle)"),
            "yaw": ("ROTATE LEFT (-Yaw)", "ROTATE RIGHT (+Yaw)"),
        }

        self.font_title = pygame.font.SysFont(
            "Inter, Helvetica, Arial", 22, bold=True
        )

    def configure_axis(self, axis_key):
        lbl_left, lbl_right = self.labels.get(
            axis_key, ("OPTION 1", "OPTION 2")
        )
        self.btn_left.text = lbl_left
        self.btn_right.text = lbl_right

    def render(
        self,
        surface,
        mouse_pos,
        is_mouse_held,
        axis_key,
        drone_renderer,
        direction_val,
    ):
        surface.fill(CLR_BG)

        # Header Title
        title_surf = self.font_title.render(
            f"Axis Control: {axis_key.upper()}", True, CLR_TEXT_DARK
        )
        surface.blit(title_surf, (160, 30))

        self.btn_back.draw(surface, mouse_pos, is_mouse_held)

        # Draw Center Drone Diagram & Thrust Animations
        drone_renderer.draw_diagram(
            surface,
            center_x=400,
            center_y=260,
            active_axis=axis_key,
            direction_val=direction_val,
        )

        # Draw Bottom Movement Control Buttons
        self.btn_left.draw(surface, mouse_pos, is_mouse_held)
        self.btn_right.draw(surface, mouse_pos, is_mouse_held)