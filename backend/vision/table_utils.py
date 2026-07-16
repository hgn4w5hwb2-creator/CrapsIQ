import cv2
import numpy as np
from .calibration import get_calibration


def crop_table(image, table_id: str = "default"):
    """Crop to dice detection region based on calibration.
    
    Args:
        image: OpenCV image (BGR format)
        table_id: Table identifier for calibration lookup
        
    Returns:
        Cropped image or original if no calibration
    """
    calibration = get_calibration(table_id)

    if not calibration:
        return image

    r = calibration.dice_region

    return image[
        r.y:r.y+r.height,
        r.x:r.x+r.width
    ]


def apply_lighting_correction(image, calibration):
    """Adjust image based on calibrated lighting level.
    
    Args:
        image: OpenCV image
        calibration: TableCalibration object
        
    Returns:
        Brightness-adjusted image
    """
    # Normalize lighting (0.5 is neutral)
    lighting_factor = calibration.lighting_level * 2
    
    adjusted = cv2.convertScaleAbs(
        image,
        alpha=lighting_factor,
        beta=0
    )
    
    return adjusted


def detect_dice_in_region(
    image,
    calibration
) -> dict:
    """Detect dice in the calibrated region.
    
    Args:
        image: Full table image
        calibration: TableCalibration object
        
    Returns:
        dict with detection results
    """
    # Crop to region
    cropped = crop_table(image)
    
    # Apply lighting correction
    corrected = apply_lighting_correction(
        cropped,
        calibration
    )
    
    return {
        "original": image,
        "cropped": cropped,
        "corrected": corrected,
        "calibration": {
            "camera_angle": calibration.camera_angle,
            "lighting_level": calibration.lighting_level
        }
    }
