import cv2
import numpy as np


class PipReader:
    """Counts pips (dots) on individual dice."""

    def count_pips(self, die_image):
        """Count the number of pips on a single die.
        
        Args:
            die_image: Cropped image of single die (BGR format)
            
        Returns:
            int: Number of pips (1-6) or None if detection failed
        """
        gray = cv2.cvtColor(
            die_image,
            cv2.COLOR_BGR2GRAY
        )

        blur = cv2.GaussianBlur(
            gray,
            (3, 3),
            0
        )

        # Detect dark dots on white dice
        _, thresh = cv2.threshold(
            blur,
            80,
            255,
            cv2.THRESH_BINARY_INV
        )

        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        pips = 0

        for c in contours:
            area = cv2.contourArea(c)

            if 20 < area < 500:
                pips += 1

        # Craps dice only have 1-6
        if 1 <= pips <= 6:
            return pips

        return None
