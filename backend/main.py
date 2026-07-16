from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
import os

from .vision.vision_api import router as vision_router
from .craps_engine import CrapsEngine, GameResult
from .models import GameSession, Roll, GameState
from .database import get_db, engine
from . import models

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CrapsIQ API",
    description="Live dealer craps analyzer with vision AI",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from frontend directory
frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Include routers
app.include_router(vision_router, prefix="/api")

# In-memory game engines (in production, use Redis or database)
game_engines = {}


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    print("🎲 CrapsIQ API started")
    print(f"Frontend: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs")


@app.get("/")
async def root():
    """Serve frontend HTML."""
    frontend_file = os.path.join(frontend_path, 'index.html')
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file, media_type='text/html')
    return {"status": "ok", "service": "CrapsIQ API", "message": "Visit /docs for API documentation"}


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "CrapsIQ API"}


@app.post("/api/game/start")
async def start_game(db: Session = Depends(get_db)):
    """Start a new craps game session.
    
    Returns:
        dict with session_id and initial game state
    """
    session_id = str(uuid.uuid4())
    engine = CrapsEngine()
    game_engines[session_id] = engine

    # Save to database
    db_session = GameSession(
        session_id=session_id,
        started_at=datetime.utcnow()
    )
    db.add(db_session)
    db.commit()

    return {
        "session_id": session_id,
        "game_state": engine.get_game_state(),
        "probabilities": engine.calculate_roll_probabilities()
    }


@app.post("/api/game/{session_id}/roll")
async def process_roll(
    session_id: str,
    dice_values: list,
    confidence: float,
    db: Session = Depends(get_db)
):
    """Process a roll in an active game.
    
    Args:
        session_id: Game session ID
        dice_values: [die1, die2]
        confidence: Detection confidence (0-1)
        
    Returns:
        dict with game result, updated state, and recommendations
    """
    if session_id not in game_engines:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    if len(dice_values) != 2:
        raise HTTPException(
            status_code=400,
            detail="Must provide exactly 2 dice values"
        )

    engine = game_engines[session_id]
    roll_total = sum(dice_values)

    # Process roll
    result = engine.process_roll(roll_total)

    # Save roll to database
    db_roll = Roll(
        session_id=session_id,
        roll_number=len(engine.roll_history),
        dice_values=dice_values,
        total=roll_total,
        game_result=result.value,
        confidence=confidence
    )
    db.add(db_roll)

    # Save game state
    db_state = GameState(
        session_id=session_id,
        phase=engine.phase.value,
        current_point=engine.point,
        roll_history=engine.roll_history,
        odds=engine.calculate_odds_for_point() if engine.point else None
    )
    db.add(db_state)
    db.commit()

    return {
        "roll": {
            "dice": dice_values,
            "total": roll_total,
            "confidence": confidence
        },
        "result": result.value,
        "game_state": engine.get_game_state(),
        "ai_recommendation": engine.get_ai_recommendation(),
        "next_probabilities": engine.calculate_roll_probabilities()
    }


@app.get("/api/game/{session_id}")
async def get_game(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get current game state.
    
    Args:
        session_id: Game session ID
        
    Returns:
        dict with complete game state and history
    """
    if session_id not in game_engines:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    engine = game_engines[session_id]

    # Get rolls from database
    rolls = db.query(Roll).filter(
        Roll.session_id == session_id
    ).all()

    return {
        "session_id": session_id,
        "game_state": engine.get_game_state(),
        "total_rolls": len(rolls),
        "rolls": [
            {
                "number": r.roll_number,
                "dice": r.dice_values,
                "total": r.total,
                "result": r.game_result,
                "confidence": r.confidence
            }
            for r in rolls
        ],
        "ai_recommendation": engine.get_ai_recommendation()
    }


@app.post("/api/game/{session_id}/end")
async def end_game(
    session_id: str,
    db: Session = Depends(get_db)
):
    """End a game session.
    
    Args:
        session_id: Game session ID
        
    Returns:
        dict with final statistics
    """
    if session_id not in game_engines:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    engine = game_engines[session_id]

    # Update database
    db_session = db.query(GameSession).filter(
        GameSession.session_id == session_id
    ).first()

    if db_session:
        db_session.ended_at = datetime.utcnow()
        db_session.total_rolls = len(engine.roll_history)
        db.commit()

    # Clean up in-memory engine
    del game_engines[session_id]

    return {
        "session_id": session_id,
        "total_rolls": len(engine.roll_history),
        "roll_history": engine.roll_history,
        "game_duration_seconds": (
            datetime.utcnow() - db_session.started_at
        ).total_seconds() if db_session else 0
    }


@app.get("/api/probabilities")
async def get_probabilities():
    """Get all possible roll probabilities.
    
    Returns:
        dict with probabilities for each roll (2-12)
    """
    engine = CrapsEngine()
    return engine.calculate_roll_probabilities()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
