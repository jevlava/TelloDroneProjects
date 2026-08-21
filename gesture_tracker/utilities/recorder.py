# utils/recorder.py

import cv2
import time
import datetime
import config

is_recording_360 = False
video_writer = None


def record_360_panorama(tello_instance):
    """Executes a 360-degree rotation while recording frames."""
    global is_recording_360, video_writer

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"360_video_{timestamp}.avi"
    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    print(f"🎥 Starting 360° Panorama: {filename}")
    video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (config.WIDTH, config.HEIGHT))
    is_recording_360 = True

    start_turn = time.time()
    while time.time() - start_turn < 9.0:
        tello_instance.send_rc_control(0, 0, 0, 40)
        time.sleep(0.05)

    tello_instance.send_rc_control(0, 0, 0, 0)
    time.sleep(0.5)

    is_recording_360 = False
    if video_writer:
        video_writer.release()
        video_writer = None
    print(f"✅ 360° Video Saved: {filename}")


def write_frame_if_recording(frame):
    """Helper to append video frames if actively recording."""
    if is_recording_360 and video_writer is not None:
        video_writer.write(frame)