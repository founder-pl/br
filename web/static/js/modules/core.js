/**
 * Core Module - API, Navigation, URL handling, Modals, Toast
 */

const API_BASE = '/api';
const PROJECT_ID = '00000000-0000-0000-0000-000000000001';
let currentFiscalYear = 2025;

// URL Management
function getPageFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('page') || 'dashboard';
}

function getUrlParam(key) {
    const params = new URLSearchParams(window.location.search);
    return params.get(key);
}

function setUrlParam(key, value, pushState = false) {
    const url = new URL(window.location.href);
    if (value === null || value === undefined || value === '') {
        url.searchParams.delete(key);
    } else {
        url.searchParams.set(key, String(value));
    }

    if (pushState) {
        history.pushState(Object.fromEntries(url.searchParams.entries()), '', url.pathname + url.search);
    } else {
        history.replaceState(Object.fromEntries(url.searchParams.entries()), '', url.pathname + url.search);
    }
}

function setPageInUrl(page, pushState = true) {
    setUrlParam('page', page, pushState);
}

// Confirm Modal
let _confirmModalResolve = null;

function closeConfirmModal() {
    const modal = document.getElementById('confirm-modal');
    if (modal) modal.classList.remove('active');
}

function confirmModalCancel() {
    if (_confirmModalResolve) {
        const resolve = _confirmModalResolve;
        _confirmModalResolve = null;
        closeConfirmModal();
        resolve(false);
    } else {
        closeConfirmModal();
    }
}

function openConfirmModal({ title, message, confirmText = 'OK' }) {
    const modal = document.getElementById('confirm-modal');
    const titleEl = document.getElementById('confirm-modal-title');
    const msgEl = document.getElementById('confirm-modal-message');
    const confirmBtn = document.getElementById('confirm-modal-confirm-btn');

    if (!modal || !titleEl || !msgEl || !confirmBtn) {
        return Promise.resolve(true);
    }

    if (_confirmModalResolve) {
        const resolve = _confirmModalResolve;
        _confirmModalResolve = null;
        resolve(false);
    }

    titleEl.textContent = title || '';
    msgEl.textContent = message || '';
    confirmBtn.textContent = confirmText;
    modal.classList.add('active');

    return new Promise(resolve => {
        _confirmModalResolve = resolve;
        const onConfirm = () => {
            if (_confirmModalResolve === resolve) {
                _confirmModalResolve = null;
                closeConfirmModal();
                resolve(true);
            }
        };
        confirmBtn.onclick = onConfirm;
    });
}

// Navigation
function navigateTo(page, options = {}) {
    const { year, month, expenseId, projectId, docId, pushState = true } = options;

    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const activeLink = document.querySelector(`.nav-link[data-page="${page}"]`);
    if (activeLink) activeLink.classList.add('active');

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const targetPage = document.getElementById(`page-${page}`);
    if (targetPage) targetPage.classList.add('active');

    setPageInUrl(page, pushState);
    if (year) setUrlParam('year', year);
    if (month) setUrlParam('month', month);

    // Page-specific loading
    const pageLoaders = {
        'dashboard': () => typeof loadDashboard === 'function' && loadDashboard(),
        'upload': () => typeof loadRecentDocuments === 'function' && loadRecentDocuments(),
        'expenses': () => typeof loadExpenses === 'function' && loadExpenses(),
        'reports': () => typeof loadReports === 'function' && loadReports(),
        'projects': () => typeof loadProjects === 'function' && loadProjects(),
        'timesheet': () => typeof loadTimesheetPage === 'function' && loadTimesheetPage(),
        'git-timesheet': () => typeof loadGitTimesheet === 'function' && loadGitTimesheet(),
        'config': () => typeof loadAIConfig === 'function' && loadAIConfig(),
        'doc-generator': () => typeof loadDocTemplates === 'function' && loadDocTemplates()
    };

    if (pageLoaders[page]) pageLoaders[page]();
}

// API Call
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const method = options.method || 'GET';
    const headers = { 'Content-Type': 'application/json', ...options.headers };

    console.log(`[API] ${method} ${url}`);
    if (options.body) {
        try {
            const parsed = JSON.parse(options.body);
            console.log('[API] Request body:', parsed);
        } catch (e) {
            console.log('[API] Request body (raw):', options.body);
        }
    }

    try {
        const response = await fetch(url, { ...options, headers });

        if (!response.ok) {
            let errorDetail = '';
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || JSON.stringify(errorData);
                console.error(`[API] Error ${response.status}:`, errorData);
            } catch (e) {
                errorDetail = await response.text();
                console.error(`[API] Error ${response.status}:`, errorDetail);
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            console.log(`[API] Response:`, data);
            return data;
        }
        return response;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;';
    document.body.appendChild(container);
    return container;
}

// Format helpers
function formatCurrency(amount, currency = 'PLN') {
    if (amount === null || amount === undefined) return '-';
    return new Intl.NumberFormat('pl-PL', { style: 'currency', currency }).format(amount);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('pl-PL');
}

// Export for modules
window.AppCore = {
    API_BASE,
    PROJECT_ID,
    currentFiscalYear,
    getPageFromUrl,
    getUrlParam,
    setUrlParam,
    setPageInUrl,
    openConfirmModal,
    closeConfirmModal,
    confirmModalCancel,
    navigateTo,
    apiCall,
    showToast,
    formatCurrency,
    formatDate
};
