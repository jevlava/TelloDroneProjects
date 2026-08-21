import cv2
import numpy as np

def crop_black_borders(img):
    """Crops black borders from an image canvas (e.g. OpenCV warped panoramas)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        return img[y:y+h, x:x+w]
    return img


def seamless_blend_strip(images, overlap_ratio=0.25):
    if not images:
        return None
    if len(images) == 1:
        return images[0]

    base_h = images[0].shape[0]
    resized = []
    for img in images:
        h, w = img.shape[:2]
        if h != base_h:
            img = cv2.resize(img, (int(w * (base_h / h)), base_h))
        resized.append(img.astype(np.float32))

    result = resized[0]
    for next_img in resized[1:]:
        w_res, w_next = result.shape[1], next_img.shape[1]
        overlap_px = int(min(w_res, w_next) * overlap_ratio)

        if overlap_px <= 0:
            result = np.hstack([result, next_img])
            continue

        zone_res = result[:, -overlap_px:]
        zone_next = next_img[:, :overlap_px]
        gain = (np.mean(zone_res) + 1e-5) / (np.mean(zone_next) + 1e-5)
        next_img_matched = np.clip(next_img * gain, 0, 255)

        alpha = np.linspace(1.0, 0.0, overlap_px, dtype=np.float32).reshape(1, overlap_px, 1)
        blended_overlap = (result[:, -overlap_px:] * alpha) + (next_img_matched[:, :overlap_px] * (1.0 - alpha))

        result = np.hstack([result[:, :-overlap_px], blended_overlap, next_img_matched[:, overlap_px:]])

    return np.clip(result, 0, 255).astype(np.uint8)


def draw_hud_guide(frame, battery, tracking_active, face_locked, lock_progress=0.0, nav_status="", face_area=0):
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (200, 230), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    batt_color = (0, 255, 0) if battery > 30 else (0, 0, 255)
    cv2.putText(frame, f"BATTERY: {battery}%", (12, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, batt_color, 1)

    if face_locked:
        status_str = "LOCKED (READY)"
        status_color = (0, 255, 0)
    elif tracking_active:
        status_str = f"LOCKING ({int(lock_progress * 100)}%)"
        status_color = (0, 215, 255)
    else:
        status_str = "SEARCHING FACE"
        status_color = (0, 0, 255)

    cv2.putText(frame, f"STATUS: {status_str}", (12, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, status_color, 1)
    cv2.putText(frame, f"NAV: {nav_status}", (12, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1)
    cv2.putText(frame, f"AREA: {face_area} px", (12, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (200, 200, 200), 1)

    cv2.putText(frame, "--- CONTROLS GUIDE ---", (12, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

    gesture_text_color = (200, 255, 200) if face_locked else (128, 128, 128)
    cv2.putText(frame, "[✌️] Peace    : Snap Photo", (12, 102),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, gesture_text_color, 1)
    cv2.putText(frame, "[👍] ThumbsUp : 5-Photo Burst Strip", (12, 117),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, gesture_text_color, 1)
    cv2.putText(frame, "[🤙] Shaka    : 5-Angle Fisheye Pano", (12, 132),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, gesture_text_color, 1)
    cv2.putText(frame, "[👌] OK Sign  : 360 Video Sweep", (12, 147),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, gesture_text_color, 1)
    cv2.putText(frame, "[P] Key      : 180 Stepped Pano", (12, 162),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 0), 1)
    cv2.putText(frame, "[Q] / [ESC]   : Land Drone", (12, 177),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (200, 200, 255), 1)