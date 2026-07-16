from fastapi import APIRouter, UploadFile, HTTPException
import numpy as np
import cv2

from .dice_detector import DiceDetector
from .pip_reader import PipReader
from .calibration import get_calibration, DiceRegion, set_calibration
from .table_utils import crop_table, apply_lighting_correction
from ..craps_engine import CrapsEngine


router = APIRouter()

detector = DiceDetector()
reader = PipReader()
game = CrapsEngine()


@router.post("/vision/calibrate")
async def calibrate_table(data: dict):
    """Calibrate dice detection region for a table.
    
    Args:
        data: {
            "table_id": "default",
            "x": 100,
            "y": 50,
            "width": 400,
            "height": 300,
            "camera_angle": 0,
            "lighting_level": 0.5
        }
        
    Returns:
        Confirmation of calibration
    """
    try:
        table_id = data.get("table_id", "default")
        dice_region = DiceRegion(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"]
        )

        set_calibration(
            dice_region=dice_region,
            table_id=table_id,
            camera_angle=data.get("camera_angle", 0),
            lighting_level=data.get("lighting_level", 0.5)
        )

        return {
            "status": "calibrated",
            "table_id": table_id,
            "dice_region": {
                "x": dice_region.x,
                "y": dice_region.y,
                "width": dice_region.width,
                "height": dice_region.height
            }
        }

    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required field: {str(e)}"
        )


@router.post("/vision/frame")
async def analyze_frame(file: UploadFile, table_id: str = "default"):
    """Analyze a single frame from the craps table.
    
    Args:
        file: Image file upload
        table_id: Table identifier for calibration lookup
        
    Returns:
        dict with detected dice, pips, confidence, and game state
    """
    try:
        data = await file.read()

        image = np.frombuffer(
            data,
            np.uint8
        )

        image = cv2.imdecode(
            image,
            cv2.IMREAD_COLOR
        )

        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid image format"
            )

        # Get calibration
        calibration = get_calibration(table_id)

        # Crop to calibrated region
        cropped = crop_table(image, table_id)

        # Apply lighting correction if calibrated
        if calibration:
            cropped = apply_lighting_correction(
                cropped,
                calibration
            )

        # Detect dice locations
        detection_result = detector.detect(cropped)

        # Extract pips from each detected die
        dice_values = []

        for die in detection_result["objects"]:
            x = die["x"]
            y = die["y"]
            w = die["width"]
            h = die["height"]

            die_crop = cropped[
                y:y+h,
                x:x+w
            ]

            pips = reader.count_pips(die_crop)

            if pips:
                dice_values.append({"value": pips})

        roll_total = sum(
            d["value"] for d in dice_values
        ) if dice_values else None

        # Process roll if high confidence
        game_result = None
        game_state = None

        if (
            detection_result["confidence"] > 0.90
            and roll_total
        ):
            game_result = game.process_roll(roll_total)
            game_state = game.get_game_state()

        return {
            "dice_detected": detection_result["dice_detected"],
            "dice": dice_values,
            "total": roll_total,
            "confidence": detection_result["confidence"],
            "objects": detection_result["objects"],
            "game_result": game_result.value if game_result else None,
            "game_state": game_state,
            "ai_recommendation": (
                game.get_ai_recommendation()
                if game_state else None
            ),
            "calibrated": calibration is not None
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vision processing error: {str(e)}"
        )


@router.post("/vision/test")
async def test_vision():
    """Test endpoint to verify vision service is running."""
    return {
        "status": "ok",
        "detector": "ready",
        "reader": "ready",
        "game_engine": "ready",
        "calibration": "ready"
    }
