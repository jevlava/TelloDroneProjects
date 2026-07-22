"""
Project: DJI Tello Real-Time Interactive Flight Control & Directional Assistant
Author: John Lava & AI Assistant

Description:
    UI-driven control interface with directional visual diagrams.
    Select a movement axis (Pitch, Roll, Altitude, Yaw) to view
    movement arrows and execute directional flight commands.
"""

import math
import sys
import pygame
from djitellopy import tello

# Initialize Pygame & Fonts
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 700, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DJI Tello Directional Flight Control")

# UI Design System
BG_COLOR = (245, 247, 250)
PANEL_BG = (255, 255, 255)
PRIMARY = (41, 128, 185)
PRIMARY_HOVER = (52, 152, 219)
PRIMARY_ACTIVE = (52, 73, 94)
ACCENT = (231, 76, 60)
TEXT_DARK = (44, 62, 80)
TEXT_LIGHT = (255, 255, 255)
BORDER_COLOR = (218, 225, 231)

FONT_TITLE = pygame.font.SysFont("Helvetica", 20, bold=True)
FONT_BTN = pygame.font.SysFont("Helvetica", 15, bold=True)

# Speed setting for RC velocity signals (-100 to 100)
SPEED = 40

# Initialize Tello Drone connection safely
tello_connected = False
try:
    me = tello.Tello()
    me.connect()
    print(f"[INFO] Connected to Tello! Battery: {me.get_battery()}%")
    tello_connected = True
except Exception as e:
    print(f"[WARN] Tello connection skipped: {e}")
    print("[INFO] Running in GUI Visualization Mode (No drone active)")


# ============================================================
# DRAWING HELPERS
# ============================================================
def draw_button(rect, text, active=False, hover=False):
    """Renders a styled UI button with hover and active state colors."""
    if active:
        color = PRIMARY_ACTIVE
    elif hover:
        color = PRIMARY_HOVER
    else:
        color = PRIMARY

    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, BORDER_COLOR, rect, width=1, border_radius=8)

    txt_surf = FONT_BTN.render(text, True, TEXT_LIGHT)
    txt_rect = txt_surf.get_rect(center=rect.center)
    screen.blit(txt_surf, txt_rect)


def draw_arrow(surface, start, end, color, body_width=6, head_size=14):
    """Draws a directional vector arrow from start point to end point."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)

    # Draw body line
    pygame.draw.line(surface, color, start, end, body_width)

    # Draw triangular head
    arrow_p1 = (
        end[0] - head_size * math.cos(angle - math.pi / 6),
        end[1] - head_size * math.sin(angle - math.pi / 6),
    )
    arrow_p2 = (
        end[0] - head_size * math.cos(angle + math.pi / 6),
        end[1] - head_size * math.sin(angle + math.pi / 6),
    )
    pygame.draw.polygon(surface, color, [end, arrow_p1, arrow_p2])


def draw_drone_diagram(center_x, center_y, active_axis, direction_val):
    """
    Renders a visual top-down quadrotor schematic with active movement arrows.
    """
    # Main Box Container
    box_rect = pygame.Rect(center_x - 180, center_y - 120, 360, 240)
    pygame.draw.rect(screen, PANEL_BG, box_rect, border_radius=12)
    pygame.draw.rect(screen, BORDER_COLOR, box_rect, width=2, border_radius=12)

    # Central Drone Chassis
    body_radius = 24
    pygame.draw.circle(
        screen, (120, 140, 160), (center_x, center_y), body_radius
    )

    # Quadrotor Arms & Rotors
    arm_offset = 55
    motors = [
        (center_x - arm_offset, center_y - arm_offset),
        (center_x + arm_offset, center_y - arm_offset),
        (center_x - arm_offset, center_y + arm_offset),
        (center_x + arm_offset, center_y + arm_offset),
    ]

    for mx, my in motors:
        pygame.draw.line(screen, (160, 175, 190), (center_x, center_y), (mx, my), 4)
        pygame.draw.circle(screen, (80, 90, 100), (mx, my), 14)
        pygame.draw.circle(screen, (200, 210, 220), (mx, my), 10)

    # Drone Heading Notch (Front Indicator)
    pygame.draw.polygon(
        screen,
        PRIMARY,
        [
            (center_x - 8, center_y - body_radius + 2),
            (center_x + 8, center_y - body_radius + 2),
            (center_x, center_y - body_radius - 8),
        ],
    )

    # Draw Movement Indicator Vectors
    if active_axis and direction_val != 0:
        arrow_len = 70

        if active_axis == "pitch":
            # Forward (+1) / Backward (-1)
            end_y = center_y - (arrow_len * direction_val)
            draw_arrow(
                screen,
                (center_x, center_y),
                (center_x, end_y),
                ACCENT,
                body_width=8,
                head_size=16,
            )

        elif active_axis == "roll":
            # Right (+1) / Left (-1)
            end_x = center_x + (arrow_len * direction_val)
            draw_arrow(
                screen,
                (center_x, center_y),
                (end_x, center_y),
                ACCENT,
                body_width=8,
                head_size=16,
            )

        elif active_axis == "altitude":
            # Up (+1) / Down (-1)
            sign = "UP" if direction_val > 0 else "DOWN"
            offset = -70 if direction_val > 0 else 70
            draw_arrow(
                screen,
                (center_x + 110, center_y),
                (center_x + 110, center_y + offset),
                ACCENT,
                body_width=8,
                head_size=16,
            )
            txt = FONT_BTN.render(sign, True, ACCENT)
            screen.blit(txt, (center_x + 95, center_y + (offset / 2) - 10))

        elif active_axis == "yaw":
            # Rotate Right (+1) / Rotate Left (-1)
            if direction_val > 0:
                draw_arrow(
                    screen,
                    (center_x + 45, center_y - 45),
                    (center_x + 65, center_y - 25),
                    ACCENT,
                    body_width=6,
                    head_size=14,
                )
            else:
                draw_arrow(
                    screen,
                    (center_x - 45, center_y - 45),
                    (center_x - 65, center_y - 25),
                    ACCENT,
                    body_width=6,
                    head_size=14,
                )


def send_flight_pulse(lr, fb, ud, yv):
    """Sends active RC velocity commands to the physical Tello drone."""
    if tello_connected:
        me.send_rc_control(lr, fb, ud, yv)


# ============================================================
# MAIN CONTROL LOOP
# ============================================================
def main():
    clock = pygame.time.Clock()

    # Default axis selection state
    selected_axis = "pitch"

    # Top Row Axis Selector Rectangles
    axis_buttons = {
        "pitch": pygame.Rect(30, 80, 140, 45),
        "roll": pygame.Rect(195, 80, 140, 45),
        "altitude": pygame.Rect(360, 80, 140, 45),
        "yaw": pygame.Rect(525, 80, 140, 45),
    }

    # Bottom Row Directional Control Rectangles
    btn_dir_left = pygame.Rect(180, 410, 160, 50)
    btn_dir_right = pygame.Rect(360, 410, 160, 50)

    # Flight Utility Rectangles
    btn_takeoff = pygame.Rect(30, 20, 100, 35)
    btn_land = pygame.Rect(140, 20, 100, 35)

    # Dynamic direction labels corresponding to (-1, +1) directions
    dir_labels = {
        "pitch": ("Backward", "Forward"),
        "roll": ("Left", "Right"),
        "altitude": ("Down", "Up"),
        "yaw": ("Rotate Left", "Rotate Right"),
    }

    while True:
        mouse_pos = pygame.mouse.get_pos()
        # Continuously poll primary mouse button state (True while held down)
        mouse_held = pygame.mouse.get_pressed()[0]

        direction_val = 0
        screen.fill(BG_COLOR)

        # ----------------------------------------------------
        # 1. Discrete Event Handling (Single Clicks)
        # ----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if tello_connected:
                    me.send_rc_control(0, 0, 0, 0)
                    me.land()
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Select Axis Mode
                for axis_key, rect in axis_buttons.items():
                    if rect.collidepoint(mouse_pos):
                        selected_axis = axis_key

                # Flight Takeoff / Land
                if btn_takeoff.collidepoint(mouse_pos) and tello_connected:
                    me.takeoff()
                elif btn_land.collidepoint(mouse_pos) and tello_connected:
                    me.land()

        # ----------------------------------------------------
        # 2. Continuous Input Polling (Button Holding)
        # ----------------------------------------------------
        if mouse_held:
            if btn_dir_left.collidepoint(mouse_pos):
                direction_val = -1
            elif btn_dir_right.collidepoint(mouse_pos):
                direction_val = 1

        # ----------------------------------------------------
        # 3. Calculate RC Velocity Vectors
        # ----------------------------------------------------
        lr, fb, ud, yv = 0, 0, 0, 0
        if direction_val != 0:
            if selected_axis == "pitch":
                fb = SPEED * direction_val
            elif selected_axis == "roll":
                lr = SPEED * direction_val
            elif selected_axis == "altitude":
                ud = SPEED * direction_val
            elif selected_axis == "yaw":
                yv = SPEED * direction_val

        # Stream continuous RC control commands frame-by-frame
        send_flight_pulse(lr, fb, ud, yv)

        # ----------------------------------------------------
        # 4. GUI Rendering
        # ----------------------------------------------------
        title_surf = FONT_TITLE.render(
            "Tello Movement Diagram & Directional Control", True, TEXT_DARK
        )
        screen.blit(title_surf, (255, 25))

        # Takeoff & Land Buttons
        draw_button(
            btn_takeoff, "Takeoff", hover=btn_takeoff.collidepoint(mouse_pos)
        )
        draw_button(btn_land, "Land", hover=btn_land.collidepoint(mouse_pos))

        # Render Top Axis Buttons
        for axis_key, rect in axis_buttons.items():
            draw_button(
                rect,
                axis_key.upper(),
                active=(selected_axis == axis_key),
                hover=rect.collidepoint(mouse_pos),
            )

        # Render Drone Diagram & Vectors
        draw_drone_diagram(
            center_x=WIDTH // 2,
            center_y=260,
            active_axis=selected_axis,
            direction_val=direction_val,
        )

        # Render Directional Sub-Buttons
        if selected_axis in dir_labels:
            label_neg, label_pos = dir_labels[selected_axis]
            draw_button(
                btn_dir_left,
                label_neg,
                active=(direction_val == -1),
                hover=btn_dir_left.collidepoint(mouse_pos),
            )
            draw_button(
                btn_dir_right,
                label_pos,
                active=(direction_val == 1),
                hover=btn_dir_right.collidepoint(mouse_pos),
            )

        pygame.display.flip()
        clock.tick(30)  # Stream RC velocity updates at ~30 Hz


if __name__ == "__main__":
    main()