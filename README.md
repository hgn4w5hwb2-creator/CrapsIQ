# CrapsIQ API

Minimal root-level FastAPI API for CrapsIQ.

## Files
- `app.py` - FastAPI application and endpoints
- `models.py` - SQLAlchemy models
- `database.py` - database configuration
- `craps_engine.py` - craps game logic
- `requirements.txt` - Python dependencies
- `Procfile` - Railway start command

## Local development
```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

## Endpoints
- `GET /api/health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /api/game/start`
- `POST /api/game/{session_id}/roll`
- `GET /api/game/{session_id}`
- `POST /api/game/{session_id}/end`
