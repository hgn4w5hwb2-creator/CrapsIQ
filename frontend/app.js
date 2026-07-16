// Configuration
const API_BASE = 'http://localhost:8000/api';
const UPDATE_INTERVAL = 100; // ms between vision frame analyses

// State
let gameState = null;
let screenStream = null;
let frameAnalysisInterval = null;
let probabilities = {};
let rollHistory = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    loadProbabilities();
});

function initializeApp() {
    console.log('🎲 CrapsIQ Dashboard initializing...');
    updateApiStatus();
    updateVisionStatus();
    
    // Lighting slider
    document.getElementById('cal-lighting').addEventListener('input', (e) => {
        document.getElementById('lighting-value').textContent = e.target.value;
    });
}

// ===== API Status =====
async function updateApiStatus() {
    try {
        const response = await fetch(`${API_BASE}/vision/test`);
        if (response.ok) {
            document.getElementById('api-status').classList.add('connected');
            console.log('✅ API connected');
        } else {
            document.getElementById('api-status').classList.add('error');
            console.error('❌ API error');
        }
    } catch (e) {
        document.getElementById('api-status').classList.add('error');
        console.error('❌ API connection failed:', e);
    }
}

function updateVisionStatus() {
    document.getElementById('vision-status').classList.add('connected');
}

// ===== Screen Share =====
async function startScreenShare() {
    try {
        screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: { cursor: 'always' },
            audio: false
        });

        const video = document.getElementById('screenVideo');
        video.srcObject = screenStream;

        document.getElementById('capture-status').innerHTML = '✅ Screen captured. Analyzing...';
        document.getElementById('capture-status').style.color = '#00ff88';

        startFrameAnalysis();

    } catch (e) {
        console.error('Screen share error:', e);
        document.getElementById('capture-status').innerHTML = '❌ Screen share cancelled';
        document.getElementById('capture-status').style.color = '#ff4444';
    }
}

function stopScreenShare() {
    if (screenStream) {
        screenStream.getTracks().forEach(track => track.stop());
        screenStream = null;
        stopFrameAnalysis();
        document.getElementById('capture-status').innerHTML = '⏹ Stopped';
        document.getElementById('screenVideo').srcObject = null;
    }
}

// ===== Frame Analysis =====
function startFrameAnalysis() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const video = document.getElementById('screenVideo');

    const analyzeFrame = async () => {
        try {
            if (!video.srcObject) {
                stopFrameAnalysis();
                return;
            }

            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            ctx.drawImage(video, 0, 0);

            canvas.toBlob(async (blob) => {
                const formData = new FormData();
                formData.append('file', blob, 'frame.jpg');

                try {
                    const response = await fetch(
                        `${API_BASE}/vision/frame`,
                        { method: 'POST', body: formData }
                    );

                    if (response.ok) {
                        const data = await response.json();
                        updateDashboard(data);
                    }
                } catch (e) {
                    console.error('Frame analysis error:', e);
                }
            }, 'image/jpeg', 0.7);

            frameAnalysisInterval = setTimeout(analyzeFrame, UPDATE_INTERVAL);
        } catch (e) {
            console.error('Frame processing error:', e);
        }
    };

    analyzeFrame();
}

function stopFrameAnalysis() {
    if (frameAnalysisInterval) {
        clearTimeout(frameAnalysisInterval);
        frameAnalysisInterval = null;
    }
}

// ===== Dashboard Updates =====
function updateDashboard(data) {
    // Update roll display
    if (data.total) {
        document.getElementById('roll-dice').textContent = 
            data.dice.map(d => d.value).join(' + ');
        document.getElementById('roll-total').textContent = data.total;
        document.getElementById('roll-confidence').textContent = 
            (data.confidence * 100).toFixed(0) + '%';

        // Update game state if available
        if (data.game_state) {
            gameState = data.game_state;
            updateGameState(data);
        }
    }
}

function updateGameState(data) {
    if (!gameState) return;

    // Update game phase and point
    const phase = gameState.phase === 'come_out' ? 'Come Out' : `Point (${gameState.point})`;
    document.getElementById('game-phase').textContent = phase;
    document.getElementById('game-point').textContent = gameState.point || '-';
    document.getElementById('game-rolls').textContent = gameState.roll_count;

    // Update game result
    if (data.game_result) {
        const result = data.game_result;
        document.getElementById('game-result').textContent = 
            result.charAt(0).toUpperCase() + result.slice(1).replace(/_/g, ' ');
        
        // Add to roll history
        addToRollHistory(gameState.roll_history[gameState.roll_history.length - 1], result);
    }

    // Update odds if point is set
    if (gameState.odds && gameState.point) {
        updateOdds(gameState.odds);
    }

    // Update AI recommendation
    if (data.ai_recommendation) {
        updateAICoach(data.ai_recommendation);
    }
}

function updateOdds(odds) {
    const container = document.getElementById('odds-container');
    container.innerHTML = `
        <div class="odds-item">
            <span class="label">Pass (For):</span>
            <span class="value">${odds.for}%</span>
        </div>
        <div class="odds-item">
            <span class="label">Don't Pass (Against):</span>
            <span class="value">${odds.against}%</span>
        </div>
    `;
}

function updateAICoach(recommendation) {
    const container = document.getElementById('ai-coach');
    let html = '';

    if (recommendation.phase) {
        html += `<div class="coach-message"><strong>Phase:</strong> ${recommendation.phase}</div>`;
    }
    if (recommendation.odds) {
        html += `<div class="coach-message"><strong>Odds:</strong> ${recommendation.odds}</div>`;
    }
    if (recommendation.bankroll) {
        html += `<div class="coach-message"><strong>Bankroll:</strong> ${recommendation.bankroll}</div>`;
    }
    if (recommendation.avoid) {
        html += `<div class="coach-message"><strong>⚠️ Avoid:</strong> ${recommendation.avoid}</div>`;
    }

    container.innerHTML = html;
}

function addToRollHistory(rollValue, result) {
    const container = document.getElementById('roll-history');
    const badge = document.createElement('span');
    badge.className = `roll-badge ${result}`;
    badge.textContent = rollValue;
    
    container.innerHTML = '';
    rollHistory.push({ value: rollValue, result });
    
    // Keep last 20 rolls
    if (rollHistory.length > 20) {
        rollHistory.shift();
    }

    rollHistory.forEach(roll => {
        const b = document.createElement('span');
        b.className = `roll-badge ${roll.result}`;
        b.textContent = roll.value;
        container.appendChild(b);
    });
}

// ===== Probabilities =====
async function loadProbabilities() {
    try {
        const response = await fetch(`${API_BASE}/probabilities`);
        if (response.ok) {
            probabilities = await response.json();
            displayProbabilities();
        }
    } catch (e) {
        console.error('Error loading probabilities:', e);
    }
}

function displayProbabilities() {
    const container = document.getElementById('probabilities-container');
    let html = '';

    for (let roll = 2; roll <= 12; roll++) {
        const prob = probabilities[roll] || 0;
        html += `
            <div class="prob-item">
                <div class="roll">${roll}</div>
                <div class="percent">${prob}%</div>
            </div>
        `;
    }

    container.innerHTML = html;
}

// ===== Calibration =====
async function calibrateTable() {
    const calibrationData = {
        table_id: 'default',
        x: parseInt(document.getElementById('cal-x').value),
        y: parseInt(document.getElementById('cal-y').value),
        width: parseInt(document.getElementById('cal-width').value),
        height: parseInt(document.getElementById('cal-height').value),
        camera_angle: parseFloat(document.getElementById('cal-angle').value),
        lighting_level: parseFloat(document.getElementById('cal-lighting').value)
    };

    try {
        const response = await fetch(`${API_BASE}/vision/calibrate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(calibrationData)
        });

        if (response.ok) {
            const result = await response.json();
            document.getElementById('calibration-status').innerHTML = 
                '✅ Calibration saved!';
            document.getElementById('calibration-status').style.color = '#00ff88';
            console.log('✅ Table calibrated:', result);
        } else {
            throw new Error('Calibration failed');
        }
    } catch (e) {
        document.getElementById('calibration-status').innerHTML = 
            '❌ Calibration error';
        document.getElementById('calibration-status').style.color = '#ff4444';
        console.error('Calibration error:', e);
    }
}
