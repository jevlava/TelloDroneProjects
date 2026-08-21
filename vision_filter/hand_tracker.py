from cvzone.HandTrackingModule import HandDetector


class GestureEngine:
    def __init__(self, confidence=0.7):
        self.detector = HandDetector(detectionCon=confidence, maxHands=1)

    def analyze(self, img):
        hands, _ = self.detector.findHands(img, draw=False)
        if not hands:
            return None, "NO_HAND"

        hand = hands[0]
        fingers = self.detector.fingersUp(hand)

        # Gesture Mapping
        if fingers == [0, 1, 0, 0, 0]:
            gesture = "POINT"
        elif fingers == [0, 1, 1, 0, 0]:
            gesture = "PEACE"
        elif fingers == [1, 1, 1, 1, 1]:
            gesture = "PALM"
        else:
            gesture = "UNKNOWN"

        return hand, gesture