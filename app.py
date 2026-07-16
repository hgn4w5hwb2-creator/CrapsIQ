import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from craps_engine import CrapsEngine
from database import Base, SQLITE, engine, get_db
from models import GameSession, User

configured_secret_key = os.getenv("SECRET_KEY")
if configured_secret_key:
    SECRET_KEY = configured_secret_key
elif SQLITE:
    SECRET_KEY = secrets.token_urlsafe(32)
else:
    raise RuntimeError("SECRET_KEY must be set when using a non-SQLite database")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_scheme = HTTPBearer()
logger = logging.getLogger("crapsiq")

app = FastAPI(title="CrapsIQ API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(
        min_length=8,
        max_length=72,
        description="User password; string length is capped at 72 characters and validation also enforces bcrypt's 72 UTF-8 byte limit",
    )

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 UTF-8 bytes or fewer")
        return value


class LoginRequest(BaseModel):
    username: str
    password: str


class RollRequest(BaseModel):
    die1: int = Field(ge=1, le=6)
    die2: int = Field(ge=1, le=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool


class GameStateResponse(BaseModel):
    session_id: str
    status: str
    phase: str
    point: int | None
    roll_count: int
    roll_history: list[dict]
    started_at: datetime
    ended_at: datetime | None


class RollResponse(BaseModel):
    session_id: str
    result: str
    status: str
    phase: str
    point: int | None
    roll_count: int
    roll_history: list[dict]


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    if not os.getenv("SECRET_KEY"):
        logger.warning("SECRET_KEY is not set; using an ephemeral development key")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "CrapsIQ API"}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(username: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError as exc:
        raise unauthorized from exc
    if not username:
        raise unauthorized

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise unauthorized
    return user


def serialize_session(game_session: GameSession) -> GameStateResponse:
    return GameStateResponse(
        session_id=game_session.session_id,
        status=game_session.status,
        phase=game_session.phase,
        point=game_session.point,
        roll_count=game_session.roll_count,
        roll_history=game_session.roll_history or [],
        started_at=game_session.started_at,
        ended_at=game_session.ended_at,
    )


def get_owned_session(db: Session, session_id: str, user: User) -> GameSession:
    game_session = (
        db.query(GameSession)
        .filter(GameSession.session_id == session_id, GameSession.user_id == user.id)
        .first()
    )
    if not game_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game session not found")
    return game_session


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing_user = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if existing_user and existing_user.username == payload.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if existing_user and existing_user.email == payload.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.username))


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.post("/api/game/start", response_model=GameStateResponse, status_code=status.HTTP_201_CREATED)
def start_game(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GameStateResponse:
    game_session = GameSession(
        session_id=str(uuid4()),
        user_id=current_user.id,
        status="active",
        phase="come_out",
        point=None,
        roll_count=0,
        roll_history=[],
    )
    db.add(game_session)
    db.commit()
    db.refresh(game_session)
    return serialize_session(game_session)


@app.post("/api/game/{session_id}/roll", response_model=RollResponse)
def roll_game(
    session_id: str,
    payload: RollRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RollResponse:
    game_session = get_owned_session(db, session_id, current_user)
    if game_session.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game session has ended")

    engine = CrapsEngine(
        phase=game_session.phase,
        point=game_session.point,
        roll_history=game_session.roll_history or [],
    )
    result = engine.process_roll(payload.die1, payload.die2)

    game_session.phase = result["phase"]
    game_session.point = result["point"]
    game_session.roll_count = result["roll_count"]
    game_session.roll_history = result["roll_history"]
    db.commit()

    return RollResponse(
        session_id=game_session.session_id,
        result=result["result"],
        status=game_session.status,
        phase=game_session.phase,
        point=game_session.point,
        roll_count=game_session.roll_count,
        roll_history=game_session.roll_history,
    )


@app.get("/api/game/{session_id}", response_model=GameStateResponse)
def get_game(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameStateResponse:
    return serialize_session(get_owned_session(db, session_id, current_user))


@app.post("/api/game/{session_id}/end", response_model=GameStateResponse)
def end_game(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameStateResponse:
    game_session = get_owned_session(db, session_id, current_user)
    if game_session.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game session has ended")

    game_session.status = "ended"
    game_session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(game_session)
    return serialize_session(game_session)
