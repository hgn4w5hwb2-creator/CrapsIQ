from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GameSession(Base):
    __tablename__ = "game_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String, unique=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    total_rolls = Column(Integer, default=0)

class Roll(Base):
    __tablename__ = "rolls"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    roll_number = Column(Integer)
    dice_values = Column(JSON)
    total = Column(Integer)
    game_result = Column(String)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class GameState(Base):
    __tablename__ = "game_states"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    phase = Column(String)
    current_point = Column(Integer, nullable=True)
    roll_history = Column(JSON)
    odds = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
