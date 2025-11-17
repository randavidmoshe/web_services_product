/**
 * Form Discoverer Agent - Log Viewer JavaScript
 * Location: agent/web_ui/static/js/logs.js
 */

// Event source for live log streaming
let logEventSource = null;
let autoScroll = true;
let logLevel = 'all';

// ========== LOG STREAMING ==========

/**
 * Start live log streaming
 */
function startLogStreaming() {
    if (logEventSource) {
        stopLogStreaming();
    }
    
    // Create event source for Server-Sent Events
    logEventSource = new EventSource('/api/logs/stream');
    
    logEventSource.onmessage = (event) => {
        const logLine = event.data;
        appendLogLine(logLine);
    };
    
    logEventSource.onerror = (error) => {
        console.error('Log streaming error:', error);
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
            if (logEventSource && logEventSource.readyState === EventSource.CLOSED) {
                startLogStreaming();
            }
        }, 5000);
    };
    
    // Update button state
    const startButton = document.getElementById('start-logs-btn');
    const stopButton = document.getElementById('stop-logs-btn');
    if (startButton) startButton.style.display = 'none';
    if (stopButton) stopButton.style.display = 'inline-flex';
}

/**
 * Stop live log streaming
 */
function stopLogStreaming() {
    if (logEventSource) {
        logEventSource.close();
        logEventSource = null;
    }
    
    // Update button state
    const startButton = document.getElementById('start-logs-btn');
    const stopButton = document.getElementById('stop-logs-btn');
    if (startButton) startButton.style.display = 'inline-flex';
    if (stopButton) stopButton.style.display = 'none';
}

/**
 * Append log line to container
 */
function appendLogLine(line) {
    const container = document.getElementById('log-container');
    if (!container) return;
    
    // Determine log level from line content
    const level = detectLogLevel(line);
    
    // Filter by selected log level
    if (logLevel !== 'all' && level !== logLevel) {
        return;
    }
    
    // Create log line element
    const lineElement = document.createElement('div');
    lineElement.className = `log-line ${level}`;
    lineElement.textContent = line;
    
    // Append to container
    container.appendChild(lineElement);
    
    // Auto-scroll to bottom if enabled
    if (autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
    
    // Limit number of lines (keep last 1000)
    const lines = container.children;
    if (lines.length > 1000) {
        container.removeChild(lines[0]);
    }
}

/**
 * Detect log level from line content
 */
function detectLogLevel(line) {
    const lowerLine = line.toLowerCase();
    if (lowerLine.includes('error') || lowerLine.includes('exception')) return 'error';
    if (lowerLine.includes('warning') || lowerLine.includes('warn')) return 'warning';
    if (lowerLine.includes('success')) return 'success';
    if (lowerLine.includes('debug')) return 'debug';
    return 'info';
}

// ========== LOG CONTROLS ==========

/**
 * Clear logs
 */
function clearLogs() {
    if (!confirm('Clear all logs from view?')) {
        return;
    }
    
    const container = document.getElementById('log-container');
    if (container) {
        container.innerHTML = '';
    }
}

/**
 * Download logs as file
 */
async function downloadLogs() {
    try {
        const container = document.getElementById('log-container');
        if (!container) return;
        
        const lines = Array.from(container.children).map(el => el.textContent);
        const content = lines.join('\n');
        
        // Create blob and download
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `agent-logs-${new Date().toISOString()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Failed to download logs:', error);
        alert('Failed to download logs');
    }
}

/**
 * Toggle auto-scroll
 */
function toggleAutoScroll() {
    const checkbox = document.getElementById('auto-scroll-checkbox');
    if (checkbox) {
        autoScroll = checkbox.checked;
    }
}

/**
 * Filter logs by level
 */
function filterByLevel(level) {
    logLevel = level;
    
    // Update button states
    document.querySelectorAll('.log-filter-btn').forEach(btn => {
        if (btn.dataset.level === level) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Re-filter existing logs
    const container = document.getElementById('log-container');
    if (container) {
        Array.from(container.children).forEach(lineElement => {
            const lineLevelClass = Array.from(lineElement.classList).find(cls => 
                ['error', 'warning', 'success', 'debug', 'info'].includes(cls)
            );
            
            if (level === 'all' || lineLevelClass === level) {
                lineElement.style.display = '';
            } else {
                lineElement.style.display = 'none';
            }
        });
    }
}

/**
 * Search logs
 */
function searchLogs() {
    const searchInput = document.getElementById('log-search');
    if (!searchInput) return;
    
    const searchTerm = searchInput.value.toLowerCase();
    const container = document.getElementById('log-container');
    
    if (!container) return;
    
    Array.from(container.children).forEach(lineElement => {
        const text = lineElement.textContent.toLowerCase();
        if (!searchTerm || text.includes(searchTerm)) {
            lineElement.style.display = '';
        } else {
            lineElement.style.display = 'none';
        }
    });
}

// ========== LOAD HISTORY ==========

/**
 * Load log history
 */
async function loadLogHistory() {
    const lines = parseInt(document.getElementById('history-lines').value) || 1000;
    
    const result = await apiGet(`/api/logs/history?lines=${lines}`);
    
    if (result.logs) {
        const container = document.getElementById('log-container');
        if (container) {
            container.innerHTML = '';
            result.logs.forEach(line => appendLogLine(line));
        }
    } else if (result.error) {
        alert('Failed to load log history: ' + result.error);
    }
}

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', () => {
    // Load log history first
    loadLogHistory();
    
    // Start live streaming
    startLogStreaming();
    
    // Set up auto-scroll checkbox
    const autoScrollCheckbox = document.getElementById('auto-scroll-checkbox');
    if (autoScrollCheckbox) {
        autoScrollCheckbox.checked = autoScroll;
        autoScrollCheckbox.addEventListener('change', toggleAutoScroll);
    }
    
    // Set up search input
    const searchInput = document.getElementById('log-search');
    if (searchInput) {
        searchInput.addEventListener('input', searchLogs);
    }
    
    // Set up filter buttons
    document.querySelectorAll('.log-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            filterByLevel(btn.dataset.level);
        });
    });
    
    console.log('Log viewer initialized');
});

// Stop streaming when leaving page
window.addEventListener('beforeunload', () => {
    stopLogStreaming();
});
