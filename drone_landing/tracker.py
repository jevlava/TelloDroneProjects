# tracker.py
import cv2

def create_tracker():
    """
    Factory function that creates a CSRT tracker with fallbacks.
    CSRT (Channel and Spatial Reliability Tracking) is ideal for high accuracy.
    """
    if hasattr(cv2, 'TrackerCSRT_create'):
        return cv2.TrackerCSRT_create()
    elif hasattr(cv2, 'legacy') and hasattr(cv2.legacy, 'TrackerCSRT_create'):
        return cv2.legacy.TrackerCSRT_create()
    elif hasattr(cv2, 'TrackerMIL_create'):
        return cv2.TrackerMIL_create()
    else:
        raise RuntimeError("No compatible OpenCV tracker algorithm found in your installed package.")