/**
 * Form Discoverer Agent - Settings Panel JavaScript
 * Location: agent/web_ui/static/js/settings.js
 */

// Current active tab
let activeTab = 'connection';

// ========== TAB MANAGEMENT ==========

/**
 * Switch to a different tab
 */
function switchTab(tabName) {
    // Update active tab
    activeTab = tabName;
    
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `tab-${tabName}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
}

// ========== SETTINGS MANAGEMENT ==========

/**
 * Test API connection
 */
async function testApiConnection() {
    const apiUrl = document.getElementById('setting-api-url').value.trim();
    
    if (!apiUrl) {
        showMessage('connection-test-result', 'Please enter API URL', 'error');
        return;
    }
    
    const testButton = document.querySelector('button[onclick="testApiConnection()"]');
    const originalText = testButton.textContent;
    
    showLoading(testButton, 'Testing...');
    hideMessage('connection-test-result');
    
    const result = await apiPost('/api/setup/test-connection', { url: apiUrl });
    
    hideLoading(testButton, originalText);
    
    if (result.success) {
        showMessage('connection-test-result', 'Connection successful!', 'success');
    } else {
        showMessage('connection-test-result', result.message || 'Connection failed', 'error');
    }
}

/**
 * Browse for folder (opens file dialog via backend)
 */
function browseFolder(inputId) {
    // In production, this would trigger a native file dialog
    // For now, just focus the input
    const input = document.getElementById(inputId);
    if (input) {
        input.focus();
    }
    
    // In actual implementation, this would be:
    // window.electron.selectFolder().then(path => {
    //     input.value = path;
    // });
}

/**
 * Save all settings
 */
async function saveSettings() {
    const settings = {
        api_url: document.getElementById('setting-api-url').value.trim(),
        browser: document.getElementById('setting-browser').value,
        headless: document.getElementById('setting-headless').checked,
        screenshot_folder: document.getElementById('setting-screenshot-folder').value.trim(),
        log_folder: document.getElementById('setting-log-folder').value.trim(),
        files_folder: document.getElementById('setting-files-folder').value.trim(),
        auto_start: document.getElementById('setting-auto-start').checked,
        log_level: document.getElementById('setting-log-level').value,
        max_concurrent_tests: parseInt(document.getElementById('setting-max-concurrent').value) || 3,
        polling_interval: parseInt(document.getElementById('setting-polling-interval').value) || 2,
        capture_traffic: document.getElementById('setting-capture-traffic').checked
    };
    
    // Validate
    if (!settings.api_url || !settings.screenshot_folder || !settings.log_folder || !settings.files_folder) {
        showMessage('settings-save-result', 'Please fill in all required fields', 'error');
        return;
    }
    
    const saveButton = document.querySelector('button[onclick="saveSettings()"]');
    const originalText = saveButton.textContent;
    
    showLoading(saveButton, 'Saving...');
    hideMessage('settings-save-result');
    
    const result = await apiPost('/api/settings/save', settings);
    
    hideLoading(saveButton, originalText);
    
    if (result.success) {
        showMessage('settings-save-result', result.message || 'Settings saved! Restart agent for changes to take effect.', 'success');
    } else {
        showMessage('settings-save-result', result.message || 'Failed to save settings', 'error');
    }
}

/**
 * Reset settings to defaults
 */
function resetSettings() {
    if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
        return;
    }
    
    // Reload page to get original values from server
    window.location.reload();
}

/**
 * Open folder in file explorer
 */
function openFolderExternal(folderId) {
    const folderPath = document.getElementById(folderId).value;
    if (folderPath) {
        // This would be handled by the system tray app in production
        console.log('Opening folder:', folderPath);
        alert('Opening folder: ' + folderPath);
    }
}

// ========== AUTO-START MANAGEMENT ==========

/**
 * Toggle auto-start
 */
function toggleAutoStart() {
    const autoStart = document.getElementById('setting-auto-start').checked;
    
    // Show info message
    if (autoStart) {
        showMessage('auto-start-info', 
            'Agent will start automatically when you log in to your computer', 
            'info');
    } else {
        hideMessage('auto-start-info');
    }
}

// ========== TRAFFIC CAPTURE ==========

/**
 * Toggle traffic capture
 */
function toggleTrafficCapture() {
    const captureTraffic = document.getElementById('setting-capture-traffic').checked;
    
    // Show info message
    if (captureTraffic) {
        showMessage('traffic-info',
            'Browser network traffic will be captured during tests for debugging',
            'info');
    } else {
        hideMessage('traffic-info');
    }
}

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', () => {
    // Set up tab click handlers
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
    
    // Show first tab
    switchTab('connection');
    
    // Set up auto-start toggle
    const autoStartCheckbox = document.getElementById('setting-auto-start');
    if (autoStartCheckbox) {
        autoStartCheckbox.addEventListener('change', toggleAutoStart);
    }
    
    // Set up traffic capture toggle
    const trafficCheckbox = document.getElementById('setting-capture-traffic');
    if (trafficCheckbox) {
        trafficCheckbox.addEventListener('change', toggleTrafficCapture);
    }
    
    console.log('Settings panel initialized');
});
