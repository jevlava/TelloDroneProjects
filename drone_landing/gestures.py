# gestures.py
import cv2
import mediapipe as mp
from config import FRAME_WIDTH, FRAME_HEIGHT


class GestureAnalyzer:
    def __init__(self):
        # Initialize Google MediaPipe Hands module
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

    def process_frame(self, frame):
        """
        Processes a frame and identifies hand gestures.
        Returns: (gesture_type, pointing_coordinates_tuple)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        gesture = "NONE"
        pointing_coords = None

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw skeletal joints on screen
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                # Extract landmark coordinates for fingertips and PIP joints
                landmarks = hand_landmarks.landmark

                index_open = landmarks[8].y < landmarks[6].y
                middle_open = landmarks[12].y < landmarks[10].y
                ring_open = landmarks[16].y < landmarks[14].y
                pinky_open = landmarks[20].y < landmarks[18].y

                # Extract Index Finger Tip position in pixel coordinates
                idx_x = int(landmarks[8].x * FRAME_WIDTH)
                idx_y = int(landmarks[8].y * FRAME_HEIGHT)
                pointing_coords = (idx_x, idx_y)

                # Classify Gesture
                if index_open and middle_open and ring_open and pinky_open:
                    gesture = "OPEN_PALM"
                elif not index_open and not middle_open and not ring_open and not pinky_open:
                    gesture = "FIST"
                elif index_open and not middle_open and not ring_open and not pinky_open:
                    gesture = "POINTING"

        return gesture, pointing_coords

    def close(self):
        self.hands.close()