import cv2
import numpy as np


class AestheticFilters:
    @staticmethod
    def apply_cyberpunk_hud(img, bbox=None):
        h, w, _ = img.shape
        cx, cy = w // 2, h // 2
        # Target reticle
        cv2.circle(img, (cx, cy), 35, (255, 255, 0), 1)
        cv2.line(img, (cx - 50, cy), (cx + 50, cy), (255, 255, 0), 1)
        cv2.line(img, (cx, cy - 50), (cx, cy + 50), (255, 255, 0), 1)

        if bbox:
            cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 0, 255), 2)
            cv2.putText(img, "LOCKED", (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return img

    @staticmethod
    def apply_simulated_thermal(img):
        # Convert RGB to thermal color map simulation
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.applyColorMap(gray, cv2.COLORMAP_JET)