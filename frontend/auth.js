// API Configuration
const API_BASE = 'http://localhost:8000/api';
const AUTH_API = 'http://localhost:8000/auth';
const STORAGE_KEY = 'crapsiq-token';
const USER_KEY = 'crapsiq-user';

// Switch between login and register
function switchToLogin(e) {
    e.preventDefault();
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('loginForm').style.display = 'block';
}

function switchToRegister(e) {
    e.preventDefault();
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
}

// Register
async function handleRegister(e) {
    e.preventDefault();
    
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;
    const errorDiv = document.getElementById('registerError');
    
    // Validate
    if (password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        return;
    }
    
    if (password.length < 6) {
        errorDiv.textContent = 'Password must be at least 6 characters';
        return;
    }
    
    try {
        const response = await fetch(`${AUTH_API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Registration failed');
        }
        
        errorDiv.textContent = '';
        alert('✅ Account created! Please log in.');
        switchToLogin({ preventDefault: () => {} });
        
    } catch (error) {
        errorDiv.textContent = '❌ ' + error.message;
    }
}

// Login
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${AUTH_API}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Login failed');
        }
        
        const data = await response.json();
        
        // Save token and user
        localStorage.setItem(STORAGE_KEY, data.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
        
        errorDiv.textContent = '';
        
        // Redirect to dashboard
        window.location.href = 'index.html';
        
    } catch (error) {
        errorDiv.textContent = '❌ ' + error.message;
    }
}

// Demo Login
async function demoLogin() {
    document.getElementById('loginUsername').value = 'demo';
    document.getElementById('loginPassword').value = 'demo123';
    
    // Simulate form submission
    const form = document.querySelector('#loginForm form');
    form.dispatchEvent(new Event('submit'));
}

// Check if already logged in
window.addEventListener('load', () => {
    const token = localStorage.getItem(STORAGE_KEY);
    if (token) {
        window.location.href = 'index.html';
    }
});
