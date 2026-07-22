"""
main.py
-------
Main application loop, event router, and continuous RC stream controller.
"""

import sys
import pygame
from drone_controller import DroneController
from drone_renderer import DroneRenderer
from views import HomeScreen, MovementScreen

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 580
SPEED_SETTING = 50  # Velocity pulse standard (-100 to 100)


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("DJI Tello Professional Flight Controller")
    clock = pygame.time.Clock()

    # Instantiate Hardware & Render Engine Modules
    drone_ctrl = DroneController(default_speed=SPEED_SETTING)
    drone_renderer = DroneRenderer()

    # Views
    home_view = HomeScreen(SCREEN_WIDTH, SCREEN_HEIGHT)
    movement_view = MovementScreen(SCREEN_WIDTH, SCREEN_HEIGHT)

    # State Machine Variables
    current_screen = "HOME"  # 'HOME' or 'MOVEMENT'
    selected_axis = None  # 'pitch', 'roll', 'throttle', 'yaw'

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        is_mouse_held = pygame.mouse.get_pressed()[0]

        # ----------------------------------------------------
        # 1. Discrete Event Dispatch Loop
        # ----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Handle Global Takeoff / Land from Home View
                if current_screen == "HOME":
                    if home_view.btn_takeoff.is_clicked(mouse_pos, event):
                        drone_ctrl.takeoff()
                    elif home_view.btn_land.is_clicked(mouse_pos, event):
                        drone_ctrl.land()

                    # Axis Selection
                    for axis_key, btn in home_view.axis_buttons.items():
                        if btn.is_clicked(mouse_pos, event):
                            selected_axis = axis_key
                            movement_view.configure_axis(selected_axis)
                            current_screen = "MOVEMENT"

                elif current_screen == "MOVEMENT":
                    if movement_view.btn_back.is_clicked(mouse_pos, event):
                        current_screen = "HOME"
                        selected_axis = None

        # ----------------------------------------------------
        # 2. Continuous Input Polling (Mouse Button Hold)
        # ----------------------------------------------------
        direction_val = 0
        if current_screen == "MOVEMENT" and is_mouse_held:
            if movement_view.btn_left.rect.collidepoint(mouse_pos):
                direction_val = 1  # Forward / Left / Climb / Rotate Left
            elif movement_view.btn_right.rect.collidepoint(mouse_pos):
                direction_val = -1  # Backward / Right / Descent / Rotate Right

        # ----------------------------------------------------
        # 3. Stream RC Velocities (Corrected Mapping & Indentation)
        # ----------------------------------------------------
        lr, fb, ud, yv = 0, 0, 0, 0
        if direction_val != 0 and selected_axis:
            speed = SPEED_SETTING * direction_val

            if selected_axis == "pitch":
                # Forward (+50) / Backward (-50)
                fb = speed

            elif selected_axis == "roll":
                # Left (-50) / Right (+50)
                lr = -speed

            elif selected_axis == "throttle":
                # Climb Up (+50) / Descent Down (-50)
                ud = speed

            elif selected_axis == "yaw":
                # Rotate Left (-50) / Rotate Right (+50)
                yv = -speed

        # Stream command frame-by-frame (sends 0,0,0,0 when released)
        drone_ctrl.send_rc(lr, fb, ud, yv)

        # ----------------------------------------------------
        # 4. Rendering Phase
        # ----------------------------------------------------
        if current_screen == "HOME":
            home_view.render(
                screen,
                mouse_pos,
                is_mouse_held,
                drone_ctrl.battery,
                drone_ctrl.is_connected,
            )
        elif current_screen == "MOVEMENT":
            movement_view.render(
                screen,
                mouse_pos,
                is_mouse_held,
                selected_axis,
                drone_renderer,
                direction_val,
            )

        pygame.display.flip()
        clock.tick(30)  # Maintain 30 FPS / ~30Hz RC signal rate

    # Clean Termination
    drone_ctrl.disconnect()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()