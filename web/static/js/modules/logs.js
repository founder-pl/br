/**
 * Logs Module - Console logging and log overlay
 */

let logBuffer = [];
let originalConsoleLog, originalConsoleError, originalConsoleWarn;

function initLogging() {
    originalConsoleLog = console.log;
    originalConsoleError = console.error;
    originalConsoleWarn = console.warn;

    console.log = (...args) => {
        captureLog('log', args);
        originalConsoleLog.apply(console, args);
    };

    console.error = (...args) => {
        captureLog('error', args);
        originalConsoleError.apply(console, args);
    };

    console.warn = (...args) => {
        captureLog('warn', args);
        originalConsoleWarn.apply(console, args);
    };
}

function captureLog(level, args) {
    const timestamp = new Date().toISOString();
    const message = args.map(a => {
        if (typeof a === 'object') {
            try { return JSON.stringify(a, null, 2); }
            catch (e) { return String(a); }
        }
        return String(a);
    }).join(' ');

    logBuffer.push({ timestamp, level, message });
    if (logBuffer.length > 500) logBuffer.shift();

    updateLogOverlay({ timestamp, level, message });
}

function updateLogOverlay(entry) {
    const content = document.getElementById('global-log-content');
    if (!content) return;

    const div = document.createElement('div');
    div.className = `log-entry log-${entry.level}`;
    div.innerHTML = `<span class="log-time">${entry.timestamp.split('T')[1].split('.')[0]}</span> <span class="log-msg">${escapeHtml(entry.message)}</span>`;
    content.appendChild(div);

    if (content.children.length > 200) {
        content.removeChild(content.firstChild);
    }

    content.scrollTop = content.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleGlobalLogs() {
    const overlay = document.getElementById('global-log-overlay');
    if (overlay) {
        overlay.classList.toggle('active');
        if (overlay.classList.contains('active')) {
            const content = document.getElementById('global-log-content');
            if (content) content.scrollTop = content.scrollHeight;
        }
    }
}

function closeGlobalLogs() {
    const overlay = document.getElementById('global-log-overlay');
    if (overlay) overlay.classList.remove('active');
}

function clearGlobalLogs() {
    logBuffer = [];
    const content = document.getElementById('global-log-content');
    if (content) content.innerHTML = '';
}

function copyGlobalLogs() {
    const text = logBuffer.map(e => `[${e.timestamp}] [${e.level.toUpperCase()}] ${e.message}`).join('\n');
    navigator.clipboard.writeText(text).then(() => {
        showToast('Logi skopiowane do schowka', 'success');
    }).catch(() => {
        showToast('Błąd kopiowania', 'error');
    });
}

function downloadGlobalLogs() {
    const text = logBuffer.map(e => `[${e.timestamp}] [${e.level.toUpperCase()}] ${e.message}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `br-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Logi pobrane', 'success');
}

function filterGlobalLogs(level) {
    const content = document.getElementById('global-log-content');
    if (!content) return;

    content.innerHTML = '';
    const filtered = level ? logBuffer.filter(e => e.level === level) : logBuffer;
    filtered.forEach(entry => updateLogOverlay(entry));
}

// Export
window.LogsModule = {
    initLogging,
    logBuffer,
    toggleGlobalLogs,
    closeGlobalLogs,
    clearGlobalLogs,
    copyGlobalLogs,
    downloadGlobalLogs,
    filterGlobalLogs
};
