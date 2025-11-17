/**
 * Form Discoverer Agent - Setup Wizard JavaScript
 * Location: agent/web_ui/static/js/setup.js
 */

// Current step tracking
let currentStep = 1;
const totalSteps = 5;

// Setup data
const setupData = {
    apiUrl: '',
    token: '',
    companyId: null,
    userId: null,
    agentId: generateAgentId(),
    browser: 'chrome',
    headless: false,
    screenshotFolder: '',
    logFolder: '',
    filesFolder: ''
};

// ========== STEP NAVIGATION ==========

/**
 * Go to next step
 */
function nextStep() {
    if (currentStep < totalSteps) {
        // Validate current step before proceeding
        if (!validateStep(currentStep)) {
            return;
        }
        
        currentStep++;
        showStep(currentStep);
    }
}

/**
 * Go to previous step
 */
function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        showStep(currentStep);
    }
}

/**
 * Show specific step
 */
function showStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.add('hidden');
    });
    
    // Show current step
    const currentStepElement = document.getElementById(`step-${stepNumber}`);
    if (currentStepElement) {
        currentStepElement.classList.remove('hidden');
    }
    
    // Update progress indicators
    document.querySelectorAll('.step').forEach((step, index) => {
        const stepNum = index + 1;
        if (stepNum < stepNumber) {
            step.classList.add('completed');
            step.classList.remove('active');
        } else if (stepNum === stepNumber) {
            step.classList.add('active');
            step.classList.remove('completed');
        } else {
            step.classList.remove('active', 'completed');
        }
    });
    
    // Load step-specific data if needed
    if (stepNumber === 4) {
        loadConfigurationDefaults();
    } else if (stepNumber === 5) {
        showConfigurationSummary();
    }
}

/**
 * Validate current step
 */
function validateStep(stepNumber) {
    switch (stepNumber) {
        case 1:
            return true; // Welcome step, no validation
        case 2:
            if (!setupData.apiUrl) {
                showMessage('connection-result', 'Please connect to API server first', 'error');
                return false;
            }
            return true;
        case 3:
            if (!setupData.token) {
                showMessage('login-result', 'Please login first', 'error');
                return false;
            }
            return true;
        case 4:
            return validateConfiguration();
        default:
            return true;
    }
}

// ========== STEP 2: API DISCOVERY ==========

/**
 * Scan network for API server
 */
async function scanNetwork() {
    const scanButton = document.querySelector('button[onclick="scanNetwork()"]');
    const originalText = scanButton.textContent;
    
    showLoading(scanButton, 'Scanning...');
    hideMessage('scan-result');
    
    const result = await apiPost('/api/setup/scan', {});
    
    hideLoading(scanButton, originalText);
    
    if (result.success) {
        setupData.apiUrl = result.url;
        document.getElementById('api-url').value = result.url;
        showMessage('scan-result', `Found API server at ${result.url}`, 'success');
        document.getElementById('api-next-btn').disabled = false;
    } else {
        showMessage('scan-result', result.message || 'No API server found', 'error');
    }
}

/**
 * Test connection to API server
 */
async function testConnection() {
    const apiUrl = document.getElementById('api-url').value.trim();
    
    if (!apiUrl) {
        showMessage('connection-result', 'Please enter API URL', 'error');
        return;
    }
    
    if (!isValidUrl(apiUrl)) {
        showMessage('connection-result', 'Invalid URL format', 'error');
        return;
    }
    
    const testButton = document.querySelector('button[onclick="testConnection()"]');
    const originalText = testButton.textContent;
    
    showLoading(testButton, 'Testing...');
    hideMessage('connection-result');
    
    const result = await apiPost('/api/setup/test-connection', { url: apiUrl });
    
    hideLoading(testButton, originalText);
    
    if (result.success) {
        setupData.apiUrl = apiUrl;
        showMessage('connection-result', 'Connection successful!', 'success');
        document.getElementById('api-next-btn').disabled = false;
    } else {
        showMessage('connection-result', result.message || 'Connection failed', 'error');
        document.getElementById('api-next-btn').disabled = true;
    }
}

// ========== STEP 3: LOGIN ==========

/**
 * Login and get agent credentials
 */
async function doLogin() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    
    if (!email || !password) {
        showMessage('login-result', 'Please enter email and password', 'error');
        return;
    }
    
    if (!isValidEmail(email)) {
        showMessage('login-result', 'Invalid email format', 'error');
        return;
    }
    
    const loginButton = document.querySelector('button[onclick="doLogin()"]');
    const originalText = loginButton.textContent;
    
    showLoading(loginButton, 'Logging in...');
    hideMessage('login-result');
    
    const result = await apiPost('/api/setup/login', {
        email: email,
        password: password,
        api_url: setupData.apiUrl
    });
    
    hideLoading(loginButton, originalText);
    
    if (result.success) {
        setupData.token = result.token;
        setupData.companyId = result.company_id;
        setupData.userId = result.user_id;
        
        showMessage('login-result', 'Login successful!', 'success');
        document.getElementById('login-next-btn').disabled = false;
    } else {
        showMessage('login-result', result.message || 'Login failed', 'error');
        document.getElementById('login-next-btn').disabled = true;
    }
}

// Handle Enter key in login form
document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    
    if (emailInput && passwordInput) {
        [emailInput, passwordInput].forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    doLogin();
                }
            });
        });
    }
});

// ========== STEP 4: CONFIGURATION ==========

/**
 * Load default configuration values
 */
function loadConfigurationDefaults() {
    // Get user's home directory (platform-specific)
    const homeDir = '/home/' + (window.location.hostname || 'user');
    const baseDir = `${homeDir}/FormDiscovererAgent`;
    
    // Set default folders if not already set
    if (!setupData.screenshotFolder) {
        setupData.screenshotFolder = `${baseDir}/screenshots`;
        document.getElementById('screenshot-folder').value = setupData.screenshotFolder;
    }
    
    if (!setupData.logFolder) {
        setupData.logFolder = `${baseDir}/logs`;
        document.getElementById('log-folder').value = setupData.logFolder;
    }
    
    if (!setupData.filesFolder) {
        setupData.filesFolder = `${baseDir}/files`;
        document.getElementById('files-folder').value = setupData.filesFolder;
    }
    
    // Set browser and headless from current values
    document.getElementById('browser').value = setupData.browser;
    document.getElementById('headless').checked = setupData.headless;
}

/**
 * Validate configuration
 */
function validateConfiguration() {
    const browser = document.getElementById('browser').value;
    const headless = document.getElementById('headless').checked;
    const screenshotFolder = document.getElementById('screenshot-folder').value.trim();
    const logFolder = document.getElementById('log-folder').value.trim();
    const filesFolder = document.getElementById('files-folder').value.trim();
    
    if (!screenshotFolder || !logFolder || !filesFolder) {
        alert('Please fill in all folder locations');
        return false;
    }
    
    // Save configuration
    setupData.browser = browser;
    setupData.headless = headless;
    setupData.screenshotFolder = screenshotFolder;
    setupData.logFolder = logFolder;
    setupData.filesFolder = filesFolder;
    
    return true;
}

// ========== STEP 5: SUMMARY ==========

/**
 * Show configuration summary
 */
function showConfigurationSummary() {
    const summary = document.getElementById('config-summary');
    if (!summary) return;
    
    summary.innerHTML = `
        <div class="summary-item">
            <span class="summary-label">API Server:</span>
            <span class="summary-value">${setupData.apiUrl}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Agent ID:</span>
            <span class="summary-value">${setupData.agentId}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Company ID:</span>
            <span class="summary-value">${setupData.companyId}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">User ID:</span>
            <span class="summary-value">${setupData.userId}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Browser:</span>
            <span class="summary-value">${setupData.browser}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Headless Mode:</span>
            <span class="summary-value">${setupData.headless ? 'Yes' : 'No'}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Screenshots:</span>
            <span class="summary-value">${setupData.screenshotFolder}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Logs:</span>
            <span class="summary-value">${setupData.logFolder}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Files:</span>
            <span class="summary-value">${setupData.filesFolder}</span>
        </div>
    `;
}

/**
 * Finish setup and save configuration
 */
async function finishSetup() {
    const finishButton = document.querySelector('button[onclick="finishSetup()"]');
    const originalText = finishButton.textContent;
    
    showLoading(finishButton, 'Saving...');
    
    const result = await apiPost('/api/setup/save', setupData);
    
    if (result.success) {
        // Clear setup state from local storage
        clearSetupState();
        
        // Show success and redirect
        alert('Setup complete! Agent will now start.');
        
        // Redirect to dashboard
        window.location.href = '/';
    } else {
        hideLoading(finishButton, originalText);
        alert('Failed to save configuration: ' + (result.message || 'Unknown error'));
    }
}

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', () => {
    // Show first step
    showStep(1);
    
    // Load any saved progress
    if (window.setupState && window.setupState.currentStep > 1) {
        Object.assign(setupData, window.setupState);
        currentStep = window.setupState.currentStep;
        showStep(currentStep);
    }
    
    console.log('Setup wizard initialized');
});

// Save progress on page unload
window.addEventListener('beforeunload', () => {
    if (currentStep < totalSteps) {
        window.setupState = {
            ...setupData,
            currentStep: currentStep
        };
        saveSetupState();
    }
});
