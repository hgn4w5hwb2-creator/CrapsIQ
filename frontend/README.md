# CrapsIQ Frontend

## Files

- **index.html** - Main dashboard HTML
- **styles.css** - Styling (dark theme with gold accents)
- **app.js** - Frontend JavaScript logic

## Features

✅ **Live Screen Capture** - Browser-based screen sharing
✅ **Table Calibration** - Set up dice detection region
✅ **Real-time Roll Detection** - Vision-based dice analysis
✅ **Game State Tracking** - Current point, rolls, phase
✅ **Roll History** - Last 20 rolls with color coding
✅ **Odds Display** - Pass/Don't Pass probabilities
✅ **AI Coach** - Real-time strategy recommendations
✅ **Roll Probabilities** - All possible outcomes (2-12)

## Running

1. Start the backend:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. Open the frontend:
   ```bash
   # Option 1: Open file directly
   open frontend/index.html

   # Option 2: Use a local server
   cd frontend
   python -m http.server 8080
   # Then visit http://localhost:8080
   ```

## API Integration

The frontend communicates with the backend API:

- `POST /api/vision/frame` - Send captured frames for analysis
- `POST /api/vision/calibrate` - Set table calibration
- `GET /api/probabilities` - Get roll probabilities

## Usage

1. **Calibrate Table** (First time):
   - Adjust dice region coordinates (x, y, width, height)
   - Set camera angle and lighting level
   - Click "Save Calibration"

2. **Start Analysis**:
   - Click "Start Screen Share"
   - Select the craps table screen
   - Dashboard will auto-update with each roll

3. **Monitor**:
   - Watch current roll and confidence
   - Track game state (phase, point, rolls)
   - Review roll history and AI recommendations

## Troubleshooting

**API Connection Failed**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/main.py`

**Screen Share Not Working**
- Requires HTTPS or localhost
- Some browsers may require specific permissions

**No Dice Detected**
- Adjust calibration region
- Check lighting conditions
- Verify dice are visible and white
