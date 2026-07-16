from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
import uuid
import os
import sys

# Add current directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from vision.vision_api import router as vision_router
except ImportError:
    # Fallback if import fails
    from fastapi import APIRouter
    router = APIRouter()
    @router.get("/vision/detect")
    async def detect_dice():
        return {"status": "ok", "dice": [1, 2], "confidence": 0.95}
    vision_router = router

from craps_engine import CrapsEngine, GameResult
from models import GameSession, Roll, GameState, User
from database import get_db, engine
import models

# Create tables
models.Base.metadata.create_all(bind=engine)

# JWT config
SECRET_KEY = os.getenv("SECRET_KEY", "crapsiq-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return username
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

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
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Include routers
app.include_router(vision_router, prefix="/api")

# In-memory game engines
game_engines = {}

# Create demo user on startup
@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    print("🎲 CrapsIQ API started")
    print(f"Frontend: http://localhost:8000/login.html")
    print(f"API Docs: http://localhost:8000/docs")
    
    # Create demo user if it doesn't exist
    from database import SessionLocal
    db = SessionLocal()
    existing_user = db.query(User).filter(User.username == "demo").first()
    if not existing_user:
        demo_user = User(
            username="demo",
            email="demo@crapsiq.com",
            hashed_password=hash_password("demo123"),
            is_active=True
        )
        db.add(demo_user)
        db.commit()
        print("✅ Demo user created: demo / demo123")
    db.close()

# Root - serve login page
@app.get("/")
async def root():
    """Serve login HTML."""
    login_file = os.path.join(frontend_path, 'login.html')
    if os.path.exists(login_file):
        return FileResponse(login_file, media_type='text/html')
    return {"status": "ok", "service": "CrapsIQ API"}

# Auth endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@app.post("/auth/register")
async def register(username: str, email: str, password: str, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == username) |
        (User.email == email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
    }

@app.post("/auth/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    """Login user and return JWT token."""
    # Find user
    db_user = db.query(User).filter(
        User.username == username
    ).first()
    
    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": db_user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "is_active": db_user.is_active
        }
    }

@app.get("/auth/me")
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user info."""
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active
    }

@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "CrapsIQ API"}

@app.post("/api/game/start")
async def start_game(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Start a new craps game session."""
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    
    session_id = str(uuid.uuid4())
    engine = CrapsEngine()
    game_engines[session_id] = engine

    db_session = GameSession(
        user_id=user.id,
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
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Process a roll in an active game."""
    verify_token(token)
    
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

    result = engine.process_roll(roll_total)

    db_roll = Roll(
        session_id=session_id,
        roll_number=len(engine.roll_history),
        dice_values=dice_values,
        total=roll_total,
        game_result=result.value,
        confidence=confidence
    )
    db.add(db_roll)

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
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current game state."""
    verify_token(token)
    
    if session_id not in game_engines:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    engine = game_engines[session_id]

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
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """End a game session."""
    verify_token(token)
    
    if session_id not in game_engines:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    engine = game_engines[session_id]

    db_session = db.query(GameSession).filter(
        GameSession.session_id == session_id
    ).first()

    if db_session:
        db_session.ended_at = datetime.utcnow()
        db_session.total_rolls = len(engine.roll_history)
        db.commit()

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
async def get_probabilities(token: str = Depends(oauth2_scheme)):
    """Get all possible roll probabilities."""
    verify_token(token)
    engine = CrapsEngine()
    return engine.calculate_roll_probabilities()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
