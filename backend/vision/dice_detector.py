import cv2
import numpy as np


class DiceDetector:
    """Detects dice in images using contour detection."""

    def __init__(self):
        pass

    def detect(self, image):
        """Detect dice-like objects in image.
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            dict with detected dice count, bounding boxes, and confidence
        """
        # Convert to grayscale
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # Reduce noise
        blur = cv2.GaussianBlur(
            gray,
            (5, 5),
            0
        )

        # Detect bright dice areas
        _, thresh = cv2.threshold(
            blur,
            200,
            255,
            cv2.THRESH_BINARY
        )

        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        dice = []

        for c in contours:
            area = cv2.contourArea(c)

            if 500 < area < 50000:
                x, y, w, h = cv2.boundingRect(c)

                dice.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                })

        return {
            "dice_detected": len(dice),
            "objects": dice,
            "confidence": 0.80 if len(dice) == 2 else 0.30
        }
