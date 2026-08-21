import os
import time
import cv2
import threading
import numpy as np
from config import PANORAMAS_DIR, BURSTS_DIR, VIDEOS_DIR
from utils import crop_black_borders, seamless_blend_strip

def execute_180_panorama(tello, frame_read):
    print("--- STARTING 180-DEGREE STEPPED PANORAMA ROUTINE ---")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    final_pano_path = os.path.join(PANORAMAS_DIR, f"180_pano_{timestamp}.jpg")

    tello.send_rc_control(0, 0, 0, 0)
    time.sleep(0.5)

    captured_frames = []

    def capture_frame(step_num, angle_deg):
        raw_rgb = frame_read.frame
        if raw_rgb is not None:
            bgr_frame = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2BGR)
            captured_frames.append(bgr_frame)
            frame_path = os.path.join(PANORAMAS_DIR, f"180_frame_{timestamp}_step{step_num}_{angle_deg}deg.jpg")
            cv2.imwrite(frame_path, bgr_frame)

    tello.rotate_counter_clockwise(90)
    time.sleep(0.8)

    capture_frame(1, -90)

    current_angle = -90
    for step in range(1, 7):
        tello.rotate_clockwise(30)
        time.sleep(0.6)
        current_angle += 30
        capture_frame(step + 1, current_angle)

    tello.rotate_counter_clockwise(90)
    time.sleep(0.8)
    tello.send_rc_control(0, 0, 0, 0)

    stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
    status, stitched_img = stitcher.stitch(captured_frames)

    if status == cv2.Stitcher_OK:
        cropped_img = crop_black_borders(stitched_img)
        cv2.imwrite(final_pano_path, cropped_img)
        print(f"SUCCESS: 180-Degree Panorama saved -> {final_pano_path}")
    else:
        fallback_path = final_pano_path.replace(".jpg", "_fallback.jpg")
        print("Stitcher keypoint match low. Applying seamless gradient alpha fallback...")
        pano_fallback = seamless_blend_strip(captured_frames, overlap_ratio=0.25)
        if pano_fallback is not None:
            cv2.imwrite(fallback_path, pano_fallback)
            print(f"SUCCESS: Seamless blended 180 panorama strip saved -> {fallback_path}")


def execute_roll_panorama(tello, frame_read):
    print("--- STARTING 5-ANGLE ROTATIONAL FISHEYE/PANORAMIC CAPTURE ---")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    single_pano_path = os.path.join(PANORAMAS_DIR, f"fisheye_pano_{timestamp}.jpg")

    tello.send_rc_control(0, 0, 0, 0)
    time.sleep(0.5)

    frames_dict = {}

    def capture_angle_frame(key, label):
        raw_rgb = frame_read.frame
        if raw_rgb is not None:
            bgr_frame = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2BGR)
            frames_dict[key] = bgr_frame

    capture_angle_frame("center", "0_deg")

    tello.rotate_clockwise(45)
    time.sleep(0.6)
    capture_angle_frame("right_45", "+45_deg")

    tello.rotate_clockwise(45)
    time.sleep(0.6)
    capture_angle_frame("right_90", "+90_deg")

    tello.rotate_counter_clockwise(135)
    time.sleep(0.9)
    capture_angle_frame("left_45", "-45_deg")

    tello.rotate_counter_clockwise(45)
    time.sleep(0.6)
    capture_angle_frame("left_90", "-90_deg")

    tello.rotate_clockwise(90)
    time.sleep(0.8)
    tello.send_rc_control(0, 0, 0, 0)

    ordered_keys = ["left_90", "left_45", "center", "right_45", "right_90"]
    ordered_frames = [frames_dict[k] for k in ordered_keys if k in frames_dict]

    stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
    status, stitched_img = stitcher.stitch(ordered_frames)

    if status == cv2.Stitcher_OK:
        cropped_img = crop_black_borders(stitched_img)
        cv2.imwrite(single_pano_path, cropped_img)
        print(f"SUCCESS: Fisheye Panorama saved -> {single_pano_path}")
    else:
        fallback_path = single_pano_path.replace(".jpg", "_fallback.jpg")
        print("Stitcher feature matching low. Building seamlessly blended fallback panorama...")
        pano_fallback = seamless_blend_strip(ordered_frames, overlap_ratio=0.30)
        if pano_fallback is not None:
            cv2.imwrite(fallback_path, pano_fallback)
            print(f"SUCCESS: Seamless blended panorama strip saved -> {fallback_path}")


def execute_shaka_burst_sequence(tello, frame_read):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    tello.send_rc_control(0, 0, 0, 0)
    time.sleep(0.3)

    frames_dict = {}

    def capture_frame(key):
        frame = frame_read.frame
        if frame is not None:
            frames_dict[key] = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    capture_frame("center")

    tello.move_right(40)
    time.sleep(0.7)
    capture_frame("right_1")

    tello.move_right(40)
    time.sleep(0.7)
    capture_frame("right_2")

    tello.move_left(120)
    time.sleep(1.0)
    capture_frame("left_1")

    tello.move_left(40)
    time.sleep(0.7)
    capture_frame("left_2")

    tello.move_right(80)
    time.sleep(0.8)
    tello.send_rc_control(0, 0, 0, 0)

    ordered_keys = ["left_2", "left_1", "center", "right_1", "right_2"]
    ordered_frames = [frames_dict[k] for k in ordered_keys if k in frames_dict]

    if len(ordered_frames) == 5:
        base_h = ordered_frames[0].shape[0]
        resized_frames = []
        for img in ordered_frames:
            h, w = img.shape[:2]
            if h != base_h:
                img = cv2.resize(img, (int(w * (base_h / h)), base_h))
            resized_frames.append(img)

        side_by_side_strip = np.hstack(resized_frames)
        composite_path = os.path.join(BURSTS_DIR, f"burst_side_by_side_{timestamp}.jpg")
        cv2.imwrite(composite_path, side_by_side_strip)
        print(f"SUCCESS: Side-by-side burst strip saved -> {composite_path}")


def execute_360_video_sweep(tello, frame_read):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(VIDEOS_DIR, f"360_video_{timestamp}.mp4")

    raw_sample = frame_read.frame
    h, w, _ = raw_sample.shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (w, h))

    recording = True

    def record_loop():
        while recording:
            frame = frame_read.frame
            if frame is not None:
                out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            time.sleep(0.03)

    tello.send_rc_control(0, 0, 0, 0)
    record_thread = threading.Thread(target=record_loop)
    record_thread.start()

    for _ in range(4):
        tello.rotate_clockwise(90)
        time.sleep(0.1)

    recording = False
    record_thread.join()
    out.release()