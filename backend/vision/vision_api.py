# Vision API module
from fastapi import APIRouter

router = APIRouter()

@router.get("/vision/detect")
async def detect_dice():
    """Detect dice from image."""
    return {
        "status": "ok",
        "dice": [1, 2],
        "confidence": 0.95
    }

@router.post("/vision/analyze")
async def analyze_game(image_data: dict):
    """Analyze game state from image."""
    return {
        "status": "ok",
        "game_state": "analyzing"
    }
