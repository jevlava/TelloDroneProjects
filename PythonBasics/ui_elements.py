"""
ui_elements.py
--------------
Reusable UI widgets, custom typography helpers, and styled buttons.
"""

import pygame

# Design Palette
CLR_BG = (240, 244, 248)
CLR_PANEL = (255, 255, 255)
CLR_PRIMARY = (37, 99, 235)  # Royal Blue
CLR_PRIMARY_HOVER = (29, 78, 216)
CLR_PRIMARY_PRESS = (30, 58, 138)
CLR_SUCCESS = (16, 185, 129)  # Green Takeoff
CLR_DANGER = (239, 68, 68)  # Red Land
CLR_NEUTRAL = (100, 116, 139)
CLR_TEXT_DARK = (15, 23, 42)
CLR_TEXT_LIGHT = (255, 255, 255)
CLR_BORDER = (226, 232, 240)


class Button:

    def __init__(
        self,
        rect,
        text,
        base_color=CLR_PRIMARY,
        hover_color=CLR_PRIMARY_HOVER,
        press_color=CLR_PRIMARY_PRESS,
        text_color=CLR_TEXT_LIGHT,
        border_radius=12,
        font_size=18,
    ):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.base_color = base_color
        self.hover_color = hover_color
        self.press_color = press_color
        self.text_color = text_color
        self.border_radius = border_radius
        self.font = pygame.font.SysFont("Inter, Helvetica, Arial", font_size, bold=True)
        self.is_pressed = False

    def draw(self, surface, mouse_pos, is_mouse_held):
        hover = self.rect.collidepoint(mouse_pos)
        self.is_pressed = hover and is_mouse_held

        if self.is_pressed:
            color = self.press_color
        elif hover:
            color = self.hover_color
        else:
            color = self.base_color

        # Subtle elevation shadow
        shadow_rect = self.rect.move(0, 3)
        pygame.draw.rect(
            surface, (200, 210, 220), shadow_rect, border_radius=self.border_radius
        )

        # Button fill
        pygame.draw.rect(
            surface, color, self.rect, border_radius=self.border_radius
        )
        pygame.draw.rect(
            surface,
            CLR_BORDER,
            self.rect,
            width=1,
            border_radius=self.border_radius,
        )

        # Centered Text label
        txt_surface = self.font.render(self.text, True, self.text_color)
        txt_rect = txt_surface.get_rect(center=self.rect.center)
        surface.blit(txt_surface, txt_rect)

    def is_clicked(self, mouse_pos, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(mouse_pos)
        )