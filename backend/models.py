from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime


Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GameSession(Base):
    """Stores craps game sessions."""
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    session_id = Column(String, unique=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    total_rolls = Column(Integer, default=0)
    final_result = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)


class Roll(Base):
    """Stores individual rolls within a session."""
    __tablename__ = "rolls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    roll_number = Column(Integer)
    dice_values = Column(JSON)  # [die1, die2]
    total = Column(Integer)
    game_result = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float)


class GameState(Base):
    """Stores snapshots of game state."""
    __tablename__ = "game_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    phase = Column(String)  # come_out or point
    current_point = Column(Integer, nullable=True)
    roll_history = Column(JSON)
    odds = Column(JSON, nullable=True)
