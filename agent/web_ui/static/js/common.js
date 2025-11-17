/**
 * Form Discoverer Agent - Common JavaScript Utilities
 * Location: agent/web_ui/static/js/common.js
 */

// ========== API UTILITIES ==========

/**
 * Make a POST request to API
 */
async function apiPost(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return {
            success: false,
            message: `Network error: ${error.message}`
        };
    }
}

/**
 * Make a GET request to API
 */
async function apiGet(url) {
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return {
            success: false,
            message: `Network error: ${error.message}`
        };
    }
}

// ========== UI UTILITIES ==========

/**
 * Show a result message
 */
function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = message;
    element.className = `result-message visible ${type}`;
}

/**
 * Hide a result message
 */
function hideMessage(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.className = 'result-message';
}

/**
 * Show loading spinner on button
 */
function showLoading(buttonElement, originalText) {
    buttonElement.disabled = true;
    buttonElement.innerHTML = `
        <span class="spinner"></span>
        <span>${originalText || 'Loading...'}</span>
    `;
}

/**
 * Hide loading spinner on button
 */
function hideLoading(buttonElement, originalText) {
    buttonElement.disabled = false;
    buttonElement.textContent = originalText;
}

/**
 * Generate unique agent ID
 */
function generateAgentId() {
    return 'agent-' + Math.random().toString(36).substr(2, 9);
}

/**
 * Format date/time
 */
function formatDateTime(date) {
    return new Date(date).toLocaleString();
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate email
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate URL
 */
function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

// ========== LOCAL STORAGE ==========

/**
 * Save to local storage
 */
function saveToStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (error) {
        console.error('Storage Error:', error);
        return false;
    }
}

/**
 * Load from local storage
 */
function loadFromStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Storage Error:', error);
        return defaultValue;
    }
}

/**
 * Remove from local storage
 */
function removeFromStorage(key) {
    try {
        localStorage.removeItem(key);
        return true;
    } catch (error) {
        console.error('Storage Error:', error);
        return false;
    }
}

// ========== GLOBAL STATE ==========

// Store setup progress
window.setupState = loadFromStorage('setupState', {
    currentStep: 1,
    apiUrl: '',
    token: '',
    companyId: null,
    userId: null,
    agentId: '',
    browser: 'chrome',
    headless: false,
    screenshotFolder: '',
    logFolder: '',
    filesFolder: ''
});

/**
 * Save setup state
 */
function saveSetupState() {
    saveToStorage('setupState', window.setupState);
}

/**
 * Clear setup state
 */
function clearSetupState() {
    removeFromStorage('setupState');
    window.setupState = {
        currentStep: 1,
        apiUrl: '',
        token: '',
        companyId: null,
        userId: null,
        agentId: '',
        browser: 'chrome',
        headless: false,
        screenshotFolder: '',
        logFolder: '',
        filesFolder: ''
    };
}

// ========== AUTO-REFRESH STATUS ==========

/**
 * Check agent status periodically
 */
function startStatusMonitoring(callback, interval = 30000) {
    // Check immediately
    checkAgentStatus(callback);
    
    // Then check periodically
    return setInterval(() => {
        checkAgentStatus(callback);
    }, interval);
}

/**
 * Check agent status
 */
async function checkAgentStatus(callback) {
    const result = await apiGet('/api/status');
    if (callback) {
        callback(result);
    }
}

/**
 * Stop status monitoring
 */
function stopStatusMonitoring(intervalId) {
    if (intervalId) {
        clearInterval(intervalId);
    }
}

// ========== EVENT HANDLERS ==========

/**
 * Handle form submission
 */
function handleFormSubmit(formElement, handler) {
    formElement.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handler(new FormData(formElement));
    });
}

/**
 * Open folder in file explorer
 */
function openFolder(path) {
    // This would be handled by the system tray in production
    console.log('Open folder:', path);
    alert('Opening folder: ' + path);
}

// ========== INITIALIZATION ==========

// Set up global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

// Set up unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});

console.log('Common utilities loaded');
