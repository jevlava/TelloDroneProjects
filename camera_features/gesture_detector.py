import math

def is_peace_sign(hand_landmarks):
    landmarks = hand_landmarks.landmark
    index_ext = landmarks[8].y < landmarks[6].y
    middle_ext = landmarks[12].y < landmarks[10].y
    ring_curled = landmarks[16].y > landmarks[14].y
    pinky_curled = landmarks[20].y > landmarks[17].y
    thumb_close = abs(landmarks[4].x - landmarks[13].x) < 0.12
    return index_ext and middle_ext and ring_curled and pinky_curled and thumb_close


def is_thumbs_up(hand_landmarks):
    lm = hand_landmarks.landmark
    thumb_extended = lm[4].y < lm[3].y < lm[2].y
    index_curled = lm[8].y > lm[6].y
    middle_curled = lm[12].y > lm[10].y
    ring_curled = lm[16].y > lm[14].y
    pinky_curled = lm[20].y > lm[18].y
    return thumb_extended and index_curled and middle_curled and ring_curled and pinky_curled


def is_shaka_sign(hand_landmarks):
    lm = hand_landmarks.landmark
    palm_size = math.hypot(lm[9].x - lm[0].x, lm[9].y - lm[0].y)
    if palm_size == 0:
        return False

    def dist(p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    thumb_ext = dist(lm[4], lm[0]) / palm_size > 1.15
    pinky_ext = dist(lm[20], lm[0]) / palm_size > 1.05

    index_curled = dist(lm[8], lm[0]) < dist(lm[6], lm[0])
    middle_curled = dist(lm[12], lm[0]) < dist(lm[10], lm[0])
    ring_curled = dist(lm[16], lm[0]) < dist(lm[14], lm[0])

    index_not_extended = dist(lm[8], lm[5]) / palm_size < 0.68
    shaka_spread = dist(lm[4], lm[20]) / palm_size > 1.35

    return thumb_ext and pinky_ext and index_curled and middle_curled and ring_curled and index_not_extended and shaka_spread


def is_okay_sign(hand_landmarks):
    lm = hand_landmarks.landmark
    hand_size = math.hypot(lm[9].x - lm[0].x, lm[9].y - lm[0].y)
    if hand_size == 0:
        return False

    pinch_dist = math.hypot(lm[8].x - lm[4].x, lm[8].y - lm[4].y) / hand_size
    is_pinched = pinch_dist < 0.25

    index_pip_thumb_mcp_dist = math.hypot(lm[6].x - lm[2].x, lm[6].y - lm[2].y) / hand_size
    has_loop_shape = index_pip_thumb_mcp_dist > 0.30

    middle_ext = math.hypot(lm[12].x - lm[0].x, lm[12].y - lm[0].y) > math.hypot(lm[10].x - lm[0].x, lm[10].y - lm[0].y)
    ring_ext = math.hypot(lm[16].x - lm[0].x, lm[16].y - lm[0].y) > math.hypot(lm[14].x - lm[0].x, lm[14].y - lm[0].y)
    pinky_ext = math.hypot(lm[20].x - lm[0].x, lm[20].y - lm[0].y) > math.hypot(lm[18].x - lm[0].x, lm[18].y - lm[0].y)

    fingers_separated = math.hypot(lm[12].x - lm[8].x, lm[12].y - lm[8].y) / hand_size > 0.20
    return is_pinched and has_loop_shape and middle_ext and ring_ext and pinky_ext and fingers_separated