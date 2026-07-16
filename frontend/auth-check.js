// Check authentication on page load
window.addEventListener('load', () => {
    checkAuthentication();
});

// Check if user is authenticated
function checkAuthentication() {
    const token = localStorage.getItem('crapsiq-token');
    const user = JSON.parse(localStorage.getItem('crapsiq-user') || '{}');
    
    if (!token) {
        // Redirect to login
        window.location.href = 'login.html';
        return;
    }
    
    // Update UI with user info
    updateUserUI(user);
}

// Update UI with user info
function updateUserUI(user) {
    const userElement = document.getElementById('current-user');
    if (userElement) {
        userElement.textContent = user.username || 'User';
    }
}

// Logout function
function logout() {
    localStorage.removeItem('crapsiq-token');
    localStorage.removeItem('crapsiq-user');
    window.location.href = 'login.html';
}

// Get auth headers for API calls
function getAuthHeaders() {
    const token = localStorage.getItem('crapsiq-token');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}
