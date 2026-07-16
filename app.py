import os
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from craps_engine import CrapsEngine, GamePhase
from database import engine, get_db
from models import Base, GameSession, User

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class RollRequest(BaseModel):
    dice_values: list[int] = Field(min_length=2, max_length=2)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(username: str) -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as error:
        raise credentials_error from error

    username = payload.get("sub")
    if not username:
        raise credentials_error

    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if user is None:
        raise credentials_error
    return user


def get_session_for_user(db: Session, session_id: str, user_id: int) -> GameSession:
    game_session = db.query(GameSession).filter(
        GameSession.session_id == session_id,
        GameSession.user_id == user_id,
    ).first()
    if game_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game session not found")
    return game_session


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


def serialize_session(game_session: GameSession) -> dict:
    return {
        "session_id": game_session.session_id,
        "phase": game_session.phase,
        "point": game_session.point,
        "roll_history": game_session.roll_history or [],
        "total_rolls": game_session.total_rolls,
        "last_result": game_session.last_result,
        "is_active": game_session.is_active,
        "started_at": game_session.started_at.isoformat(),
        "ended_at": game_session.ended_at.isoformat() if game_session.ended_at else None,
    }


app = FastAPI(
    title="CrapsIQ API",
    description="Minimal CrapsIQ API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CrapsIQ API"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": serialize_user(user)}


@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
        "user": serialize_user(user),
    }


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user": serialize_user(current_user)}


@app.post("/api/game/start", status_code=status.HTTP_201_CREATED)
def start_game(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine_state = CrapsEngine().get_game_state()
    session = GameSession(
        session_id=str(uuid4()),
        user_id=current_user.id,
        phase=engine_state["phase"],
        point=engine_state["point"],
        roll_history=engine_state["roll_history"],
        total_rolls=engine_state["total_rolls"],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"game": serialize_session(session)}


@app.post("/api/game/{session_id}/roll")
def roll_game(
    session_id: str,
    payload: RollRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game_session = get_session_for_user(db, session_id, current_user.id)
    if not game_session.is_active or game_session.phase == GamePhase.ENDED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game session has already ended")

    engine_instance = CrapsEngine(
        phase=GamePhase(game_session.phase),
        point=game_session.point,
        roll_history=game_session.roll_history or [],
    )

    try:
        total, result = engine_instance.process_roll(payload.dice_values)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    state = engine_instance.get_game_state()
    game_session.phase = state["phase"]
    game_session.point = state["point"]
    game_session.roll_history = state["roll_history"]
    game_session.total_rolls = state["total_rolls"]
    game_session.last_result = result.value
    db.commit()
    db.refresh(game_session)

    return {
        "roll": {"dice_values": payload.dice_values, "total": total},
        "result": result.value,
        "game": serialize_session(game_session),
    }


@app.get("/api/game/{session_id}")
def get_game(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game_session = get_session_for_user(db, session_id, current_user.id)
    return {"game": serialize_session(game_session)}


@app.post("/api/game/{session_id}/end")
def end_game(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game_session = get_session_for_user(db, session_id, current_user.id)
    if not game_session.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game session has already ended")

    engine_instance = CrapsEngine(
        phase=GamePhase(game_session.phase),
        point=game_session.point,
        roll_history=game_session.roll_history or [],
    )
    final_state = engine_instance.end_game()

    game_session.phase = final_state["phase"]
    game_session.point = final_state["point"]
    game_session.roll_history = final_state["roll_history"]
    game_session.total_rolls = final_state["total_rolls"]
    game_session.is_active = False
    game_session.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(game_session)

    return {"game": serialize_session(game_session)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
