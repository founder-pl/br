/**
 * System B+R - Main Application JavaScript
 */

const API_BASE = '/api';
const PROJECT_ID = '00000000-0000-0000-0000-000000000001';
let currentFiscalYear = 2025;

// Navigation - setup in DOMContentLoaded below

function getPageFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('page') || 'dashboard';
}

async function processAllExpensesForYear() {
    const year = parseInt(document.getElementById('report-year')?.value || currentFiscalYear);
    const confirmed = await openConfirmModal({
        title: 'Przetwórz wszystkie wydatki',
        message: `Uruchomić automatyczne przetwarzanie (walidacja, uzupełnienie danych, waluty, kategorie, uzasadnienia) dla roku ${year}?`,
        confirmText: 'Przetwórz'
    });
    if (!confirmed) return;
    
    try {
        showToast('Przetwarzanie wydatków...', 'info');
        await apiCall('/expenses/process-all', {
            method: 'POST',
            body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: year })
        });
        showToast('Przetwarzanie zakończone', 'success');
        loadReports();
        loadDashboard();
        const expensesPage = document.getElementById('page-expenses');
        if (expensesPage && expensesPage.classList.contains('active')) {
            loadExpenses();
        }
    } catch (e) {
        showToast('Błąd przetwarzania', 'error');
    }
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

    titleEl.textContent = title || 'Potwierdzenie';
    msgEl.textContent = message || '';
    confirmBtn.textContent = confirmText;

    return new Promise((resolve) => {
        _confirmModalResolve = resolve;
        confirmBtn.onclick = () => {
            if (_confirmModalResolve) {
                const r = _confirmModalResolve;
                _confirmModalResolve = null;
                closeConfirmModal();
                r(true);
            }
        };

        modal.classList.add('active');
    });
}

function navigateTo(page, options = {}) {
    const { updateUrl = true } = options;

    const navItem = document.querySelector(`[data-page="${page}"]`);
    const pageEl = document.getElementById(`page-${page}`);
    if (!navItem || !pageEl) {
        page = 'dashboard';
    }

    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');

    if (updateUrl) {
        setPageInUrl(page, true);
    }
    
    const loaders = { dashboard: loadDashboard, upload: () => { setupUploadListeners(); loadRecentDocuments(); }, 
                      projects: loadProjects, expenses: () => { initExpenseFilters(); loadProjectsForFilter(); loadExpenses(); },
                      reports: loadReports, clarifications: loadClarifications, timesheet: initTimesheet,
                      integrations: loadIntegrations, logs: initLogStreams, 'ai-config': loadAIConfig,
                      'git-timesheet': initGitTimesheet, 'doc-generator': loadDocTemplates,
                      'doc-annotations': loadDocAnnotations };
    if (loaders[page]) loaders[page]();
    
    // Stop log streams when leaving logs page
    if (page !== 'logs' && !isGlobalLogsOpen()) stopAllLogStreams();
}

// API
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers }, ...options
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast('Błąd połączenia z serwerem', 'error');
        throw error;
    }
}

// Dashboard Modules Configuration
const DASHBOARD_MODULES = {
    'total-expenses': { icon: '💰', title: 'Wydatki ogółem', size: '1x1', type: 'stat', dataKey: 'total_expenses' },
    'br-expenses': { icon: '✅', title: 'Koszty B+R', size: '1x1', type: 'stat', dataKey: 'br_qualified_expenses', highlight: true },
    'br-deduction': { icon: '📉', title: 'Odliczenie B+R', size: '1x1', type: 'stat', dataKey: 'br_deduction_amount' },
    'ip-expenses': { icon: '🎯', title: 'Koszty IP Box', size: '1x1', type: 'stat', dataKey: 'ip_qualified_expenses' },
    'documents-count': { icon: '📄', title: 'Dokumenty', size: '1x1', type: 'stat', dataKey: 'documents_count', format: 'number' },
    'pending-docs': { icon: '⏳', title: 'Oczekujące', size: '1x1', type: 'stat', dataKey: 'pending_documents', format: 'number' },
    'clarifications': { icon: '❓', title: 'Wyjaśnienia', size: '1x1', type: 'stat', dataKey: 'needs_clarification', format: 'number' },
    'recent-documents': { icon: '📑', title: 'Ostatnie dokumenty', size: '2x2', type: 'list', loader: 'loadRecentDocsModule' },
    'category-breakdown': { icon: '📊', title: 'Wydatki wg kategorii', size: '2x2', type: 'chart', loader: 'loadCategoryModule' },
    'quick-actions': { icon: '⚡', title: 'Szybkie akcje', size: '1x2', type: 'actions' },
    'timesheet-summary': { icon: '⏱️', title: 'Czas pracy', size: '2x1', type: 'custom', loader: 'loadTimesheetModule' },
    'git-activity': { icon: '🔀', title: 'Aktywność Git', size: '2x1', type: 'custom', loader: 'loadGitActivityModule' },
    'project-progress': { icon: '📈', title: 'Postęp projektu', size: '2x1', type: 'progress' },
    'fiscal-year': { icon: '📅', title: 'Rok podatkowy', size: '1x1', type: 'stat', dataKey: 'fiscal_year', format: 'year' },
    'monthly-trend': { icon: '📉', title: 'Trend miesięczny', size: '2x2', type: 'chart', loader: 'loadMonthlyTrendModule' },
    'top-vendors': { icon: '🏢', title: 'Top dostawcy', size: '2x2', type: 'list', loader: 'loadTopVendorsModule' }
};

const DEFAULT_DASHBOARD_LAYOUT = [
    'total-expenses', 'br-expenses', 'br-deduction', 'ip-expenses',
    'documents-count', 'pending-docs', 'clarifications', 'fiscal-year',
    'recent-documents', 'category-breakdown', 'quick-actions', 'top-vendors'
];

let dashboardLayout = [];
let dashboardData = {};

function getDashboardLayout() {
    const saved = localStorage.getItem('dashboardLayout');
    return saved ? JSON.parse(saved) : [...DEFAULT_DASHBOARD_LAYOUT];
}

function saveDashboardLayout() {
    localStorage.setItem('dashboardLayout', JSON.stringify(dashboardLayout));
}

function toggleDashboardConfig() {
    const config = document.getElementById('dashboard-config');
    config.style.display = config.style.display === 'none' ? 'block' : 'none';
    updateModuleSelect();
}

function updateModuleSelect() {
    const select = document.getElementById('add-module-select');
    const available = Object.keys(DASHBOARD_MODULES).filter(m => !dashboardLayout.includes(m));
    select.innerHTML = '<option value="">-- Wybierz moduł --</option>' +
        available.map(m => `<option value="${m}">${DASHBOARD_MODULES[m].icon} ${DASHBOARD_MODULES[m].title}</option>`).join('');
}

function addDashboardModule(moduleId) {
    if (!moduleId || dashboardLayout.includes(moduleId)) return;
    dashboardLayout.push(moduleId);
    saveDashboardLayout();
    renderDashboard();
}

function removeDashboardModule(moduleId) {
    dashboardLayout = dashboardLayout.filter(m => m !== moduleId);
    saveDashboardLayout();
    renderDashboard();
}

function resetDashboardConfig() {
    dashboardLayout = [...DEFAULT_DASHBOARD_LAYOUT];
    saveDashboardLayout();
    renderDashboard();
    showToast('Dashboard zresetowany', 'success');
}

function renderDashboard() {
    const container = document.getElementById('dashboard-modules');
    if (!container) return;
    
    container.innerHTML = dashboardLayout.map(moduleId => {
        const mod = DASHBOARD_MODULES[moduleId];
        if (!mod) return '';
        const sizeClass = `module-${mod.size.replace('x', 'by-')}`;
        const highlightClass = mod.highlight ? 'highlight' : '';
        return `
            <div class="dashboard-module ${sizeClass} ${highlightClass}" data-module="${moduleId}">
                <div class="module-header">
                    <span class="module-icon">${mod.icon}</span>
                    <span class="module-title">${mod.title}</span>
                    <button class="module-remove" onclick="removeDashboardModule('${moduleId}')" title="Usuń">×</button>
                </div>
                <div class="module-content" id="module-${moduleId}">
                    <div class="loading-spinner"></div>
                </div>
            </div>
        `;
    }).join('');
    
    updateModuleSelect();
    loadDashboardModules();
}

async function loadDashboard() {
    dashboardLayout = getDashboardLayout();
    renderDashboard();
}

async function loadDashboardModules() {
    try {
        const summary = await apiCall(`/projects/${PROJECT_ID}/summary`);
        dashboardData = summary;
        const badge = document.getElementById('clarification-badge');
        if (badge) badge.textContent = summary.needs_clarification || 0;
        
        // Update stat modules
        dashboardLayout.forEach(moduleId => {
            const mod = DASHBOARD_MODULES[moduleId];
            if (!mod) return;
            const content = document.getElementById(`module-${moduleId}`);
            if (!content) return;
            
            if (mod.type === 'stat') {
                const value = summary[mod.dataKey];
                let formatted;
                if (mod.format === 'number') formatted = value ?? 0;
                else if (mod.format === 'year') formatted = value ?? new Date().getFullYear();
                else formatted = formatCurrency(value ?? 0);
                content.innerHTML = `<p class="stat-value">${formatted}</p>`;
            } else if (mod.type === 'actions') {
                content.innerHTML = `
                    <div class="quick-actions-grid">
                        <button class="btn btn-sm" onclick="navigateTo('upload')">📄 Upload</button>
                        <button class="btn btn-sm" onclick="navigateTo('expenses')">💰 Wydatki</button>
                        <button class="btn btn-sm" onclick="navigateTo('reports')">📊 Raporty</button>
                        <button class="btn btn-sm" onclick="navigateTo('timesheet')">⏱️ Timesheet</button>
                    </div>`;
            } else if (mod.type === 'progress') {
                const progress = summary.documents_count > 0 ? Math.min(100, Math.round((summary.documents_count - summary.pending_documents) / summary.documents_count * 100)) : 0;
                content.innerHTML = `
                    <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
                    <p class="progress-text">${progress}% ukończone</p>`;
            } else if (mod.loader) {
                window[mod.loader]?.(content, summary);
            }
        });
    } catch (error) { console.error('Dashboard error:', error); }
}

async function loadRecentDocsModule(container) {
    try {
        const docs = await apiCall(`/documents/?limit=5`);
        if (docs.length === 0) {
            container.innerHTML = '<p class="empty-state">Brak dokumentów</p>';
            return;
        }
        container.innerHTML = docs.map(d => `
            <div class="mini-doc-item" onclick="showDocumentDetail('${d.id}')">
                <span class="doc-status ${d.ocr_status}"></span>
                <span class="doc-name">${d.filename.substring(0, 25)}${d.filename.length > 25 ? '...' : ''}</span>
            </div>
        `).join('');
    } catch (e) { container.innerHTML = '<p class="empty-state">Błąd</p>'; }
}

function loadCategoryModule(container, summary) {
    if (!summary.expenses_by_category || Object.keys(summary.expenses_by_category).length === 0) {
        container.innerHTML = '<p class="empty-state">Brak danych</p>';
        return;
    }
    container.innerHTML = Object.entries(summary.expenses_by_category)
        .map(([cat, amount]) => `<div class="category-item"><span>${getCategoryName(cat)}</span><span>${formatCurrency(amount)}</span></div>`).join('');
}

async function loadTopVendorsModule(container) {
    try {
        const vendors = await apiCall('/timesheet/contractors');
        if (!vendors || vendors.length === 0) {
            container.innerHTML = '<p class="empty-state">Brak dostawców</p>';
            return;
        }
        container.innerHTML = vendors.slice(0, 5).map(v => `
            <div class="vendor-item">
                <span class="vendor-name">${v.vendor_name || 'Nieznany'}</span>
                <span class="vendor-total">${formatCurrency(v.total)}</span>
            </div>
        `).join('');
    } catch (e) { container.innerHTML = '<p class="empty-state">Błąd</p>'; }
}

async function loadTimesheetModule(container) {
    try {
        const workers = await apiCall('/timesheet/workers');
        container.innerHTML = `<p class="stat-value">${workers.length} pracowników</p>`;
    } catch (e) { container.innerHTML = '<p class="empty-state">-</p>'; }
}

async function loadGitActivityModule(container) {
    container.innerHTML = `<p class="stat-mini">Użyj Git Timesheet →</p>
        <button class="btn btn-sm" onclick="navigateTo('git-timesheet')">🔀 Otwórz</button>`;
}

async function loadMonthlyTrendModule(container) {
    try {
        const expenses = await apiCall(`/expenses/?limit=100`);
        const byMonth = {};
        expenses.forEach(e => {
            const m = e.invoice_date?.substring(0, 7) || 'Brak';
            byMonth[m] = (byMonth[m] || 0) + parseFloat(e.gross_amount || 0);
        });
        const sorted = Object.entries(byMonth).sort((a, b) => b[0].localeCompare(a[0])).slice(0, 6);
        if (sorted.length === 0) {
            container.innerHTML = '<p class="empty-state">Brak danych</p>';
            return;
        }
        container.innerHTML = sorted.map(([m, v]) => `
            <div class="trend-item"><span>${m}</span><span>${formatCurrency(v)}</span></div>
        `).join('');
    } catch (e) { container.innerHTML = '<p class="empty-state">Błąd</p>'; }
}

// Upload - setup event listeners lazily
function setupUploadListeners() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    if (!uploadArea || !fileInput) return;
    if (uploadArea._listenersAttached) return;
    uploadArea._listenersAttached = true;

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', (e) => { e.preventDefault(); uploadArea.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));
}

function handleFiles(files) { Array.from(files).forEach(uploadFile); }

async function uploadFile(file) {
    const itemId = `upload-${Date.now()}`;
    
    document.getElementById('upload-queue').insertAdjacentHTML('beforeend', `
        <div class="upload-item" id="${itemId}">
            <span>📄 ${file.name}</span>
            <div class="upload-progress"><div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div></div>
            <span class="upload-status">Przesyłanie...</span>
        </div>
    `);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE}/documents/upload?project_id=${PROJECT_ID}&document_type=auto`, { method: 'POST', body: formData });
        const result = await response.json();
        
        if (response.ok) {
            document.querySelector(`#${itemId} .progress-fill`).style.width = '100%';
            document.querySelector(`#${itemId} .upload-status`).textContent = 'OCR w toku...';
            pollDocumentStatus(result.document_id, itemId);
            showToast('Dokument przesłany', 'success');
        } else throw new Error(result.detail);
    } catch (error) {
        document.querySelector(`#${itemId} .upload-status`).textContent = 'Błąd!';
        showToast(`Błąd: ${error.message}`, 'error');
    }
}

async function pollDocumentStatus(docId, itemId) {
    let attempts = 0;
    const poll = async () => {
        try {
            const doc = await apiCall(`/documents/${docId}`);
            if (doc.ocr_status === 'completed') {
                document.querySelector(`#${itemId} .upload-status`).textContent = 'Gotowe ✓';
                loadRecentDocuments(); return;
            } else if (doc.ocr_status === 'failed') {
                document.querySelector(`#${itemId} .upload-status`).textContent = 'Błąd OCR'; return;
            }
            if (++attempts < 60) setTimeout(poll, 2000);
        } catch (e) { console.error('Poll error:', e); }
    };
    poll();
}

async function loadRecentDocuments() {
    try {
        const docs = await apiCall(`/documents/?project_id=${PROJECT_ID}&limit=10`);
        const html = docs.length === 0 ? '<p class="empty-state">Brak dokumentów</p>' :
            docs.map(d => `
                <div class="document-item" data-id="${d.id}">
                    <div class="doc-info" onclick="showDocumentDetail('${d.id}')">
                        <span class="doc-icon">📄</span>
                        <span class="doc-name">${d.filename}</span>
                        <span class="doc-type">${getDocTypeName(d.document_type)}</span>
                    </div>
                    <div class="doc-actions">
                        <span class="status-badge ${d.ocr_status}">${getStatusLabel(d.ocr_status)}</span>
                        <button class="btn-icon" onclick="retryOcr('${d.id}')" title="Powtórz OCR">🔄</button>
                        <button class="btn-icon btn-danger" onclick="deleteDocument('${d.id}')" title="Usuń">🗑️</button>
                    </div>
                </div>
            `).join('');
        const recentDocs = document.getElementById('recent-documents');
        const uploadedDocs = document.getElementById('uploaded-documents');
        if (recentDocs) recentDocs.innerHTML = html;
        if (uploadedDocs) uploadedDocs.innerHTML = html;
    } catch (e) { console.error('Error:', e); }
}

function getDocTypeName(type) {
    const types = { invoice: 'Faktura', receipt: 'Paragon', contract: 'Umowa', protocol: 'Protokół', report: 'Raport', other: 'Inny', auto: 'Auto' };
    return types[type] || type;
}

window.deleteDocument = async function(docId) {
    const confirmed = await openConfirmModal({
        title: 'Usuń dokument',
        message: 'Czy na pewno chcesz usunąć ten dokument?',
        confirmText: 'Usuń'
    });
    if (!confirmed) return false;
    try {
        await apiCall(`/documents/${docId}`, { method: 'DELETE' });
        document.querySelectorAll(`.document-item[data-id="${docId}"]`).forEach(el => el.remove());
        showToast('Dokument usunięty', 'success');
        loadRecentDocuments();
        return true;
    } catch (e) {
        showToast('Błąd usuwania dokumentu', 'error');
        return false;
    }
};

async function deleteDocumentFromModal(docId) {
    const deleted = await window.deleteDocument(docId);
    if (deleted) {
        closeDocumentModal();
    }
}

async function retryOcr(docId) {
    try {
        await apiCall(`/documents/${docId}/reprocess`, { method: 'POST' });
        showToast('OCR uruchomiony ponownie', 'success');
        loadRecentDocuments();
    } catch (e) { showToast('Błąd uruchamiania OCR', 'error'); }
}

let currentDocData = null;

function normalizeExtractedData(raw) {
    if (!raw || typeof raw !== 'object') return {};
    const nested = raw.extracted_data;
    if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
        const { extracted_data, ...rest } = raw;
        return { ...rest, ...nested };
    }
    return raw;
}

function formatExtractedValue(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') {
        try {
            return JSON.stringify(v);
        } catch (e) {
            return String(v);
        }
    }
    return String(v);
}

async function showDocumentDetail(docId, options = {}) {
    const { updateUrl = true } = options;
    try {
        if (updateUrl) {
            setUrlParam('doc', docId, true);
        }
        const doc = await apiCall(`/documents/${docId}/detail`);
        currentDocData = doc;
        const modal = document.getElementById('document-modal');
        
        const editableFields = ['invoice_number', 'invoice_date', 'gross_amount', 'net_amount', 'vat_amount', 'vendor_name', 'vendor_nip', 'description'];
        const extractedData = normalizeExtractedData(doc.extracted_data || {});
        
        document.getElementById('document-modal-content').innerHTML = `
            <div class="doc-detail-header">
                <h3>📄 ${doc.filename}</h3>
                <span class="status-badge ${doc.ocr_status}">${getStatusLabel(doc.ocr_status)}</span>
            </div>
            <div class="doc-detail-info">
                <p><strong>Typ:</strong> ${getDocTypeName(doc.document_type)}</p>
                <p><strong>Pewność OCR:</strong> ${doc.ocr_confidence ? (doc.ocr_confidence * 100).toFixed(1) + '%' : '-'}</p>
                <p><strong>Data dodania:</strong> ${new Date(doc.created_at).toLocaleString('pl-PL')}</p>
                <div class="ocr-engine-select">
                    <label><strong>Silnik OCR:</strong></label>
                    <select id="ocr-engine-select" onchange="updateOcrEngine(this.value)">
                        <option value="paddleocr" selected>PaddleOCR (domyślny)</option>
                        <option value="tesseract">Tesseract</option>
                        <option value="easyocr">EasyOCR</option>
                    </select>
                </div>
            </div>
            <div class="doc-detail-section">
                <h4>Wyodrębnione dane 
                    <button class="btn btn-sm" onclick="toggleEditMode()">✏️ Edytuj</button>
                    <button class="btn btn-sm btn-ai" onclick="fillFieldsWithLLM('${docId}')" title="Uzupełnij puste pola za pomocą AI">🤖 Uzupełnij AI</button>
                </h4>
                <div class="extracted-data" id="extracted-data-view">
                    ${Object.entries(extractedData)
                        .filter(([k]) => !k.startsWith('_'))
                        .map(([k, v]) => `<div class="data-row"><span class="data-key">${k}:</span> <span class="data-value">${formatExtractedValue(v)}</span></div>`).join('') || '<p class="empty-state">Brak danych</p>'}
                </div>
                <div class="extracted-data-edit" id="extracted-data-edit" style="display:none;">
                    <div class="edit-grid">
                        ${editableFields.map(field => `
                            <div class="edit-field">
                                <label>${getFieldLabel(field)}</label>
                                <input type="${field.includes('date') ? 'date' : field.includes('amount') ? 'number' : 'text'}" 
                                       id="edit-${field}" 
                                       value="${extractedData[field] || ''}"
                                       ${field.includes('amount') ? 'step="0.01"' : ''}>
                            </div>
                        `).join('')}
                    </div>
                    <div class="edit-actions">
                        <button class="btn btn-primary" onclick="saveExtractedData('${docId}')">💾 Zapisz</button>
                        <button class="btn btn-secondary" onclick="toggleEditMode()">Anuluj</button>
                    </div>
                </div>
            </div>
            ${doc.ocr_text ? `
                <div class="doc-detail-section collapsible">
                    <h4 onclick="this.parentElement.classList.toggle('collapsed')">Tekst OCR ▼</h4>
                    <pre class="ocr-text">${doc.ocr_text}</pre>
                </div>
            ` : ''}
            ${doc.validation_errors && doc.validation_errors.length > 0 ? `
                <div class="doc-detail-section error-section">
                    <h4>Błędy</h4>
                    <ul>${doc.validation_errors.map(e => `<li>${e}</li>`).join('')}</ul>
                </div>
            ` : ''}
            <div id="duplicate-check-result"></div>
            <div class="doc-detail-actions">
                <button class="btn btn-primary" onclick="retryOcr('${docId}'); closeDocumentModal();">🔄 Powtórz OCR</button>
                <button class="btn btn-secondary" onclick="reExtractData('${docId}')">🔍 Ponowne wyodrębnienie</button>
                <button class="btn btn-warning" onclick="checkDuplicates('${docId}')">🔎 Sprawdź duplikaty</button>
                <button class="btn btn-success" onclick="createExpenseFromDoc('${docId}')">📤 Utwórz wydatek</button>
                <button class="btn btn-info" onclick="createRevenueFromDoc('${docId}')">📥 Utwórz przychód</button>
                <button class="btn btn-danger" onclick="deleteDocumentFromModal('${docId}')">🗑️ Usuń</button>
            </div>
        `;
        modal.classList.add('active');
    } catch (e) { showToast('Błąd ładowania szczegółów', 'error'); }
}

function getFieldLabel(field) {
    const labels = {
        'invoice_number': 'Nr faktury',
        'invoice_date': 'Data faktury',
        'gross_amount': 'Kwota brutto',
        'net_amount': 'Kwota netto',
        'vat_amount': 'Kwota VAT',
        'vendor_name': 'Nazwa sprzedawcy',
        'vendor_nip': 'NIP sprzedawcy',
        'description': 'Opis'
    };
    return labels[field] || field;
}

function toggleEditMode() {
    const view = document.getElementById('extracted-data-view');
    const edit = document.getElementById('extracted-data-edit');
    if (view && edit) {
        const isEditing = edit.style.display !== 'none';
        view.style.display = isEditing ? 'block' : 'none';
        edit.style.display = isEditing ? 'none' : 'block';
    }
}

async function saveExtractedData(docId) {
    const fields = ['invoice_number', 'invoice_date', 'gross_amount', 'net_amount', 'vat_amount', 'vendor_name', 'vendor_nip', 'description'];
    const extractedData = { ...normalizeExtractedData(currentDocData?.extracted_data || {}) };
    
    fields.forEach(field => {
        const input = document.getElementById(`edit-${field}`);
        if (!input) return;
        if (field.includes('amount')) {
            extractedData[field] = input.value === '' ? null : parseFloat(input.value);
        } else {
            extractedData[field] = input.value === '' ? null : input.value;
        }
    });
    
    try {
        await apiCall(`/documents/${docId}`, {
            method: 'PATCH',
            body: JSON.stringify({ extracted_data: extractedData })
        });
        showToast('Dane zapisane', 'success');
        showDocumentDetail(docId, { updateUrl: false });
    } catch (e) {
        showToast('Błąd zapisywania', 'error');
    }
}

async function createExpenseFromDoc(docId) {
    if (!currentDocData) return;
    const data = currentDocData.extracted_data || {};
    
    const grossAmount = parseFloat(data.gross_amount || data.total_gross || 0);
    const netAmount = parseFloat(data.net_amount || grossAmount * 0.81); // assume 23% VAT if not specified
    const vatAmount = parseFloat(data.vat_amount || (grossAmount - netAmount));
    
    try {
        const response = await fetch(`${API_BASE}/expenses/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: PROJECT_ID,
                document_id: docId,
                invoice_number: data.invoice_number || null,
                invoice_date: data.invoice_date || null,
                vendor_name: data.vendor_name || null,
                vendor_nip: data.vendor_nip || null,
                gross_amount: grossAmount,
                net_amount: netAmount,
                vat_amount: vatAmount,
                currency: 'PLN',
                description: data.description || `Faktura ${data.invoice_number || currentDocData.filename}`,
                expense_category: 'other'
            })
        });
        
        if (response.ok) {
            showToast('Wydatek utworzony', 'success');
            closeDocumentModal();
            navigateTo('expenses');
        } else {
            const err = await response.json();
            showToast(`Błąd: ${err.detail || 'Nie udało się utworzyć wydatku'}`, 'error');
        }
    } catch (e) {
        showToast('Błąd tworzenia wydatku', 'error');
    }
}

async function createRevenueFromDoc(docId) {
    if (!currentDocData) return;
    const data = currentDocData.extracted_data || {};
    
    const grossAmount = parseFloat(data.gross_amount || data.total_gross || 0);
    const netAmount = parseFloat(data.net_amount || grossAmount * 0.81);
    const vatAmount = parseFloat(data.vat_amount || (grossAmount - netAmount));
    
    try {
        const response = await fetch(`${API_BASE}/expenses/revenues/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: PROJECT_ID,
                document_id: docId,
                invoice_number: data.invoice_number || null,
                invoice_date: data.invoice_date || null,
                client_name: data.vendor_name || data.client_name || null,
                client_nip: data.vendor_nip || data.client_nip || null,
                gross_amount: grossAmount,
                net_amount: netAmount,
                vat_amount: vatAmount,
                currency: data.currency || 'PLN',
                description: data.description || `Faktura ${data.invoice_number || currentDocData.filename}`,
                ip_qualified: false
            })
        });
        
        if (response.ok) {
            showToast('Przychód utworzony', 'success');
            closeDocumentModal();
            navigateTo('expenses');
            document.getElementById('expense-filter-type').value = 'revenue';
            loadExpenses();
        } else {
            const err = await response.json();
            showToast(`Błąd: ${err.detail || 'Nie udało się utworzyć przychodu'}`, 'error');
        }
    } catch (e) {
        showToast('Błąd tworzenia przychodu', 'error');
    }
}

function closeDocumentModal(options = {}) {
    const { updateUrl = true } = options;
    if (updateUrl) {
        setUrlParam('doc', null, true);
    }
    document.getElementById('document-modal').classList.remove('active');
}

async function approveDocument(docId) {
    try {
        await apiCall(`/documents/${docId}?ocr_status=approved`, { method: 'PATCH' });
        showToast('Dokument zatwierdzony', 'success');
        closeDocumentModal();
        loadRecentDocuments();
    } catch (e) { showToast('Błąd zatwierdzania', 'error'); }
}

// ==================== PROJECTS ====================
let projectsCache = [];

async function loadProjects() {
    try {
        projectsCache = await apiCall('/projects/');
        
        if (projectsCache.length === 0) {
            document.getElementById('projects-list').innerHTML = `
                <div class="empty-state-card">
                    <p>Brak projektów B+R</p>
                    <button class="btn btn-primary" onclick="showCreateProjectModal()">➕ Utwórz pierwszy projekt</button>
                </div>`;
            return;
        }
        
        document.getElementById('projects-list').innerHTML = projectsCache.map(p => `
            <div class="project-card" data-id="${p.id}">
                <div class="project-header">
                    <h3>${p.name}</h3>
                    <span class="project-year">${p.fiscal_year}</span>
                </div>
                <div class="project-stats">
                    <div class="stat">
                        <span class="stat-value">${formatCurrency(p.total_expenses)}</span>
                        <span class="stat-label">Wydatki ogółem</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">${formatCurrency(p.br_qualified_expenses)}</span>
                        <span class="stat-label">Kwalifikowane B+R</span>
                    </div>
                </div>
                <p class="project-desc">${p.description || 'Brak opisu'}</p>
                <div class="project-actions">
                    <button class="btn btn-sm btn-secondary" onclick="editProject('${p.id}')">✏️ Edytuj</button>
                    <button class="btn btn-sm btn-primary" onclick="viewProjectExpenses('${p.id}')">💰 Wydatki</button>
                    <button class="btn btn-sm btn-success" onclick="viewProjectDocs('${p.id}')">📄 Podgląd</button>
                    <button class="btn btn-sm btn-warning" onclick="generateProjectSummary('${p.id}')">📝 Generuj</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteProject('${p.id}')">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (e) { 
        console.error('Error loading projects:', e);
        document.getElementById('projects-list').innerHTML = '<p class="error">Błąd ładowania projektów</p>';
    }
}

function showCreateProjectModal() {
    const name = prompt('Nazwa projektu:');
    if (!name) return;
    const description = prompt('Opis projektu (opcjonalnie):') || '';
    const year = prompt('Rok podatkowy:', '2025') || '2025';
    
    createProject(name, description, parseInt(year));
}

async function createProject(name, description, fiscalYear) {
    try {
        await apiCall('/projects/', {
            method: 'POST',
            body: JSON.stringify({ name, description, fiscal_year: fiscalYear })
        });
        showToast('Projekt utworzony', 'success');
        loadProjects();
    } catch (e) { showToast('Błąd tworzenia projektu', 'error'); }
}

async function editProject(id) {
    const project = projectsCache.find(p => p.id === id);
    if (!project) return;
    
    const name = prompt('Nazwa projektu:', project.name);
    if (!name) return;
    const description = prompt('Opis projektu:', project.description || '');
    
    try {
        await apiCall(`/projects/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ name, description })
        });
        showToast('Projekt zaktualizowany', 'success');
        loadProjects();
    } catch (e) { showToast('Błąd aktualizacji projektu', 'error'); }
}

async function deleteProject(id) {
    if (!confirm('Czy na pewno chcesz usunąć ten projekt?')) return;
    try {
        await apiCall(`/projects/${id}`, { method: 'DELETE' });
        showToast('Projekt usunięty', 'success');
        loadProjects();
    } catch (e) { 
        showToast('Nie można usunąć projektu z wydatkami', 'error'); 
    }
}

function viewProjectExpenses(projectId) {
    navigateTo('expenses');
    setTimeout(() => {
        document.getElementById('expense-filter-project').value = projectId;
        loadExpenses();
    }, 100);
}

// Load projects for filter dropdowns
async function loadProjectsForFilter() {
    try {
        projectsCache = await apiCall('/projects/');
        
        // Update expense filter dropdown
        const filterSelect = document.getElementById('expense-filter-project');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">Wszystkie projekty</option>' +
                projectsCache.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        }
        
        // Update bulk assign dropdown
        const bulkSelect = document.getElementById('bulk-assign-project');
        if (bulkSelect) {
            bulkSelect.innerHTML = '<option value="">Przypisz do projektu...</option>' +
                projectsCache.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        }
    } catch (e) { console.error('Error loading projects:', e); }
}

function getProjectName(projectId) {
    const project = projectsCache.find(p => p.id === projectId);
    return project ? project.name : '-';
}

// Expenses and Revenues
let selectedExpenses = new Set();

function initExpenseFilters() {
    // Initialize filters from URL params on page load
    const urlYear = getUrlParam('year');
    const urlMonth = getUrlParam('month');
    
    if (urlYear && document.getElementById('expense-filter-year')) {
        document.getElementById('expense-filter-year').value = urlYear;
    }
    if (urlMonth && document.getElementById('expense-filter-month')) {
        document.getElementById('expense-filter-month').value = urlMonth;
    }
}

async function loadExpenses() {
    try {
        const typeFilter = document.getElementById('expense-filter-type')?.value || 'expense';
        const projectFilter = document.getElementById('expense-filter-project')?.value;
        const status = document.getElementById('expense-filter-status')?.value;
        const brQualified = document.getElementById('expense-filter-br')?.value;
        // Get current filter values from selects
        const year = document.getElementById('expense-filter-year')?.value || '';
        const month = document.getElementById('expense-filter-month')?.value || '';
        
        // Update URL params when filters change
        if (year) {
            setUrlParam('year', year, true);
        } else {
            setUrlParam('year', null, true);
        }
        if (month) {
            setUrlParam('month', month, true);
        } else {
            setUrlParam('month', null, true);
        }
        
        // Update page title based on type and filters
        const titleEl = document.getElementById('expenses-page-title');
        if (titleEl) {
            let title = typeFilter === 'revenue' ? '📥 Przychody (IP Box)' : 
                        typeFilter === 'all' ? '📊 Wszystkie faktury' : '📤 Wydatki B+R';
            if (year && month) {
                const monthNames = ['', 'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 
                                   'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'];
                title += ` - ${monthNames[parseInt(month)]} ${year}`;
            } else if (year) {
                title += ` - ${year}`;
            }
            titleEl.textContent = title;
        }
        
        let items = [];
        
        // Load expenses
        if (typeFilter === 'expense' || typeFilter === 'all') {
            let expUrl = `/expenses/?limit=500`;
            if (year) expUrl += `&year=${year}`;
            if (month) expUrl += `&month=${month}`;
            if (projectFilter) expUrl += `&project_id=${projectFilter}`;
            if (status) expUrl += `&status=${status}`;
            if (brQualified) expUrl += `&br_qualified=${brQualified}`;
            const expenses = await apiCall(expUrl);
            items = items.concat(expenses.map(e => ({...e, type: 'expense'})));
        }
        
        // Load revenues
        if (typeFilter === 'revenue' || typeFilter === 'all') {
            let revUrl = `/expenses/revenues/`;
            if (projectFilter) revUrl += `?project_id=${projectFilter}`;
            const revenues = await apiCall(revUrl);
            items = items.concat(revenues.map(r => ({...r, type: 'revenue'})));
        }
        
        // Sort by date descending
        items.sort((a, b) => (b.invoice_date || '').localeCompare(a.invoice_date || ''));
        
        // Detect duplicate invoice numbers
        const invoiceCounts = {};
        items.forEach(e => {
            const inv = (e.invoice_number || '').toLowerCase().trim();
            if (inv && inv !== '-') {
                invoiceCounts[inv] = (invoiceCounts[inv] || 0) + 1;
            }
        });
        
        selectedExpenses.clear();
        updateBulkActionsBar();
        
        const isRevenue = typeFilter === 'revenue';
        const emptyMsg = isRevenue ? 'Brak przychodów' : typeFilter === 'all' ? 'Brak faktur' : 'Brak wydatków';
        
        document.getElementById('expenses-table-body').innerHTML = items.length === 0 ? 
            `<tr><td colspan="10" class="empty-state">${emptyMsg}</td></tr>` :
            items.map(e => {
                const isRev = e.type === 'revenue';
                const typeIcon = isRev ? '📥' : '📤';
                const partyName = isRev ? (e.client_name || '-') : (e.vendor_name || '-');
                const categoryDisplay = isRev ? 
                    (e.ip_qualified ? '✅ IP Box' : '⏳ Do klasyfikacji') :
                    (getCategoryName(e.br_category) || '-');
                
                // Check if invoice number is duplicate
                const invKey = (e.invoice_number || '').toLowerCase().trim();
                const isDuplicate = invKey && invKey !== '-' && invoiceCounts[invKey] > 1;
                const duplicateClass = isDuplicate ? 'duplicate-invoice' : '';
                const duplicateTitle = isDuplicate ? `title="⚠️ Duplikat (${invoiceCounts[invKey]}x)"` : '';
                
                return `<tr class="${isRev ? 'revenue-row' : 'expense-row'} ${duplicateClass}">
                    <td><input type="checkbox" class="expense-checkbox" data-id="${e.id}" data-type="${e.type}" onchange="toggleExpenseSelection('${e.id}', this.checked)"></td>
                    <td><span class="project-tag">${getProjectName(e.project_id)}</span></td>
                    <td>${typeIcon} ${e.invoice_date || '-'}</td>
                    <td ${duplicateTitle} class="${duplicateClass}">${isDuplicate ? '⚠️ ' : ''}${e.invoice_number || '-'}</td>
                    <td>${partyName}</td>
                    <td class="${isRev ? 'amount-revenue' : ''}">${formatCurrencyWithCode(e.gross_amount, e.currency)}</td>
                    <td>${categoryDisplay}</td>
                    <td>
                        ${isRev ? `
                            <button class="btn btn-small ${e.ip_qualified ? 'btn-success' : 'btn-warning'}" 
                                    onclick="classifyRevenue('${e.id}', ${!e.ip_qualified})">
                                ${e.ip_qualified ? '✅ IP Box' : '📋 Klasyfikuj'}
                            </button>
                        ` : `
                            <select class="status-select status-${e.status}" onchange="changeExpenseStatus('${e.id}', this.value)">
                                <option value="draft" ${e.status === 'draft' ? 'selected' : ''}>Szkic</option>
                                <option value="classified" ${e.status === 'classified' ? 'selected' : ''}>Sklasyfikowany</option>
                                <option value="approved" ${e.status === 'approved' ? 'selected' : ''}>Zatwierdzony</option>
                                <option value="rejected" ${e.status === 'rejected' ? 'selected' : ''}>Odrzucony</option>
                            </select>
                        `}
                    </td>
                    <td>
                        ${e.document_id ? `<button class="btn btn-small btn-outline" onclick="showDocumentDetail('${e.document_id}')" title="Pokaż dokument">📄</button>` : ''}
                        <button class="btn btn-small btn-secondary" onclick="${isRev ? 'showRevenueDetails' : 'showExpenseDetails'}('${e.id}')">Szczegóły</button>
                        ${!isRev ? `<button class="btn btn-small btn-primary" onclick="convertToRevenue('${e.id}')" title="Oznacz jako przychód">📥</button>` : 
                                   `<button class="btn btn-small btn-warning" onclick="convertToExpense('${e.id}')" title="Oznacz jako wydatek">📤</button>`}
                        <button class="btn btn-small btn-danger" onclick="${isRev ? 'deleteRevenue' : 'deleteExpense'}('${e.id}')" title="Usuń">🗑️</button>
                    </td>
                </tr>`;
            }).join('');
    } catch (e) { console.error('Error:', e); }
}

async function classifyRevenue(revenueId, ipQualified) {
    try {
        await apiCall(`/expenses/revenues/${revenueId}/classify`, {
            method: 'PUT',
            body: JSON.stringify({ ip_qualified: ipQualified, ip_category: 'software_license' })
        });
        showToast(ipQualified ? 'Przychód oznaczony jako IP Box' : 'Klasyfikacja usunięta', 'success');
        loadExpenses();
    } catch (e) {
        showToast('Błąd klasyfikacji', 'error');
    }
}

async function showRevenueDetails(revenueId) {
    // For now, show basic info - can be expanded later
    showToast('Szczegóły przychodu - do implementacji', 'info');
}

async function deleteRevenue(revenueId) {
    if (!confirm('Czy na pewno chcesz usunąć ten przychód?')) return;
    showToast('Usuwanie przychodów - do implementacji', 'info');
}

async function convertToRevenue(expenseId) {
    if (!confirm('Czy na pewno chcesz przekształcić ten wydatek w przychód?')) return;
    
    try {
        const result = await apiCall(`/expenses/invoices/${expenseId}/reclassify?from_type=expense&to_type=revenue&reason=manual_conversion`, {
            method: 'POST'
        });
        
        if (result.success) {
            showToast(`Przekształcono w przychód (ID: ${result.new_id})`, 'success');
            loadExpenses();
        } else {
            showToast(result.error || 'Błąd konwersji', 'error');
        }
    } catch (e) {
        console.error('Error converting to revenue:', e);
        showToast('Błąd przekształcania w przychód', 'error');
    }
}

async function convertToExpense(revenueId) {
    if (!confirm('Czy na pewno chcesz przekształcić ten przychód w wydatek?')) return;
    
    try {
        const result = await apiCall(`/expenses/invoices/${revenueId}/reclassify?from_type=revenue&to_type=expense&reason=manual_conversion`, {
            method: 'POST'
        });
        
        if (result.success) {
            showToast(`Przekształcono w wydatek (ID: ${result.new_id})`, 'success');
            loadExpenses();
        } else {
            showToast(result.error || 'Błąd konwersji', 'error');
        }
    } catch (e) {
        console.error('Error converting to expense:', e);
        showToast('Błąd przekształcania w wydatek', 'error');
    }
}

// Bulk selection functions
function toggleExpenseSelection(id, checked) {
    if (checked) {
        selectedExpenses.add(id);
    } else {
        selectedExpenses.delete(id);
    }
    updateBulkActionsBar();
}

function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.expense-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
        if (checkbox.checked) {
            selectedExpenses.add(cb.dataset.id);
        } else {
            selectedExpenses.delete(cb.dataset.id);
        }
    });
    updateBulkActionsBar();
}

function updateBulkActionsBar() {
    const bar = document.getElementById('bulk-actions-bar');
    const count = document.getElementById('selected-count');
    if (selectedExpenses.size > 0) {
        bar.style.display = 'flex';
        count.textContent = `${selectedExpenses.size} zaznaczonych`;
    } else {
        bar.style.display = 'none';
    }
}

function clearSelection() {
    selectedExpenses.clear();
    document.querySelectorAll('.expense-checkbox').forEach(cb => cb.checked = false);
    document.getElementById('select-all-expenses').checked = false;
    updateBulkActionsBar();
}

async function bulkAssignToProject() {
    const projectId = document.getElementById('bulk-assign-project').value;
    if (!projectId) {
        showToast('Wybierz projekt', 'warning');
        return;
    }
    if (selectedExpenses.size === 0) {
        showToast('Zaznacz wydatki', 'warning');
        return;
    }
    
    try {
        await apiCall('/projects/bulk-assign-expenses', {
            method: 'POST',
            body: JSON.stringify({
                expense_ids: Array.from(selectedExpenses),
                project_id: projectId
            })
        });
        showToast(`Przypisano ${selectedExpenses.size} wydatków do projektu`, 'success');
        clearSelection();
        loadExpenses();
    } catch (e) {
        showToast('Błąd przypisywania', 'error');
    }
}

async function showExpenseDetails(id) {
    try {
        const e = await apiCall(`/expenses/${id}`);
        document.getElementById('expense-modal-content').innerHTML = `
            <p><strong>Nr faktury:</strong> ${e.invoice_number || '-'}</p>
            <p><strong>Data:</strong> ${e.invoice_date || '-'}</p>
            <p><strong>Dostawca:</strong> ${e.vendor_name || '-'} (NIP: ${e.vendor_nip || '-'})</p>
            <p><strong>Kwota brutto:</strong> ${formatCurrencyWithCode(e.gross_amount, e.currency)}</p>
            <p><strong>Kwota netto:</strong> ${formatCurrencyWithCode(e.net_amount, e.currency)}</p>
            <p><strong>VAT:</strong> ${formatCurrencyWithCode(e.vat_amount, e.currency)}</p>
            ${e.document_id ? `<p><strong>Dokument źródłowy:</strong> <a href="#" onclick="showDocumentDetail('${e.document_id}'); return false;">📄 Zobacz dokument</a></p>` : ''}
            <hr><h4>Klasyfikacja B+R</h4>
            <p><strong>Kwalifikowany:</strong> ${e.br_qualified ? '✅ Tak' : '❌ Nie'}</p>
            <p><strong>Kategoria:</strong> ${getCategoryName(e.br_category) || '-'}</p>
            <p><strong>Stawka:</strong> ${e.br_deduction_rate * 100}%</p>
            <p><strong>Uzasadnienie:</strong> ${e.br_qualification_reason || '-'}</p>
            <p><strong>Status:</strong> 
                <select id="expense-status-select" class="status-select">
                    <option value="draft" ${e.status === 'draft' ? 'selected' : ''}>Szkic</option>
                    <option value="classified" ${e.status === 'classified' ? 'selected' : ''}>Sklasyfikowany</option>
                    <option value="approved" ${e.status === 'approved' ? 'selected' : ''}>Zatwierdzony</option>
                    <option value="rejected" ${e.status === 'rejected' ? 'selected' : ''}>Odrzucony</option>
                </select>
            </p>
            <div style="margin-top:1rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
                <button class="btn btn-primary" onclick="classifyExpense('${e.id}')">Zmień klasyfikację</button>
                <button class="btn btn-secondary" onclick="reclassifyWithLLM('${e.id}')">Reklasyfikuj AI</button>
                <button class="btn btn-success" onclick="saveExpenseStatus('${e.id}')">💾 Zapisz status</button>
                <button class="btn btn-warning" onclick="generateExpenseDoc('${e.id}')">📝 Generuj dokumentację</button>
                <button class="btn btn-danger" onclick="deleteExpense('${e.id}')">🗑️ Usuń</button>
            </div>`;
        document.getElementById('expense-modal').classList.add('active');
    } catch (e) { showToast('Błąd', 'error'); }
}

async function classifyExpense(id) {
    const cat = prompt('Kategoria B+R (personnel_employment, materials, equipment, depreciation, expertise, external_services):');
    if (!cat) return;
    const qualified = confirm('Czy kwalifikuje się do B+R?');
    try {
        await apiCall(`/expenses/${id}/classify`, { method: 'PUT', body: JSON.stringify({ br_qualified: qualified, br_category: cat, br_deduction_rate: cat.startsWith('personnel') ? 2.0 : 1.0 }) });
        showToast('Zapisano', 'success');
        document.getElementById('expense-modal').classList.remove('active');
        loadExpenses(); loadDashboard();
    } catch (e) { showToast('Błąd', 'error'); }
}

async function reclassifyWithLLM(id) {
    try { await apiCall(`/expenses/${id}/auto-classify`, { method: 'POST' }); showToast('Zlecono', 'success'); document.getElementById('expense-modal').classList.remove('active'); setTimeout(loadExpenses, 5000); }
    catch (e) { showToast('Błąd', 'error'); }
}

// Reports
async function loadReports() {
    const year = document.getElementById('report-year').value;
    currentFiscalYear = parseInt(year);
    const months = ['','Styczeń','Luty','Marzec','Kwiecień','Maj','Czerwiec','Lipiec','Sierpień','Wrzesień','Październik','Listopad','Grudzień'];
    
    try {
        // Load annual B+R summary
        const br = await apiCall(`/reports/annual/br-summary?fiscal_year=${year}&project_id=${PROJECT_ID}`);
        document.getElementById('annual-br-summary').innerHTML = `
            <p><strong>Projekt:</strong> ${br.project_name}</p>
            <p><strong>Suma kosztów B+R:</strong> ${formatCurrency(br.total_br_costs)}</p>
            <p><strong>Kwota odliczenia:</strong> <span style="color:var(--success);font-size:1.25rem">${formatCurrency(br.total_br_deduction)}</span></p>`;
        
        // Load annual IP Box summary
        const ip = await apiCall(`/reports/annual/ip-box-summary?fiscal_year=${year}&project_id=${PROJECT_ID}`);
        document.getElementById('annual-ip-summary').innerHTML = `
            <p><strong>Przychody IP:</strong> ${formatCurrency(ip.ip_revenues)}</p>
            <p><strong>Wskaźnik nexus:</strong> ${(ip.nexus_ratio * 100).toFixed(2)}%</p>
            <p><strong>Podatek 5%:</strong> <span style="color:var(--success);font-size:1.25rem">${formatCurrency(ip.tax_5_percent)}</span></p>`;
        
        // Load detailed monthly data
        const monthlyData = await loadMonthlyDetails(year);
        
        // Render monthly table
        let totalExpenses = 0, totalBr = 0, totalRevenues = 0, totalIp = 0;
        let nexusSum = 0, nexusCount = 0;
        
        const tbody = document.getElementById('monthly-reports-body');
        if (monthlyData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Brak danych za wybrany rok</td></tr>';
        } else {
            tbody.innerHTML = monthlyData.map(m => {
                totalExpenses += m.expenses || 0;
                totalBr += m.br_qualified || 0;
                totalRevenues += m.revenues || 0;
                totalIp += m.ip_qualified || 0;
                if (m.nexus_ratio > 0) { nexusSum += m.nexus_ratio; nexusCount++; }
                
                return `<tr>
                    <td><strong>${months[m.month]}</strong></td>
                    <td>${formatCurrency(m.expenses || 0)}</td>
                    <td class="br-qualified">${formatCurrency(m.br_qualified || 0)}</td>
                    <td class="revenue">${formatCurrency(m.revenues || 0)}</td>
                    <td class="ip-qualified">${formatCurrency(m.ip_qualified || 0)}</td>
                    <td>${m.nexus_ratio ? (m.nexus_ratio * 100).toFixed(1) + '%' : '-'}</td>
                    <td>
                        <button class="btn btn-small btn-primary" onclick="viewMonthExpenses(${year}, ${m.month})" title="Wydatki miesiąca">💰</button>
                        <button class="btn btn-small btn-outline" onclick="showMonthDetails(${year}, ${m.month})" title="Szczegóły">📋</button>
                        <button class="btn btn-small btn-secondary" onclick="regenerateMonthReport(${year}, ${m.month})" title="Regeneruj">🔄</button>
                    </td>
                </tr>`;
            }).join('');
        }
        
        // Update totals
        document.getElementById('total-expenses').textContent = formatCurrency(totalExpenses);
        document.getElementById('total-br').textContent = formatCurrency(totalBr);
        document.getElementById('total-revenues').textContent = formatCurrency(totalRevenues);
        document.getElementById('total-ip').textContent = formatCurrency(totalIp);
        document.getElementById('avg-nexus').textContent = nexusCount > 0 ? ((nexusSum / nexusCount) * 100).toFixed(1) + '%' : '-';
        
    } catch (e) { console.error('Error loading reports:', e); }
}

async function loadMonthlyDetails(year) {
    try {
        // Get expenses and revenues grouped by month
        const [expenses, revenues] = await Promise.all([
            apiCall(`/expenses/?year=${year}&limit=500`),
            apiCall(`/expenses/revenues/`)
        ]);
        
        // Group by month
        const monthlyMap = {};
        for (let m = 1; m <= 12; m++) {
            monthlyMap[m] = { month: m, expenses: 0, br_qualified: 0, revenues: 0, ip_qualified: 0, nexus_ratio: 0 };
        }
        
        // Process expenses
        expenses.forEach(e => {
            if (!e.invoice_date) return;
            const date = new Date(e.invoice_date);
            if (date.getFullYear() !== parseInt(year)) return;
            const month = date.getMonth() + 1;
            monthlyMap[month].expenses += e.gross_amount || 0;
            if (e.br_qualified) {
                monthlyMap[month].br_qualified += (e.gross_amount || 0) * (e.br_deduction_rate || 1);
            }
        });
        
        // Process revenues
        revenues.forEach(r => {
            if (!r.invoice_date) return;
            const date = new Date(r.invoice_date);
            if (date.getFullYear() !== parseInt(year)) return;
            const month = date.getMonth() + 1;
            monthlyMap[month].revenues += r.gross_amount || 0;
            if (r.ip_qualified) {
                monthlyMap[month].ip_qualified += r.gross_amount || 0;
            }
        });
        
        // Calculate nexus ratio per month (simplified)
        Object.values(monthlyMap).forEach(m => {
            if (m.br_qualified > 0 && m.expenses > 0) {
                m.nexus_ratio = Math.min(1, m.br_qualified / m.expenses);
            }
        });
        
        // Return only months with data
        return Object.values(monthlyMap).filter(m => m.expenses > 0 || m.revenues > 0);
    } catch (e) {
        console.error('Error loading monthly details:', e);
        return [];
    }
}

function viewMonthExpenses(year, month) {
    // Navigate to expenses page with year/month filter
    navigateTo('expenses');
    // Set URL params and update filters after navigation
    setTimeout(() => {
        const yearSelect = document.getElementById('expense-filter-year');
        const monthSelect = document.getElementById('expense-filter-month');
        if (yearSelect) yearSelect.value = year.toString();
        if (monthSelect) monthSelect.value = month.toString();
        // Update URL
        const url = new URL(window.location);
        url.searchParams.set('page', 'expenses');
        url.searchParams.set('year', year);
        url.searchParams.set('month', month);
        history.pushState({}, '', url);
        loadExpenses();
    }, 100);
}

async function showMonthDetails(year, month) {
    const months = ['','Styczeń','Luty','Marzec','Kwiecień','Maj','Czerwiec','Lipiec','Sierpień','Wrzesień','Październik','Listopad','Grudzień'];
    
    document.getElementById('month-detail-card').style.display = 'block';
    document.getElementById('month-detail-title').textContent = `📋 Szczegóły: ${months[month]} ${year}`;
    
    const content = document.getElementById('month-detail-content');
    content.innerHTML = '<p class="loading">Ładowanie...</p>';
    
    try {
        const [expenses, revenues] = await Promise.all([
            apiCall(`/expenses/?year=${year}&month=${month}&limit=100`),
            apiCall(`/expenses/revenues/`)
        ]);
        
        // Filter revenues by month
        const monthRevenues = revenues.filter(r => {
            if (!r.invoice_date) return false;
            const d = new Date(r.invoice_date);
            return d.getFullYear() === year && d.getMonth() + 1 === month;
        });
        
        let html = '';
        
        // Expenses table
        if (expenses.length > 0) {
            html += `<h4>📤 Wydatki (${expenses.length})</h4>
            <table class="data-table compact">
                <thead><tr><th>Data</th><th>Nr faktury</th><th>Dostawca</th><th>Kwota</th><th>Kategoria B+R</th><th>Status</th></tr></thead>
                <tbody>
                ${expenses.map(e => `<tr class="${e.br_qualified ? 'br-row' : ''}">
                    <td>${e.invoice_date || '-'}</td>
                    <td>${e.invoice_number || '-'}</td>
                    <td>${e.vendor_name || e.vendor_nip || '-'}</td>
                    <td>${formatCurrency(e.gross_amount)}</td>
                    <td>${e.br_category || '-'}</td>
                    <td>${e.br_qualified ? '✅ B+R' : '⏳'}</td>
                </tr>`).join('')}
                </tbody>
            </table>`;
        }
        
        // Revenues table
        if (monthRevenues.length > 0) {
            html += `<h4>📥 Przychody (${monthRevenues.length})</h4>
            <table class="data-table compact">
                <thead><tr><th>Data</th><th>Nr faktury</th><th>Klient</th><th>Kwota</th><th>Kategoria IP</th><th>Status</th></tr></thead>
                <tbody>
                ${monthRevenues.map(r => `<tr class="${r.ip_qualified ? 'ip-row' : ''}">
                    <td>${r.invoice_date || '-'}</td>
                    <td>${r.invoice_number || '-'}</td>
                    <td>${r.client_name || r.client_nip || '-'}</td>
                    <td>${formatCurrency(r.gross_amount)}</td>
                    <td>${r.ip_category || '-'}</td>
                    <td>${r.ip_qualified ? '✅ IP Box' : '⏳'}</td>
                </tr>`).join('')}
                </tbody>
            </table>`;
        }
        
        if (!html) {
            html = '<p class="empty-state">Brak danych za ten miesiąc</p>';
        }
        
        content.innerHTML = html;
        
    } catch (e) {
        content.innerHTML = `<p class="error">Błąd ładowania: ${e.message}</p>`;
    }
}

async function regenerateMonthReport(year, month) {
    try {
        showToast(`Regenerowanie raportu ${month}/${year}...`, 'info');
        await apiCall('/reports/monthly/generate', { 
            method: 'POST', 
            body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: year, month: month, regenerate: true, preprocess: true }) 
        });
        showToast('Zregenerowano', 'success');
        loadReports(); loadDashboard();
    } catch (e) { showToast('Błąd regenerowania raportu', 'error'); }
}

async function regenerateAllMonthlyReports() {
    const confirmed = await openConfirmModal({
        title: 'Regeneruj raporty',
        message: 'Czy na pewno chcesz zregenerować raporty dla wszystkich miesięcy?',
        confirmText: 'Regeneruj'
    });
    if (!confirmed) return;
    
    const year = document.getElementById('report-year').value;
    showToast('Regenerowanie wszystkich raportów...', 'info');
    
    let success = 0, errors = 0;
    for (let m = 1; m <= 12; m++) {
        try {
            await apiCall('/reports/monthly/generate', { 
                method: 'POST', 
                body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: parseInt(year), month: m, regenerate: true, preprocess: true }) 
            });
            success++;
        } catch (e) { errors++; }
    }
    
    showToast(`Zregenerowano ${success} raportów${errors > 0 ? `, ${errors} błędów` : ''}`, success > 0 ? 'success' : 'error');
    loadReports();
}

async function generateMonthlyReport() {
    const year = document.getElementById('report-year').value;
    const month = prompt('Miesiąc (1-12):');
    if (!month || month < 1 || month > 12) { showToast('Nieprawidłowy miesiąc', 'error'); return; }
    try { await apiCall('/reports/monthly/generate', { method: 'POST', body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: parseInt(year), month: parseInt(month), regenerate: true, preprocess: true }) }); showToast('Wygenerowano', 'success'); loadReports(); }
    catch (e) { showToast('Błąd', 'error'); }
}

async function generateAllReports() {
    for (let m = 1; m <= new Date().getMonth() + 1; m++) {
        try { await apiCall('/reports/monthly/generate', { method: 'POST', body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: currentFiscalYear, month: m, regenerate: false, preprocess: true }) }); }
        catch (e) { console.error(e); }
    }
    showToast('Wygenerowano raporty', 'success'); loadDashboard();
}

// Clarifications
async function loadClarifications() {
    try {
        const unanswered = document.getElementById('show-unanswered').checked;
        const clarifications = await apiCall(`/clarifications/?limit=50${unanswered ? '&unanswered_only=true' : ''}`);
        document.getElementById('clarifications-list').innerHTML = clarifications.length === 0 ? '<p class="empty-state">Brak pytań</p>' :
            clarifications.map(c => `<div class="clarification-item card">
                <p><strong>Pytanie:</strong> ${c.question}</p>
                ${c.answer ? `<p><strong>Odpowiedź:</strong> ${c.answer}</p>` : `
                    <textarea id="answer-${c.id}" placeholder="Odpowiedź..." rows="2" style="width:100%;margin-top:0.5rem"></textarea>
                    <button class="btn btn-primary btn-small" onclick="answerClarification('${c.id}')" style="margin-top:0.5rem">Odpowiedz</button>`}
            </div>`).join('');
        document.getElementById('clarification-badge').textContent = clarifications.filter(c => !c.answer).length;
    } catch (e) { console.error('Error:', e); }
}

async function answerClarification(id) {
    const answer = document.getElementById(`answer-${id}`).value;
    if (!answer.trim()) { showToast('Wprowadź odpowiedź', 'warning'); return; }
    try { await apiCall(`/clarifications/${id}/answer`, { method: 'PUT', body: JSON.stringify({ answer }) }); showToast('Zapisano', 'success'); loadClarifications(); }
    catch (e) { showToast('Błąd', 'error'); }
}

document.getElementById('show-unanswered').addEventListener('change', loadClarifications);

// Settings
function saveProjectSettings() {
    document.getElementById('active-project').textContent = document.getElementById('setting-project-name').value;
    document.getElementById('fiscal-year').textContent = document.getElementById('setting-fiscal-year').value;
    currentFiscalYear = parseInt(document.getElementById('setting-fiscal-year').value);
    showToast('Zapisano', 'success');
}

// Utilities
function formatCurrency(amount) { return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(amount || 0); }
function formatCurrencyWithCode(amount, currency = 'PLN') {
    const cur = (currency || 'PLN').toUpperCase();
    try {
        return new Intl.NumberFormat('pl-PL', { style: 'currency', currency: cur }).format(amount || 0);
    } catch (e) {
        return `${(amount || 0).toFixed(2)} ${cur}`;
    }
}
function getStatusLabel(s) { return { pending: 'Oczekuje', processing: 'Przetwarzanie', completed: 'Gotowe', failed: 'Błąd', draft: 'Szkic', classified: 'Sklasyfikowane', approved: 'Zatwierdzony', rejected: 'Odrzucony', generated: 'Wygenerowany' }[s] || s; }
function getCategoryName(c) { return { personnel_employment: 'Wynagrodzenia (umowa o pracę)', personnel_civil: 'Wynagrodzenia (cywilnoprawne)', materials: 'Materiały', equipment: 'Sprzęt', depreciation: 'Amortyzacja', expertise: 'Ekspertyzy', external_services: 'Usługi zewnętrzne' }[c] || c; }
function showToast(msg, type = 'info') { const t = document.createElement('div'); t.className = `toast ${type}`; t.textContent = msg; document.getElementById('toast-container').appendChild(t); setTimeout(() => t.remove(), 4000); }

// Expense management functions
async function changeExpenseStatus(id, status) {
    try {
        await apiCall(`/expenses/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) });
        showToast('Status zmieniony', 'success');
    } catch (e) { showToast('Błąd zmiany statusu', 'error'); loadExpenses(); }
}

async function saveExpenseStatus(id) {
    const status = document.getElementById('expense-status-select').value;
    try {
        await apiCall(`/expenses/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) });
        showToast('Status zapisany', 'success');
        document.getElementById('expense-modal').classList.remove('active');
        loadExpenses();
    } catch (e) { showToast('Błąd zapisu statusu', 'error'); }
}

window.deleteExpense = async function(id) {
    const confirmed = await openConfirmModal({
        title: 'Usuń wydatek',
        message: 'Czy na pewno chcesz usunąć ten wydatek?',
        confirmText: 'Usuń'
    });
    if (!confirmed) return;
    
    try {
        await apiCall(`/expenses/${id}`, { method: 'DELETE' });
        showToast('Wydatek usunięty', 'success');
        const modal = document.getElementById('expense-modal');
        if (modal) modal.classList.remove('active');
        loadExpenses();
        loadDashboard();
    } catch (e) {
        showToast('Błąd usuwania', 'error');
    }
};

// Document duplicate check and re-extract
async function checkDuplicates(docId) {
    try {
        const result = await apiCall(`/documents/${docId}/check-duplicates`);
        const container = document.getElementById('duplicate-check-result');
        
        if (result.potential_duplicates && result.potential_duplicates.length > 0) {
            container.innerHTML = `
                <div class="doc-detail-section warning-section" style="background:#fef3c7; padding:1rem; border-radius:8px; margin:1rem 0;">
                    <h4 style="color:#92400e;">⚠️ Potencjalne duplikaty (${result.potential_duplicates.length})</h4>
                    <ul style="margin:0.5rem 0; padding-left:1.5rem;">
                        ${result.potential_duplicates.map(d => `
                            <li style="margin:0.25rem 0;">
                                <a href="#" onclick="showDocumentDetail('${d.id}'); return false;">${d.filename}</a>
                                <small style="color:#92400e;"> - ${d.match_reason}</small>
                            </li>
                        `).join('')}
                    </ul>
                </div>`;
            showToast('Znaleziono potencjalne duplikaty', 'warning');
        } else {
            container.innerHTML = `
                <div class="doc-detail-section" style="background:#dcfce7; padding:1rem; border-radius:8px; margin:1rem 0;">
                    <p style="color:#166534; margin:0;">✅ Nie znaleziono duplikatów</p>
                </div>`;
            showToast('Brak duplikatów', 'success');
        }
    } catch (e) { 
        showToast('Błąd sprawdzania duplikatów', 'error'); 
        console.error(e);
    }
}

async function reExtractData(docId) {
    try {
        showToast('Wyodrębnianie danych...', 'info');
        const result = await apiCall(`/documents/${docId}/re-extract`, { method: 'POST' });
        showToast(`Dane wyodrębnione (typ: ${result.detected_type})`, 'success');
        // Refresh the document detail view
        showDocumentDetail(docId, { updateUrl: false });
    } catch (e) { 
        showToast('Błąd wyodrębniania danych', 'error'); 
        console.error(e);
    }
}

let selectedOcrEngine = 'paddleocr';

function updateOcrEngine(engine) {
    selectedOcrEngine = engine;
    showToast(`Silnik OCR zmieniony na: ${engine}`, 'info');
}

async function fillFieldsWithLLM(docId) {
    if (!currentDocData || !currentDocData.ocr_text) {
        showToast('Brak tekstu OCR do analizy', 'error');
        return;
    }
    
    try {
        showToast('Analizowanie tekstu za pomocą AI...', 'info');
        
        const result = await apiCall(`/documents/${docId}/llm-extract`, {
            method: 'POST',
            body: JSON.stringify({
                ocr_text: currentDocData.ocr_text,
                current_data: normalizeExtractedData(currentDocData.extracted_data || {})
            })
        });
        
        if (result.status === 'success' && result.extracted_fields) {
            // Update the form fields with LLM results
            const fields = result.extracted_fields;
            let filledCount = 0;
            
            for (const [field, value] of Object.entries(fields)) {
                if (value) {
                    const input = document.getElementById(`edit-${field}`);
                    if (input && (!input.value || input.value === '' || input.value === 'faktury' || input.value === 'sprzedazy')) {
                        input.value = value;
                        filledCount++;
                    }
                }
            }
            
            // Switch to edit mode to show filled fields
            const editDiv = document.getElementById('extracted-data-edit');
            const viewDiv = document.getElementById('extracted-data-view');
            if (editDiv && viewDiv) {
                viewDiv.style.display = 'none';
                editDiv.style.display = 'block';
            }
            
            showToast(`AI uzupełniło ${filledCount} pól. Sprawdź i zapisz.`, 'success');
        } else {
            showToast('AI nie znalazło dodatkowych danych', 'warning');
        }
    } catch (e) {
        console.error('LLM extraction error:', e);
        showToast('Błąd analizy AI', 'error');
    }
}

// Documentation generation
async function generateExpenseDoc(expenseId) {
    try {
        showToast('Generowanie dokumentacji...', 'info');
        const result = await apiCall(`/expenses/${expenseId}/generate-doc`, { method: 'POST' });
        
        if (result.status === 'success') {
            showToast('Dokumentacja wygenerowana!', 'success');
            // Show link to file
            const filename = result.file_path.split('/').pop();
            alert(`Dokumentacja zapisana:\n${filename}\n\nŚcieżka: ${result.file_path}`);
        } else {
            showToast('Błąd generowania dokumentacji', 'error');
        }
    } catch (e) { 
        showToast('Błąd generowania dokumentacji', 'error'); 
        console.error(e);
    }
}

async function generateProjectSummary(projectId) {
    try {
        showToast('Generowanie podsumowania projektu...', 'info');
        const result = await apiCall(`/expenses/project/${projectId}/generate-summary`, { method: 'POST' });
        
        if (result.status === 'success') {
            showToast(`Podsumowanie wygenerowane!`, 'success');
            // Refresh projects to show updated totals
            loadProjects();
            // Show documentation viewer
            viewProjectDocs(projectId);
        } else {
            showToast('Błąd generowania podsumowania', 'error');
        }
    } catch (e) { 
        showToast('Błąd generowania podsumowania', 'error'); 
        console.error(e);
    }
}

async function regenerateAllReports() {
    if (!confirm('Czy na pewno chcesz wygenerować raporty dla wszystkich projektów?')) return;
    
    try {
        showToast('Regenerowanie raportów...', 'info');
        const projects = await apiCall('/projects/');
        
        let successCount = 0;
        let errorCount = 0;
        
        for (const project of projects) {
            try {
                await apiCall(`/expenses/project/${project.id}/generate-summary`, { method: 'POST' });
                successCount++;
            } catch (e) {
                console.error(`Error generating report for project ${project.id}:`, e);
                errorCount++;
            }
        }
        
        if (errorCount === 0) {
            showToast(`Wygenerowano ${successCount} raportów`, 'success');
        } else {
            showToast(`Wygenerowano ${successCount} raportów, ${errorCount} błędów`, 'warning');
        }
        
        loadProjects();
    } catch (e) {
        showToast('Błąd regenerowania raportów', 'error');
        console.error(e);
    }
}

// Documentation viewer
async function viewProjectDocs(projectId) {
    try {
        const result = await apiCall(`/expenses/project/${projectId}/docs`);
        const modal = document.getElementById('docs-modal');
        const content = document.getElementById('docs-modal-content');
        
        if (result.files.length === 0) {
            content.innerHTML = `
                <p class="empty-state">Brak wygenerowanych dokumentów dla tego projektu.</p>
                <button class="btn btn-primary" onclick="generateProjectSummary('${projectId}'); closeDocsModal();">
                    📝 Generuj dokumentację
                </button>`;
        } else {
            content.innerHTML = `
                <div class="docs-list">
                    ${result.files.map(f => `
                        <div class="doc-item" onclick="viewDocContent('${projectId}', '${f.filename}')">
                            <span class="doc-icon">📄</span>
                            <span class="doc-name">${f.filename}</span>
                            <span class="doc-size">${(f.size / 1024).toFixed(1)} KB</span>
                        </div>
                    `).join('')}
                </div>
                <div id="doc-preview" class="doc-preview"></div>
                <div class="docs-actions">
                    <button class="btn btn-primary" onclick="generateProjectSummary('${projectId}')">
                        🔄 Wygeneruj nowe podsumowanie
                    </button>
                </div>`;
            
            // Auto-load latest document
            if (result.files.length > 0) {
                viewDocContent(projectId, result.files[0].filename);
            }
        }
        
        modal.classList.add('active');
    } catch (e) { 
        showToast('Błąd ładowania dokumentacji', 'error'); 
        console.error(e);
    }
}

async function viewDocContent(projectId, filename) {
    try {
        const result = await apiCall(`/expenses/project/${projectId}/docs/${filename}`);
        const preview = document.getElementById('doc-preview');
        
        // Highlight selected doc
        document.querySelectorAll('.doc-item').forEach(d => d.classList.remove('active'));
        event?.target?.closest('.doc-item')?.classList.add('active');
        
        // Store content for copy/download
        currentDocContent = { projectId, filename, content: result.content };
        
        // Render markdown content
        preview.innerHTML = `
            <div class="doc-content-header">
                <strong>${filename}</strong>
                <div class="doc-actions">
                    <button class="btn btn-sm btn-secondary" onclick="copyDocToClipboard()" title="Kopiuj markdown">📋 Kopiuj</button>
                    <button class="btn btn-sm btn-secondary" onclick="downloadDocFile()" title="Pobierz plik .md">⬇️ MD</button>
                    <button class="btn btn-sm btn-primary" onclick="downloadPdf('${projectId}', '${filename}')">📄 PDF</button>
                    <button class="btn btn-sm btn-secondary" onclick="viewDocHistory('${projectId}', '${filename}')">📜 Historia</button>
                    <button class="btn btn-sm btn-secondary" onclick="printDoc()">🖨️ Drukuj</button>
                </div>
            </div>
            <div class="doc-markdown">${renderMarkdown(result.content)}</div>`;
    } catch (e) { 
        showToast('Błąd ładowania dokumentu', 'error'); 
    }
}

// Use MarkdownRenderer module (loaded from markdown-renderer.js)
function renderMarkdown(md) {
    return MarkdownRenderer.render(md);
}

let currentDocContent = null;

function copyDocToClipboard() {
    if (!currentDocContent) {
        showToast('Brak dokumentu do skopiowania', 'error');
        return;
    }
    navigator.clipboard.writeText(currentDocContent.content).then(() => {
        showToast('Markdown skopiowany do schowka', 'success');
    }).catch(err => {
        showToast('Błąd kopiowania', 'error');
        console.error('Copy failed:', err);
    });
}

function downloadDocFile() {
    if (!currentDocContent) {
        showToast('Brak dokumentu do pobrania', 'error');
        return;
    }
    const blob = new Blob([currentDocContent.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentDocContent.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Pobrano ${currentDocContent.filename}`, 'success');
}

function downloadPdf(projectId, filename) {
    // Download/view PDF
    window.open(`${API_BASE}/expenses/project/${projectId}/docs/${filename}/pdf`, '_blank');
}

async function viewDocHistory(projectId, filename) {
    try {
        const data = await apiCall(`/expenses/project/${projectId}/docs/${filename}/history`);
        const preview = document.getElementById('doc-preview');
        
        if (!data.history || data.history.length === 0) {
            preview.innerHTML = `
                <div class="doc-content-header">
                    <strong>📜 Historia: ${filename}</strong>
                    <button class="btn btn-sm btn-secondary" onclick="viewDocContent('${projectId}', '${filename}')">← Powrót</button>
                </div>
                <p class="empty-state">Brak historii zmian</p>`;
            return;
        }
        
        let historyHtml = data.history.map(h => `
            <div class="history-item" onclick="viewDocVersion('${projectId}', '${filename}', '${h.commit}')">
                <span class="history-commit">${h.commit}</span>
                <span class="history-date">${h.date}</span>
                <span class="history-message">${h.message}</span>
            </div>
        `).join('');
        
        preview.innerHTML = `
            <div class="doc-content-header">
                <strong>📜 Historia: ${filename}</strong>
                <button class="btn btn-sm btn-secondary" onclick="viewDocContent('${projectId}', '${filename}')">← Powrót</button>
            </div>
            <div class="history-list">${historyHtml}</div>`;
    } catch (e) {
        showToast('Błąd ładowania historii', 'error');
    }
}

async function viewDocVersion(projectId, filename, commit) {
    try {
        const data = await apiCall(`/expenses/project/${projectId}/docs/${filename}/version/${commit}`);
        const preview = document.getElementById('doc-preview');
        
        preview.innerHTML = `
            <div class="doc-content-header">
                <strong>Wersja: ${commit}</strong>
                <div class="doc-actions">
                    <button class="btn btn-sm btn-primary" onclick="compareDocs('${projectId}', '${filename}', '${commit}')">📊 Porównaj z aktualną</button>
                    <button class="btn btn-sm btn-secondary" onclick="viewDocHistory('${projectId}', '${filename}')">📜 Historia</button>
                    <button class="btn btn-sm btn-secondary" onclick="viewDocContent('${projectId}', '${filename}')">← Aktualna</button>
                </div>
            </div>
            <div class="doc-markdown version-preview">${renderMarkdown(data.content)}</div>`;
    } catch (e) {
        showToast('Błąd ładowania wersji', 'error');
    }
}

async function compareDocs(projectId, filename, oldCommit) {
    try {
        // Fetch old and current versions
        const [oldData, currentData] = await Promise.all([
            apiCall(`/expenses/project/${projectId}/docs/${filename}/version/${oldCommit}`),
            apiCall(`/expenses/project/${projectId}/docs/${filename}`)
        ]);
        
        const preview = document.getElementById('doc-preview');
        
        // Simple line-by-line diff
        const oldLines = oldData.content.split('\n');
        const newLines = currentData.content.split('\n');
        
        let diffHtml = '';
        const maxLines = Math.max(oldLines.length, newLines.length);
        
        for (let i = 0; i < maxLines; i++) {
            const oldLine = oldLines[i] || '';
            const newLine = newLines[i] || '';
            
            if (oldLine === newLine) {
                diffHtml += `<tr class="diff-same"><td class="diff-old">${escapeHtml(oldLine)}</td><td class="diff-new">${escapeHtml(newLine)}</td></tr>`;
            } else if (!oldLine && newLine) {
                diffHtml += `<tr class="diff-added"><td class="diff-old"></td><td class="diff-new diff-highlight-add">+ ${escapeHtml(newLine)}</td></tr>`;
            } else if (oldLine && !newLine) {
                diffHtml += `<tr class="diff-removed"><td class="diff-old diff-highlight-del">- ${escapeHtml(oldLine)}</td><td class="diff-new"></td></tr>`;
            } else {
                diffHtml += `<tr class="diff-changed"><td class="diff-old diff-highlight-del">${escapeHtml(oldLine)}</td><td class="diff-new diff-highlight-add">${escapeHtml(newLine)}</td></tr>`;
            }
        }
        
        preview.innerHTML = `
            <div class="doc-content-header">
                <strong>📊 Porównanie: ${oldCommit} → Aktualna</strong>
                <div class="doc-actions">
                    <button class="btn btn-sm btn-secondary" onclick="viewDocHistory('${projectId}', '${filename}')">📜 Historia</button>
                    <button class="btn btn-sm btn-secondary" onclick="viewDocContent('${projectId}', '${filename}')">← Aktualna</button>
                </div>
            </div>
            <div class="diff-legend">
                <span class="diff-legend-add">+ Dodane</span>
                <span class="diff-legend-del">- Usunięte</span>
                <span class="diff-legend-mod">~ Zmienione</span>
            </div>
            <div class="diff-container">
                <table class="diff-table">
                    <thead>
                        <tr>
                            <th>📁 Poprzednia wersja (${oldCommit})</th>
                            <th>📄 Aktualna wersja</th>
                        </tr>
                    </thead>
                    <tbody>${diffHtml}</tbody>
                </table>
            </div>`;
    } catch (e) {
        showToast('Błąd porównywania wersji', 'error');
        console.error(e);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function printDoc() {
    // Print the current document preview
    const content = document.querySelector('.doc-markdown').innerHTML;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Dokumentacja B+R</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #1e40af; border-bottom: 2px solid #1e40af; padding-bottom: 10px; }
                h2 { color: #1e40af; margin-top: 30px; }
                h3 { color: #374151; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th { background: #1e40af; color: white; padding: 10px; text-align: left; }
                td { border: 1px solid #e5e7eb; padding: 8px; }
                tr:nth-child(even) td { background: #f9fafb; }
                hr { border: none; border-top: 1px solid #e5e7eb; margin: 30px 0; }
                p { margin: 5px 0; }
                .spacer { height: 10px; }
                @media print { body { margin: 20px; } }
            </style>
        </head>
        <body>${content}</body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
}

function closeDocsModal() {
    document.getElementById('docs-modal').classList.remove('active');
}

// Modal
document.querySelector('.modal-close').addEventListener('click', () => document.getElementById('expense-modal').classList.remove('active'));
document.getElementById('expense-modal').addEventListener('click', (e) => { if (e.target.id === 'expense-modal') e.target.classList.remove('active'); });

// Filters
document.getElementById('expense-filter-status').addEventListener('change', loadExpenses);
document.getElementById('expense-filter-br').addEventListener('change', loadExpenses);
document.getElementById('report-year').addEventListener('change', loadReports);

// =============================================================================
// Timesheet
// =============================================================================

const TIME_SLOTS = [
    { id: 'morning', label: '8-12', hours: 4 },
    { id: 'afternoon', label: '12-16', hours: 4 },
    { id: 'evening', label: '16-20', hours: 4 },
    { id: 'night', label: '20-24', hours: 4 }
];

let timesheetData = {};
let workersCache = [];

async function initTimesheet() {
    // Populate month selector
    const monthSelect = document.getElementById('timesheet-month');
    const months = ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 
                    'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'];
    const currentMonth = new Date().getMonth();
    monthSelect.innerHTML = months.map((m, i) => 
        `<option value="${i + 1}" ${i === currentMonth ? 'selected' : ''}>${m}</option>`
    ).join('');
    
    // Load workers
    await loadWorkers();
    
    // Load contractors
    await loadContractors();
    
    // Load timesheet if worker selected
    const workerId = document.getElementById('timesheet-worker').value;
    if (workerId) {
        loadTimesheet();
    }
}

async function loadWorkers() {
    try {
        const workers = await apiCall('/timesheet/workers');
        workersCache = workers;
        
        const select = document.getElementById('timesheet-worker');
        select.innerHTML = '<option value="">Wybierz pracownika...</option>' +
            workers.map(w => `<option value="${w.id}">${w.name}${w.role ? ` (${w.role})` : ''}</option>`).join('');
    } catch (e) { console.error('Error loading workers:', e); }
}

async function loadContractors() {
    try {
        const contractors = await apiCall('/timesheet/contractors');
        const container = document.getElementById('contractors-list');
        
        if (contractors.length === 0) {
            container.innerHTML = '<p class="empty-state">Brak kooperantów</p>';
            return;
        }
        
        container.innerHTML = contractors.map(c => `
            <div class="contractor-item">
                <strong>${c.vendor_name}</strong>
                ${c.vendor_nip ? `<span class="nip">NIP: ${c.vendor_nip}</span>` : ''}
                <span class="amount">${formatCurrency(c.total_amount)} (${c.invoice_count} faktur)</span>
            </div>
        `).join('');
    } catch (e) { console.error('Error loading contractors:', e); }
}

async function loadTimesheet() {
    const workerId = document.getElementById('timesheet-worker').value;
    const month = document.getElementById('timesheet-month').value;
    const year = document.getElementById('timesheet-year').value;
    
    if (!workerId) {
        document.getElementById('timesheet-grid').innerHTML = 
            '<p class="empty-state">Wybierz pracownika, aby wyświetlić harmonogram</p>';
        return;
    }
    
    try {
        // Load projects and timesheet entries
        const [projects, entriesData] = await Promise.all([
            apiCall('/projects/'),
            apiCall(`/timesheet/entries?year=${year}&month=${month}&worker_id=${workerId}`)
        ]);
        
        // Build entries lookup
        timesheetData = {};
        for (const entry of entriesData.entries) {
            const key = `${entry.project_id}_${entry.work_date}_${entry.time_slot}`;
            timesheetData[key] = entry.hours;
        }
        
        // Get days in month
        const daysInMonth = new Date(year, month, 0).getDate();
        
        // Build grid HTML with checkboxes
        let html = '<table class="timesheet-table timesheet-checkbox">';
        
        // Header row with projects
        html += '<thead><tr><th>Dzień</th><th>Pora</th>';
        for (const p of projects) {
            html += `<th class="project-col" title="${p.name}">${p.name.substring(0, 12)}${p.name.length > 12 ? '..' : ''}</th>`;
        }
        html += '<th>Σ</th></tr></thead>';
        
        html += '<tbody>';
        
        // Rows for each day and time slot
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayOfWeek = new Date(year, month - 1, day).getDay();
            const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
            const dayNames = ['Nd', 'Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So'];
            
            // Calculate daily total (sum of all slots for this day)
            let dayTotal = 0;
            for (const slot of TIME_SLOTS) {
                for (const p of projects) {
                    const key = `${p.id}_${dateStr}_${slot.id}`;
                    dayTotal += timesheetData[key] || 0;
                }
            }
            
            for (let slotIdx = 0; slotIdx < TIME_SLOTS.length; slotIdx++) {
                const slot = TIME_SLOTS[slotIdx];
                const rowClass = isWeekend ? 'weekend' : '';
                
                html += `<tr class="${rowClass}" data-date="${dateStr}">`;
                
                // Day column (only on first slot)
                if (slotIdx === 0) {
                    html += `<td rowspan="${TIME_SLOTS.length}" class="day-cell ${isWeekend ? 'weekend' : ''}">${day} ${dayNames[dayOfWeek]}</td>`;
                }
                
                // Time slot
                html += `<td class="slot-cell">${slot.label}</td>`;
                
                // Project columns - CHECKBOXES
                for (const p of projects) {
                    const key = `${p.id}_${dateStr}_${slot.id}`;
                    const hours = timesheetData[key] || 0;
                    const checked = hours > 0;
                    
                    html += `<td class="check-cell">
                        <input type="checkbox" ${checked ? 'checked' : ''} 
                               data-project="${p.id}" data-date="${dateStr}" data-slot="${slot.id}"
                               onchange="toggleTimesheetBlock(this)" class="ts-checkbox">
                    </td>`;
                }
                
                // Daily total (only on first slot, spans all rows)
                if (slotIdx === 0) {
                    html += `<td rowspan="${TIME_SLOTS.length}" class="total-cell day-total" data-date="${dateStr}">${dayTotal > 0 ? dayTotal : ''}</td>`;
                }
                html += '</tr>';
            }
        }
        
        html += '</tbody></table>';
        
        document.getElementById('timesheet-grid').innerHTML = html;
        
        // Update summary
        updateTimesheetSummary(year, month);
        
    } catch (e) { 
        console.error('Error loading timesheet:', e);
        document.getElementById('timesheet-grid').innerHTML = '<p class="error">Błąd ładowania harmonogramu</p>';
    }
}

async function toggleTimesheetBlock(checkbox) {
    const workerId = document.getElementById('timesheet-worker').value;
    
    if (!workerId) {
        showToast('Wybierz pracownika', 'error');
        checkbox.checked = !checkbox.checked;
        return;
    }
    
    const hours = checkbox.checked ? 4 : 0;
    const dateStr = checkbox.dataset.date;
    const key = `${checkbox.dataset.project}_${dateStr}_${checkbox.dataset.slot}`;
    timesheetData[key] = hours;
    
    // Save immediately to database
    try {
        await apiCall('/timesheet/entries', {
            method: 'POST',
            body: JSON.stringify({
                project_id: checkbox.dataset.project,
                worker_id: workerId,
                work_date: checkbox.dataset.date,
                time_slot: checkbox.dataset.slot,
                hours: hours
            })
        });
        
        // Update daily total (sum all checkboxes for this date)
        const allCheckboxes = document.querySelectorAll(`.ts-checkbox[data-date="${dateStr}"]`);
        let dayTotal = 0;
        allCheckboxes.forEach(cb => { if (cb.checked) dayTotal += 4; });
        const dayTotalCell = document.querySelector(`.day-total[data-date="${dateStr}"]`);
        if (dayTotalCell) {
            dayTotalCell.textContent = dayTotal > 0 ? dayTotal : '';
        }
        
        // Update summary
        const year = document.getElementById('timesheet-year').value;
        const month = document.getElementById('timesheet-month').value;
        updateTimesheetSummary(year, month);
    } catch (e) {
        console.error('Error saving timesheet:', e);
        checkbox.checked = !checkbox.checked; // Revert
        showToast('Błąd zapisywania', 'error');
    }
}

function updateTimesheetCell(input) {
    const hours = parseFloat(input.value) || 0;
    const key = `${input.dataset.project}_${input.dataset.date}_${input.dataset.slot}`;
    timesheetData[key] = hours;
    
    input.classList.toggle('has-value', hours > 0);
    
    // Update row total
    const row = input.closest('tr');
    const inputs = row.querySelectorAll('.hours-input');
    let total = 0;
    inputs.forEach(i => total += parseFloat(i.value) || 0);
    row.querySelector('.total-cell').textContent = total > 0 ? total : '';
}

async function saveTimesheet() {
    const workerId = document.getElementById('timesheet-worker').value;
    if (!workerId) {
        showToast('Wybierz pracownika', 'warning');
        return;
    }
    
    // Collect all entries
    const entries = [];
    document.querySelectorAll('.hours-input').forEach(input => {
        const hours = parseFloat(input.value) || 0;
        if (hours > 0) {
            entries.push({
                project_id: input.dataset.project,
                worker_id: workerId,
                work_date: input.dataset.date,
                time_slot: input.dataset.slot,
                hours: hours
            });
        }
    });
    
    try {
        await apiCall('/timesheet/entries/batch', {
            method: 'POST',
            body: JSON.stringify(entries)
        });
        showToast(`Zapisano ${entries.length} wpisów`, 'success');
        
        // Update summary
        const year = document.getElementById('timesheet-year').value;
        const month = document.getElementById('timesheet-month').value;
        updateTimesheetSummary(year, month);
    } catch (e) {
        showToast('Błąd zapisywania', 'error');
    }
}

async function updateTimesheetSummary(year, month) {
    try {
        const summary = await apiCall(`/timesheet/summary?year=${year}&month=${month}`);
        const container = document.getElementById('timesheet-month-summary');
        
        let html = `<div class="summary-total"><strong>Razem:</strong> ${summary.total_hours} h</div>`;
        
        if (summary.by_project.length > 0) {
            html += '<div class="summary-section"><strong>Wg projektów:</strong>';
            for (const p of summary.by_project) {
                html += `<div class="summary-item">${p.project_name}: <strong>${p.total_hours}h</strong></div>`;
            }
            html += '</div>';
        }
        
        if (summary.by_worker.length > 0) {
            html += '<div class="summary-section"><strong>Wg pracowników:</strong>';
            for (const w of summary.by_worker) {
                html += `<div class="summary-item">${w.worker_name}: <strong>${w.total_hours}h</strong></div>`;
            }
            html += '</div>';
        }
        
        container.innerHTML = html;
    } catch (e) { console.error('Error loading summary:', e); }
}

function showAddWorkerModal() {
    const name = prompt('Imię i nazwisko pracownika:');
    if (!name) return;
    
    const role = prompt('Rola/stanowisko (opcjonalnie):') || null;
    const rateStr = prompt('Stawka godzinowa (opcjonalnie):');
    const hourlyRate = rateStr ? parseFloat(rateStr) : null;
    
    createWorker(name, role, hourlyRate);
}

async function createWorker(name, role, hourlyRate) {
    try {
        await apiCall('/timesheet/workers', {
            method: 'POST',
            body: JSON.stringify({ name, role, hourly_rate: hourlyRate })
        });
        showToast('Pracownik dodany', 'success');
        loadWorkers();
    } catch (e) {
        showToast('Błąd dodawania pracownika', 'error');
    }
}

// =============================================================================
// Integrations
// =============================================================================

const PROVIDER_CONFIGS = {
    // Accounting
    ifirma: {
        name: 'iFirma',
        type: 'accounting',
        fields: [
            { id: 'api_key', label: 'API Key', type: 'password', required: true },
            { id: 'username', label: 'Login (email)', type: 'email', required: true },
            { id: 'company_name', label: 'Nazwa firmy', type: 'text', required: true },
            { id: 'invoice_key', label: 'Klucz faktur', type: 'password', required: false },
            { id: 'expense_key', label: 'Klucz wydatków', type: 'password', required: false }
        ]
    },
    fakturownia: {
        name: 'Fakturownia',
        type: 'accounting',
        fields: [
            { id: 'api_token', label: 'API Token', type: 'password', required: true },
            { id: 'subdomain', label: 'Subdomena', type: 'text', required: true, placeholder: 'np. mojafirma' }
        ]
    },
    wfirma: {
        name: 'wFirma',
        type: 'accounting',
        fields: [
            { id: 'access_key', label: 'Access Key', type: 'password', required: true },
            { id: 'secret_key', label: 'Secret Key', type: 'password', required: true },
            { id: 'company_id', label: 'ID firmy', type: 'text', required: true }
        ]
    },
    infakt: {
        name: 'InFakt',
        type: 'accounting',
        fields: [
            { id: 'api_key', label: 'API Key', type: 'password', required: true }
        ]
    },
    // Cloud Storage
    nextcloud: {
        name: 'Nextcloud',
        type: 'cloud_storage',
        fields: [
            { id: 'url', label: 'URL serwera', type: 'url', required: true, placeholder: 'https://cloud.example.com' },
            { id: 'username', label: 'Nazwa użytkownika', type: 'text', required: true },
            { id: 'password', label: 'Hasło', type: 'password', required: true }
        ]
    },
    google_drive: {
        name: 'Google Drive',
        type: 'cloud_storage',
        fields: [
            { id: 'client_id', label: 'Client ID', type: 'text', required: true },
            { id: 'client_secret', label: 'Client Secret', type: 'password', required: true },
            { id: 'access_token', label: 'Access Token', type: 'password', required: true },
            { id: 'refresh_token', label: 'Refresh Token', type: 'password', required: false }
        ]
    },
    dropbox: {
        name: 'Dropbox',
        type: 'cloud_storage',
        fields: [
            { id: 'access_token', label: 'Access Token', type: 'password', required: true }
        ]
    },
    onedrive: {
        name: 'OneDrive',
        type: 'cloud_storage',
        fields: [
            { id: 'client_id', label: 'Client ID', type: 'text', required: true },
            { id: 'client_secret', label: 'Client Secret', type: 'password', required: true },
            { id: 'access_token', label: 'Access Token', type: 'password', required: true },
            { id: 'refresh_token', label: 'Refresh Token', type: 'password', required: false }
        ]
    },
    aws_s3: {
        name: 'AWS S3',
        type: 'cloud_storage',
        fields: [
            { id: 'access_key_id', label: 'Access Key ID', type: 'text', required: true },
            { id: 'secret_access_key', label: 'Secret Access Key', type: 'password', required: true },
            { id: 'bucket', label: 'Bucket', type: 'text', required: true },
            { id: 'region', label: 'Region', type: 'text', required: false, placeholder: 'eu-central-1' }
        ]
    },
    minio: {
        name: 'MinIO',
        type: 'cloud_storage',
        fields: [
            { id: 'access_key_id', label: 'Access Key', type: 'text', required: true },
            { id: 'secret_access_key', label: 'Secret Key', type: 'password', required: true },
            { id: 'bucket', label: 'Bucket', type: 'text', required: true },
            { id: 'endpoint_url', label: 'Endpoint URL', type: 'url', required: true, placeholder: 'http://minio:9000' }
        ]
    }
};

async function loadIntegrations() {
    try {
        const integrations = await apiCall('/integrations/');
        
        const accountingList = document.getElementById('accounting-integrations');
        const cloudList = document.getElementById('cloud-integrations');
        
        const accounting = integrations.filter(i => i.integration_type === 'accounting');
        const cloud = integrations.filter(i => i.integration_type === 'cloud_storage');
        
        if (accounting.length > 0) {
            accountingList.innerHTML = accounting.map(i => renderIntegrationCard(i)).join('');
        } else {
            accountingList.innerHTML = `<div class="integration-placeholder">
                <p>Brak skonfigurowanych integracji księgowych</p>
                <button class="btn btn-outline" onclick="showAddIntegrationModal('accounting')">Dodaj integrację</button>
            </div>`;
        }
        
        if (cloud.length > 0) {
            cloudList.innerHTML = cloud.map(i => renderIntegrationCard(i)).join('');
        } else {
            cloudList.innerHTML = `<div class="integration-placeholder">
                <p>Brak skonfigurowanych integracji chmurowych</p>
                <button class="btn btn-outline" onclick="showAddIntegrationModal('cloud_storage')">Dodaj integrację</button>
            </div>`;
        }
        
        await loadSyncLogs();
    } catch (error) {
        console.error('Failed to load integrations:', error);
    }
}

function renderIntegrationCard(integration) {
    const config = PROVIDER_CONFIGS[integration.provider] || { name: integration.provider };
    const statusClass = integration.is_verified ? 'green' : 'yellow';
    const statusText = integration.is_verified ? 'Połączono' : 'Nie zweryfikowano';
    
    return `
        <div class="integration-card" data-id="${integration.id}">
            <div class="integration-header">
                <span class="integration-name">${config.name}</span>
                <span class="status-badge ${statusClass}">${statusText}</span>
            </div>
            <div class="integration-meta">
                <span>ID: ${integration.id}</span>
                ${integration.last_sync_at ? `<span>Ostatnia sync: ${new Date(integration.last_sync_at).toLocaleString('pl-PL')}</span>` : ''}
            </div>
            <div class="integration-actions">
                <button class="btn btn-sm" onclick="verifyIntegration('${integration.id}')">Weryfikuj</button>
                ${integration.integration_type === 'accounting' ? 
                    `<button class="btn btn-sm btn-primary" onclick="syncInvoices('${integration.id}')">Synchronizuj</button>` :
                    `<button class="btn btn-sm btn-primary" onclick="uploadReport('${integration.id}')">Wyślij raport</button>`
                }
                <button class="btn btn-sm btn-danger" onclick="deleteIntegration('${integration.id}')">Usuń</button>
            </div>
        </div>
    `;
}

async function loadSyncLogs() {
    try {
        const integrations = await apiCall('/integrations/?active_only=false');
        let allLogs = [];
        
        for (const integration of integrations.slice(0, 5)) {
            const logs = await apiCall(`/integrations/${integration.id}/logs?limit=10`);
            allLogs = allLogs.concat(logs);
        }
        
        allLogs.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
        
        const tbody = document.getElementById('sync-logs-table');
        if (allLogs.length > 0) {
            tbody.innerHTML = allLogs.slice(0, 20).map(log => `
                <tr>
                    <td>${new Date(log.started_at).toLocaleString('pl-PL')}</td>
                    <td>${log.integration_id}</td>
                    <td>${log.sync_type}</td>
                    <td><span class="status-badge ${log.status === 'success' ? 'green' : 'red'}">${log.status}</span></td>
                    <td>${log.items_processed} / ${log.items_failed} błędów</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to load sync logs:', error);
    }
}

function showAddIntegrationModal(type = null) {
    document.getElementById('integration-modal').classList.add('active');
    document.getElementById('integration-form').reset();
    document.getElementById('credential-fields').innerHTML = '';
    
    if (type) {
        document.getElementById('integration-type').value = type;
        updateProviderOptions();
    }
}

function closeIntegrationModal() {
    document.getElementById('integration-modal').classList.remove('active');
}

function updateProviderOptions() {
    const type = document.getElementById('integration-type').value;
    const providerSelect = document.getElementById('integration-provider');
    
    providerSelect.innerHTML = '<option value="">Wybierz dostawcę...</option>';
    
    Object.entries(PROVIDER_CONFIGS)
        .filter(([_, config]) => config.type === type)
        .forEach(([id, config]) => {
            providerSelect.innerHTML += `<option value="${id}">${config.name}</option>`;
        });
    
    document.getElementById('credential-fields').innerHTML = '';
}

function updateCredentialFields() {
    const provider = document.getElementById('integration-provider').value;
    const container = document.getElementById('credential-fields');
    
    if (!provider || !PROVIDER_CONFIGS[provider]) {
        container.innerHTML = '';
        return;
    }
    
    const config = PROVIDER_CONFIGS[provider];
    container.innerHTML = config.fields.map(field => `
        <div class="form-group">
            <label for="cred-${field.id}">${field.label}${field.required ? ' *' : ''}:</label>
            <input type="${field.type}" id="cred-${field.id}" 
                   ${field.required ? 'required' : ''} 
                   ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}>
        </div>
    `).join('');
}

async function saveIntegration(event) {
    event.preventDefault();
    
    const id = document.getElementById('integration-id').value;
    const type = document.getElementById('integration-type').value;
    const provider = document.getElementById('integration-provider').value;
    const baseUrl = document.getElementById('integration-base-url').value;
    
    const credentials = {};
    const config = PROVIDER_CONFIGS[provider];
    
    if (config) {
        config.fields.forEach(field => {
            const value = document.getElementById(`cred-${field.id}`)?.value;
            if (value) credentials[field.id] = value;
        });
    }
    
    try {
        await apiCall('/integrations/', {
            method: 'POST',
            body: JSON.stringify({
                id, provider, 
                integration_type: type,
                credentials,
                base_url: baseUrl || null
            })
        });
        
        showToast('Integracja została dodana', 'success');
        closeIntegrationModal();
        loadIntegrations();
    } catch (error) {
        showToast('Błąd podczas dodawania integracji', 'error');
    }
}

async function verifyIntegration(id) {
    try {
        showToast('Weryfikuję połączenie...', 'info');
        const result = await apiCall(`/integrations/${id}/verify`, { method: 'POST' });
        
        if (result.is_verified) {
            showToast('Połączenie zweryfikowane pomyślnie', 'success');
        } else {
            showToast('Weryfikacja nie powiodła się', 'error');
        }
        
        loadIntegrations();
    } catch (error) {
        showToast('Błąd weryfikacji', 'error');
    }
}

async function syncInvoices(integrationId) {
    try {
        showToast('Rozpoczynam synchronizację faktur...', 'info');
        const result = await apiCall(`/integrations/${integrationId}/sync/invoices`, {
            method: 'POST',
            body: JSON.stringify({
                date_from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                date_to: new Date().toISOString().split('T')[0]
            })
        });
        
        showToast(`Zsynchronizowano ${result.created || 0} nowych faktur`, 'success');
        loadIntegrations();
    } catch (error) {
        showToast('Błąd synchronizacji', 'error');
    }
}

async function syncAllInvoices() {
    try {
        showToast('Synchronizuję faktury ze wszystkich źródeł...', 'info');
        const result = await apiCall('/integrations/actions/sync-all-invoices', {
            method: 'POST',
            body: JSON.stringify({
                date_from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                date_to: new Date().toISOString().split('T')[0]
            })
        });
        
        showToast(`Zsynchronizowano z ${result.integrations_synced} źródeł`, 'success');
        loadIntegrations();
    } catch (error) {
        showToast('Błąd synchronizacji', 'error');
    }
}

async function uploadReport(integrationId) {
    const month = new Date().getMonth() + 1;
    const year = currentFiscalYear;
    
    try {
        showToast('Wysyłam raport...', 'info');
        const result = await apiCall(`/integrations/${integrationId}/upload/report`, {
            method: 'POST',
            body: JSON.stringify({
                report_name: `raport-br-${year}-${String(month).padStart(2, '0')}.pdf`,
                year, month
            })
        });
        
        if (result.success) {
            showToast('Raport wysłany pomyślnie', 'success');
        } else {
            showToast(`Błąd: ${result.error}`, 'error');
        }
        
        loadIntegrations();
    } catch (error) {
        showToast('Błąd wysyłania raportu', 'error');
    }
}

async function uploadAllReports() {
    const month = new Date().getMonth() + 1;
    const year = currentFiscalYear;
    
    try {
        showToast('Wysyłam raporty do wszystkich magazynów...', 'info');
        const result = await apiCall(`/integrations/actions/upload-monthly-reports?year=${year}&month=${month}`, {
            method: 'POST'
        });
        
        showToast(`Wysłano do ${result.integrations_uploaded} magazynów`, 'success');
        loadIntegrations();
    } catch (error) {
        showToast('Błąd wysyłania raportów', 'error');
    }
}

async function deleteIntegration(id) {
    if (!confirm(`Czy na pewno chcesz usunąć integrację "${id}"?`)) return;
    
    try {
        await apiCall(`/integrations/${id}`, { method: 'DELETE' });
        showToast('Integracja została usunięta', 'success');
        loadIntegrations();
    } catch (error) {
        showToast('Błąd usuwania integracji', 'error');
    }
}

// ==================== AI CONFIG ====================
async function loadAIConfig() {
    try {
        // Load current config
        const ocrConfig = await apiCall('/config/ocr/config');
        const llmConfig = await apiCall('/config/llm/config');
        
        // Set OCR values
        document.getElementById('ocr-primary-engine').value = ocrConfig.primary_engine;
        document.getElementById('ocr-strategy').value = ocrConfig.strategy;
        document.getElementById('ocr-min-confidence').value = ocrConfig.min_confidence * 100;
        document.getElementById('ocr-confidence-value').textContent = Math.round(ocrConfig.min_confidence * 100) + '%';
        document.getElementById('ocr-language').value = ocrConfig.language;
        document.getElementById('ocr-use-gpu').checked = ocrConfig.use_gpu;
        document.getElementById('ocr-field-specific').checked = ocrConfig.use_field_specific;
        
        // Set LLM values
        document.getElementById('llm-provider').value = llmConfig.provider;
        document.getElementById('llm-model').value = llmConfig.model;
        document.getElementById('llm-api-base').value = llmConfig.api_base;
        document.getElementById('llm-temperature').value = llmConfig.temperature * 100;
        document.getElementById('llm-temp-value').textContent = llmConfig.temperature.toFixed(2);
        document.getElementById('llm-use-extraction').checked = llmConfig.use_for_extraction;
        document.getElementById('llm-use-classification').checked = llmConfig.use_for_classification;
        document.getElementById('llm-use-validation').checked = llmConfig.use_for_validation;
        
        // Load engines list
        await loadOCREngines();
        await loadDocumentTypes();
        
        // Test connections
        testConnections();
        
        // Add slider listener
        document.getElementById('ocr-min-confidence').addEventListener('input', function() {
            document.getElementById('ocr-confidence-value').textContent = this.value + '%';
        });
    } catch (e) { console.error('Error loading AI config:', e); }
}

async function loadOCREngines() {
    try {
        const data = await apiCall('/config/ocr/engines');
        const html = data.engines.map(e => `
            <div class="engine-card ${e.gpu_required ? 'gpu-required' : ''}">
                <div class="engine-header">
                    <strong>${e.name}</strong>
                    ${e.gpu_required ? '<span class="gpu-badge">GPU</span>' : ''}
                </div>
                <p class="engine-desc">${e.description}</p>
                <div class="engine-scores">
                    <span title="Dokładność">🎯 ${Math.round(e.accuracy_score * 100)}%</span>
                    <span title="Szybkość">⚡ ${Math.round(e.speed_score * 100)}%</span>
                </div>
                <div class="engine-tags">
                    ${e.strengths.slice(0, 3).map(s => `<span class="tag">${s}</span>`).join('')}
                </div>
            </div>
        `).join('');
        document.getElementById('ocr-engines-list').innerHTML = html;
    } catch (e) { console.error('Error loading OCR engines:', e); }
}

async function loadDocumentTypes() {
    try {
        const data = await apiCall('/config/ocr/document-types');
        const html = data.document_types.map(t => `
            <div class="doc-type-card">
                <strong>${t.name}</strong>
                <div class="recommended-engines">
                    ${t.recommended_engines.slice(0, 3).map(e => `<span class="engine-tag">${e}</span>`).join('')}
                </div>
                ${t.required_fields.length > 0 ? `
                    <div class="required-fields">
                        Wymagane: ${t.required_fields.join(', ')}
                    </div>
                ` : ''}
            </div>
        `).join('');
        document.getElementById('document-types-list').innerHTML = html;
    } catch (e) { console.error('Error loading document types:', e); }
}

async function saveAIConfig() {
    try {
        // Save OCR config
        const ocrParams = new URLSearchParams({
            primary_engine: document.getElementById('ocr-primary-engine').value,
            strategy: document.getElementById('ocr-strategy').value,
            min_confidence: document.getElementById('ocr-min-confidence').value / 100,
            language: document.getElementById('ocr-language').value,
            use_gpu: document.getElementById('ocr-use-gpu').checked,
            use_field_specific: document.getElementById('ocr-field-specific').checked
        });
        await apiCall(`/config/ocr/config?${ocrParams}`, { method: 'PUT' });
        
        // Save LLM config
        const llmParams = new URLSearchParams({
            provider: document.getElementById('llm-provider').value,
            model: document.getElementById('llm-model').value,
            api_base: document.getElementById('llm-api-base').value,
            temperature: document.getElementById('llm-temperature').value / 100,
            use_for_extraction: document.getElementById('llm-use-extraction').checked,
            use_for_classification: document.getElementById('llm-use-classification').checked,
            use_for_validation: document.getElementById('llm-use-validation').checked
        });
        await apiCall(`/config/llm/config?${llmParams}`, { method: 'PUT' });
        
        showToast('Konfiguracja zapisana', 'success');
    } catch (e) { showToast('Błąd zapisywania konfiguracji', 'error'); }
}

async function testConnections() {
    // Test OCR
    document.getElementById('status-ocr').innerHTML = '⏳ Sprawdzanie...';
    try {
        const health = await fetch('/api/health').then(r => r.json());
        document.getElementById('status-ocr').innerHTML = '✅ Połączony';
    } catch (e) {
        document.getElementById('status-ocr').innerHTML = '❌ Brak połączenia';
    }
    
    // Test LLM
    document.getElementById('status-llm').innerHTML = '⏳ Sprawdzanie...';
    try {
        const result = await apiCall('/config/test-llm', { method: 'POST' });
        if (result.status === 'connected') {
            document.getElementById('status-llm').innerHTML = '✅ Połączony';
            document.getElementById('status-ollama').innerHTML = `✅ ${result.available_models?.length || 0} modeli`;
        } else {
            document.getElementById('status-llm').innerHTML = '❌ Brak połączenia';
            document.getElementById('status-ollama').innerHTML = '❌ Niedostępny';
        }
    } catch (e) {
        document.getElementById('status-llm').innerHTML = '❌ Błąd';
        document.getElementById('status-ollama').innerHTML = '❌ Błąd';
    }
}

function updateModelList() {
    const provider = document.getElementById('llm-provider').value;
    const modelSelect = document.getElementById('llm-model');
    
    const models = {
        ollama: [
            { id: 'llama3.2', name: 'Llama 3.2 (3B)' },
            { id: 'llama3.1:8b', name: 'Llama 3.1 (8B)' },
            { id: 'mistral', name: 'Mistral 7B' },
            { id: 'gemma2:9b', name: 'Gemma 2 (9B)' },
            { id: 'qwen2.5:7b', name: 'Qwen 2.5 (7B)' },
            { id: 'phi3', name: 'Phi-3' }
        ],
        openai: [
            { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
            { id: 'gpt-4o', name: 'GPT-4o' },
            { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' }
        ],
        anthropic: [
            { id: 'claude-3-5-sonnet-latest', name: 'Claude 3.5 Sonnet' },
            { id: 'claude-3-5-haiku-latest', name: 'Claude 3.5 Haiku' }
        ]
    };
    
    modelSelect.innerHTML = models[provider].map(m => 
        `<option value="${m.id}">${m.name}</option>`
    ).join('');
}

// ==================== LOGS ====================
const logStreams = {};
const LOG_SERVICES = ['api', 'ocr', 'llm', 'web', 'postgres'];

function initLogStreams() {
    LOG_SERVICES.forEach(service => {
        startLogStreamFor(service);
    });
}

function startLogStreamForPage(service) {
    // Close existing stream if any
    if (logStreams[service]) {
        logStreams[service].close();
    }
    
    const logOutput = document.getElementById(`log-output-${service}`);
    const tabDot = document.getElementById(`dot-${service}`);
    
    if (!logOutput) return;
    
    // Start SSE stream
    const eventSource = new EventSource(`${API_BASE}/logs/stream?service=${service}&lines=50`);
    logStreams[service] = eventSource;
    
    eventSource.onopen = () => {
        if (tabDot) tabDot.className = 'tab-dot connected';
    };
    
    eventSource.onmessage = (event) => {
        const line = event.data.replace(/\\n/g, '\n');
        logOutput.textContent += line + '\n';
        // Auto-scroll to bottom
        logOutput.scrollTop = logOutput.scrollHeight;
        
        // Limit lines to prevent memory issues
        const lines = logOutput.textContent.split('\n');
        if (lines.length > 500) {
            logOutput.textContent = lines.slice(-300).join('\n');
        }
    };
    
    eventSource.onerror = () => {
        if (tabDot) tabDot.className = 'tab-dot error';
        eventSource.close();
        logStreams[service] = null;
        // Try to reconnect after 5 seconds
        setTimeout(() => startLogStreamForPage(service), 5000);
    };
}

function switchLogTab(service) {
    // Update tabs
    document.querySelectorAll('.log-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.service === service);
    });
    
    // Update panels
    document.querySelectorAll('.log-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `log-panel-${service}`);
    });
    
    // Scroll to bottom of active panel
    const logOutput = document.getElementById(`log-output-${service}`);
    if (logOutput) logOutput.scrollTop = logOutput.scrollHeight;
}

function copyLogs(service) {
    const logOutput = document.getElementById(`log-output-${service}`) || 
                      document.getElementById(`global-log-output-${service}`);
    if (!logOutput) return;
    
    const text = logOutput.textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Logi ${service.toUpperCase()} skopiowane do schowka`, 'success');
    }).catch(err => {
        showToast('Błąd kopiowania logów', 'error');
        console.error('Copy failed:', err);
    });
}

function clearAllLogs() {
    LOG_SERVICES.forEach(service => {
        const logOutput = document.getElementById(`log-output-${service}`);
        if (logOutput) logOutput.textContent = '';
    });
}

function reconnectAllLogs() {
    LOG_SERVICES.forEach(service => {
        if (logStreams[service]) {
            logStreams[service].close();
        }
        const logOutput = document.getElementById(`log-output-${service}`);
        if (logOutput) logOutput.textContent = '';
    });
    initLogStreams();
}

function stopAllLogStreams() {
    LOG_SERVICES.forEach(service => {
        if (logStreams[service]) {
            logStreams[service].close();
            logStreams[service] = null;
        }
    });
}

// ==================== GLOBAL LOGS OVERLAY ====================
function isGlobalLogsOpen() {
    const el = document.getElementById('global-logs-overlay');
    return el && el.classList.contains('open');
}

function toggleGlobalLogs() {
    const overlay = document.getElementById('global-logs-overlay');
    if (!overlay) return;

    const willOpen = !overlay.classList.contains('open');
    overlay.classList.toggle('open', willOpen);
    setUrlParam('logs', willOpen ? '1' : null, true);

    if (willOpen) {
        initLogStreams();
        const tab = getUrlParam('logs_tab') || 'api';
        switchGlobalLogTab(tab);
    } else {
        stopAllLogStreams();
    }
}

function switchGlobalLogTab(service) {
    document.querySelectorAll('.global-log-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.service === service);
    });

    document.querySelectorAll('.global-log-output').forEach(panel => {
        panel.classList.toggle('active', panel.id === `global-log-output-${service}`);
    });

    setUrlParam('logs_tab', service, false);
}

function clearGlobalLogs() {
    LOG_SERVICES.forEach(service => {
        const el = document.getElementById(`global-log-output-${service}`);
        if (el) el.textContent = '';
    });
}

function copyGlobalLogs() {
    const activeTab = document.querySelector('.global-log-tab.active');
    const service = activeTab ? activeTab.dataset.service : 'api';
    const el = document.getElementById(`global-log-output-${service}`);
    if (el && el.textContent) {
        navigator.clipboard.writeText(el.textContent).then(() => {
            showToast(`Logi ${service.toUpperCase()} skopiowane do schowka`, 'success');
        }).catch(err => {
            console.error('Failed to copy logs:', err);
            showToast('Błąd kopiowania logów', 'error');
        });
    } else {
        showToast('Brak logów do skopiowania', 'warning');
    }
}

function downloadGlobalLogs() {
    const activeTab = document.querySelector('.global-log-tab.active');
    const service = activeTab ? activeTab.dataset.service : 'api';
    const el = document.getElementById(`global-log-output-${service}`);
    if (el && el.textContent) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `logs_${service}_${timestamp}.txt`;
        const blob = new Blob([el.textContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast(`Logi ${service.toUpperCase()} pobrane jako ${filename}`, 'success');
    } else {
        showToast('Brak logów do pobrania', 'warning');
    }
}

// mirror streams into overlay panels
function startLogStreamFor(service) {
    if (logStreams[service]) {
        logStreams[service].close();
    }

    const tabDot = document.getElementById(`dot-${service}`);
    const pageLogOutput = document.getElementById(`log-output-${service}`);
    const overlayLogOutput = document.getElementById(`global-log-output-${service}`);

    const eventSource = new EventSource(`${API_BASE}/logs/stream?service=${service}&lines=50`);
    logStreams[service] = eventSource;

    eventSource.onopen = () => {
        if (tabDot) tabDot.className = 'tab-dot connected';
    };

    eventSource.onmessage = (event) => {
        const line = event.data.replace(/\\n/g, '\n');
        if (pageLogOutput) {
            pageLogOutput.textContent += line + '\n';
            pageLogOutput.scrollTop = pageLogOutput.scrollHeight;
            const lines = pageLogOutput.textContent.split('\n');
            if (lines.length > 500) pageLogOutput.textContent = lines.slice(-300).join('\n');
        }
        if (overlayLogOutput) {
            overlayLogOutput.textContent += line + '\n';
            overlayLogOutput.scrollTop = overlayLogOutput.scrollHeight;
            const lines = overlayLogOutput.textContent.split('\n');
            if (lines.length > 500) overlayLogOutput.textContent = lines.slice(-300).join('\n');
        }
    };

    eventSource.onerror = () => {
        if (tabDot) tabDot.className = 'tab-dot error';
        eventSource.close();
        logStreams[service] = null;
        setTimeout(() => startLogStreamFor(service), 5000);
    };
}

// Init
window.addEventListener('popstate', () => {
    const page = getPageFromUrl();
    navigateTo(page, { updateUrl: false });

    const logs = getUrlParam('logs');
    const overlay = document.getElementById('global-logs-overlay');
    if (overlay) {
        const shouldOpen = logs === '1';
        overlay.classList.toggle('open', shouldOpen);
        if (shouldOpen) {
            initLogStreams();
            switchGlobalLogTab(getUrlParam('logs_tab') || 'api');
        } else {
            stopAllLogStreams();
        }
    }

    const docId = getUrlParam('doc');
    if (docId) {
        showDocumentDetail(docId, { updateUrl: false });
    } else {
        closeDocumentModal({ updateUrl: false });
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // Setup nav click handlers
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => navigateTo(item.dataset.page));
    });

    const page = getPageFromUrl();
    setPageInUrl(page, false);
    navigateTo(page, { updateUrl: false });

    if (getUrlParam('logs') === '1') {
        const overlay = document.getElementById('global-logs-overlay');
        if (overlay) {
            overlay.classList.add('open');
            initLogStreams();
            switchGlobalLogTab(getUrlParam('logs_tab') || 'api');
        }
    }

    const docId = getUrlParam('doc');
    if (docId) {
        showDocumentDetail(docId, { updateUrl: false });
    } else {
        closeDocumentModal({ updateUrl: false });
    }
});

// =============================================================================
// Git Timesheet
// =============================================================================

let gitScanResults = null;
let gitSelectedAuthors = [];
let gitSelectedRepos = [];
let gitCommitsData = [];
let gitProjectMappings = {};

async function initGitTimesheet() {
    console.log('[Git Timesheet] initGitTimesheet called');
    // Load workers for the git-timesheet worker select
    try {
        const workers = await apiCall('/timesheet/workers');
        const select = document.getElementById('git-timesheet-worker');
        if (select) {
            select.innerHTML = '<option value="">-- Wybierz pracownika --</option>' +
                workers.map(w => `<option value="${w.id}">${w.name}</option>`).join('');
            console.log('[Git Timesheet] Loaded workers:', workers.length);
        }
    } catch (e) {
        console.error('[Git Timesheet] Error loading workers:', e);
    }
}

async function scanGitRepos() {
    const folderPath = document.getElementById('git-folder-path').value;
    const depth = parseInt(document.getElementById('git-scan-depth').value);
    
    if (!folderPath) {
        showToast('Wprowadź ścieżkę do folderu', 'error');
        return;
    }
    
    const resultsDiv = document.getElementById('git-scan-results');
    resultsDiv.innerHTML = '<p class="loading">🔍 Skanowanie repozytoriów...</p>';
    
    try {
        const result = await apiCall('/git-timesheet/scan', {
            method: 'POST',
            body: JSON.stringify({
                folder_path: folderPath,
                max_depth: depth
            })
        });
        
        gitScanResults = result;
        
        if (result.total_repos === 0) {
            resultsDiv.innerHTML = '<p class="empty-state">Nie znaleziono repozytoriów Git w podanej lokalizacji</p>';
            return;
        }
        
        resultsDiv.innerHTML = `
            <div class="git-scan-summary">
                <strong>Znaleziono ${result.total_repos} repozytoriów</strong>
                <span class="text-muted">w ${result.base_path}</span>
            </div>
            <div class="git-repos-list">
                ${result.repositories.map(repo => `
                    <div class="git-repo-item">
                        <span class="repo-name">📁 ${repo.name}</span>
                        <span class="repo-path text-muted">${repo.path}</span>
                        <span class="repo-stats">${repo.commit_count} commitów</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        displayGitAuthors(result.all_authors);
        document.getElementById('git-authors-section').style.display = 'block';
        
    } catch (e) {
        console.error('Error scanning git repos:', e);
        resultsDiv.innerHTML = `<p class="error">Błąd skanowania: ${e.message}</p>`;
    }
}

function displayGitAuthors(authors) {
    const container = document.getElementById('git-authors-list');
    
    if (!authors || authors.length === 0) {
        container.innerHTML = '<p class="empty-state">Brak autorów</p>';
        return;
    }
    
    authors.sort((a, b) => b.commit_count - a.commit_count);
    
    container.innerHTML = `
        <div class="git-authors-grid">
            ${authors.map(author => `
                <label class="git-author-item">
                    <input type="checkbox" value="${author.name}" 
                           onchange="toggleGitAuthor('${author.name}')" checked>
                    <div class="author-info">
                        <strong>${author.name}</strong>
                        <span class="text-muted">${author.email}</span>
                        <span class="commit-count">${author.commit_count} commitów</span>
                    </div>
                </label>
            `).join('')}
        </div>
        <div class="author-actions">
            <button class="btn btn-sm btn-outline" onclick="selectAllGitAuthors(true)">Zaznacz wszystkich</button>
            <button class="btn btn-sm btn-outline" onclick="selectAllGitAuthors(false)">Odznacz wszystkich</button>
        </div>
    `;
    
    gitSelectedAuthors = authors.map(a => a.name);
    displayGitRepoMapping();
    document.getElementById('git-repos-section').style.display = 'block';
}

function toggleGitAuthor(authorName) {
    const idx = gitSelectedAuthors.indexOf(authorName);
    if (idx >= 0) {
        gitSelectedAuthors.splice(idx, 1);
    } else {
        gitSelectedAuthors.push(authorName);
    }
}

function selectAllGitAuthors(select) {
    const checkboxes = document.querySelectorAll('#git-authors-list input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = select);
    
    if (select && gitScanResults) {
        gitSelectedAuthors = gitScanResults.all_authors.map(a => a.name);
    } else {
        gitSelectedAuthors = [];
    }
}

async function displayGitRepoMapping() {
    const container = document.getElementById('git-repo-mapping');
    console.log('[Git Timesheet] displayGitRepoMapping called, gitScanResults:', gitScanResults?.repositories?.length || 0);
    
    if (!gitScanResults || !gitScanResults.repositories) {
        container.innerHTML = '<p class="empty-state">Najpierw wykonaj skanowanie</p>';
        return;
    }
    
    let projects = [];
    try {
        projects = await apiCall('/projects/');
        console.log('[Git Timesheet] Loaded projects:', projects.length);
    } catch (e) {
        console.error('[Git Timesheet] Error loading projects:', e);
    }
    
    if (projects.length === 0) {
        container.innerHTML = '<p class="empty-state">Brak projektów B+R. Utwórz projekt, aby mapować repozytoria.</p>';
        return;
    }
    
    // Store projects for select all functionality
    window.gitProjects = projects;
    
    let html = `
        <table class="git-mapping-table">
            <thead>
                <tr>
                    <th>Repozytorium Git</th>
                    <th>Ścieżka</th>
                    ${projects.map(p => `
                        <th class="project-col" title="${p.name}">
                            <div class="project-header">
                                <input type="checkbox" 
                                       id="select-all-${p.id}" 
                                       onchange="selectAllReposForProject('${p.id}')"
                                       title="Zaznacz wszystkie">
                                <span>${p.name.substring(0, 12)}${p.name.length > 12 ? '..' : ''}</span>
                            </div>
                        </th>
                    `).join('')}
                </tr>
            </thead>
            <tbody>
    `;
    
    for (const repo of gitScanResults.repositories) {
        const safeRepoId = repo.path.replace(/[^a-zA-Z0-9]/g, '_');
        html += `
            <tr data-repo="${repo.path}">
                <td><strong>${repo.name}</strong></td>
                <td class="text-muted path-cell">${repo.path}</td>
                ${projects.map(p => `
                    <td class="check-cell">
                        <input type="radio" name="repo-${safeRepoId}" 
                               value="${p.id}" data-repo="${repo.path}"
                               class="repo-radio-${p.id}"
                               onchange="updateGitProjectMapping(this.dataset.repo, '${p.id}')">
                    </td>
                `).join('')}
            </tr>
        `;
    }
    
    html += '</tbody></table>';
    container.innerHTML = html;
    
    const now = new Date();
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    document.getElementById('git-date-since').value = lastMonth.toISOString().split('T')[0];
    document.getElementById('git-date-until').value = now.toISOString().split('T')[0];
}

function selectAllReposForProject(projectId) {
    const checkbox = document.getElementById(`select-all-${projectId}`);
    const radios = document.querySelectorAll(`.repo-radio-${projectId}`);
    console.log(`[Git Timesheet] selectAllReposForProject: ${projectId}, checked: ${checkbox.checked}, radios: ${radios.length}`);
    
    if (checkbox.checked) {
        // Uncheck other project checkboxes
        window.gitProjects?.forEach(p => {
            if (p.id !== projectId) {
                const otherCheckbox = document.getElementById(`select-all-${p.id}`);
                if (otherCheckbox) otherCheckbox.checked = false;
            }
        });
        
        // Select all radios for this project
        radios.forEach(radio => {
            radio.checked = true;
            updateGitProjectMapping(radio.dataset.repo, projectId);
        });
    } else {
        // Deselect all radios for this project
        radios.forEach(radio => {
            if (radio.checked) {
                radio.checked = false;
                delete gitProjectMappings[radio.dataset.repo];
            }
        });
    }
    checkGitTimesheetReady();
    console.log(`[Git Timesheet] Project mappings count: ${Object.keys(gitProjectMappings).length}`);
}

function updateGitProjectMapping(repoPath, projectId) {
    gitProjectMappings[repoPath] = projectId;
    checkGitTimesheetReady();
}

function checkGitTimesheetReady() {
    const btn = document.getElementById('btn-generate-git-ts');
    const hasAuthors = gitSelectedAuthors.length > 0;
    const hasMappings = Object.keys(gitProjectMappings).length > 0;
    const hasCommits = gitCommitsData.length > 0;
    btn.disabled = !(hasAuthors && hasMappings && hasCommits);
}

async function loadGitCommits() {
    if (!gitScanResults || gitSelectedAuthors.length === 0) {
        showToast('Najpierw wybierz autorów', 'error');
        return;
    }
    
    const since = document.getElementById('git-date-since').value;
    const until = document.getElementById('git-date-until').value;
    
    const preview = document.getElementById('git-commits-preview');
    preview.innerHTML = '<p class="loading">📥 Pobieranie commitów...</p>';
    document.getElementById('git-commits-section').style.display = 'block';
    
    try {
        const result = await apiCall('/git-timesheet/commits', {
            method: 'POST',
            body: JSON.stringify({
                repo_paths: gitScanResults.repositories.map(r => r.path),
                authors: gitSelectedAuthors,
                since: since || null,
                until: until || null
            })
        });
        
        gitCommitsData = result.commits;
        
        document.getElementById('git-commits-count').textContent = `${result.total_commits} commitów`;
        document.getElementById('git-commits-days').textContent = `${result.date_count} dni`;
        
        if (result.commits.length === 0) {
            preview.innerHTML = '<p class="empty-state">Brak commitów w wybranym zakresie</p>';
            return;
        }
        
        let html = '<div class="git-commits-list">';
        const byDate = result.by_date;
        const dates = Object.keys(byDate).sort().reverse();
        
        for (const dateStr of dates.slice(0, 30)) {
            const commits = byDate[dateStr];
            html += `
                <div class="git-commits-day">
                    <div class="commit-date-header">
                        <strong>${dateStr}</strong>
                        <span class="commit-count">${commits.length} commitów</span>
                    </div>
                    <div class="commit-list">
                        ${commits.slice(0, 10).map(c => `
                            <div class="commit-item">
                                <span class="commit-time">${c.date.substring(11, 16)}</span>
                                <span class="commit-repo">${c.repo_name}</span>
                                <span class="commit-hash">${c.hash}</span>
                                <span class="commit-msg">${escapeHtml(c.message.substring(0, 60))}${c.message.length > 60 ? '...' : ''}</span>
                                <span class="commit-author">${c.author_name}</span>
                            </div>
                        `).join('')}
                        ${commits.length > 10 ? `<div class="more-commits">... i ${commits.length - 10} więcej</div>` : ''}
                    </div>
                </div>
            `;
        }
        
        if (dates.length > 30) {
            html += `<div class="more-days">... i ${dates.length - 30} więcej dni</div>`;
        }
        
        html += '</div>';
        preview.innerHTML = html;
        
        document.getElementById('git-timesheet-result').style.display = 'block';
        checkGitTimesheetReady();
        
    } catch (e) {
        console.error('Error loading git commits:', e);
        preview.innerHTML = `<p class="error">Błąd: ${e.message}</p>`;
    }
}

async function generateGitTimesheet() {
    console.log('[Git Timesheet] generateGitTimesheet called');
    console.log('[Git Timesheet] commits:', gitCommitsData.length, 'mappings:', Object.keys(gitProjectMappings).length);
    
    if (gitCommitsData.length === 0) {
        showToast('Najpierw pobierz commity', 'error');
        return;
    }
    
    if (Object.keys(gitProjectMappings).length === 0) {
        showToast('Przypisz repozytoria do projektów B+R', 'error');
        return;
    }
    
    // Try git-timesheet worker first, then fallback to timesheet-worker
    let workerSelect = document.getElementById('git-timesheet-worker');
    let workerId = workerSelect?.value;
    if (!workerId) {
        workerSelect = document.getElementById('timesheet-worker');
        workerId = workerSelect?.value;
    }
    console.log('[Git Timesheet] workerId:', workerId);
    
    if (!workerId) {
        showToast('Wybierz pracownika z listy w nagłówku strony', 'error');
        return;
    }
    
    const resultDiv = document.getElementById('git-timesheet-grid');
    resultDiv.innerHTML = '<p class="loading">📊 Generowanie harmonogramu...</p>';
    
    try {
        const result = await apiCall('/git-timesheet/generate-timesheet', {
            method: 'POST',
            body: JSON.stringify({
                commits: gitCommitsData,
                worker_id: workerId,
                project_mappings: gitProjectMappings
            })
        });
        
        if (result.entries_created === 0) {
            resultDiv.innerHTML = '<p class="empty-state">Nie utworzono żadnych wpisów. Sprawdź mapowanie repozytoriów.</p>';
            return;
        }
        
        resultDiv.innerHTML = `
            <div class="git-timesheet-summary">
                <div class="summary-stat">
                    <strong>${result.entries_created}</strong>
                    <span>wpisów utworzonych</span>
                </div>
                <div class="summary-stat">
                    <strong>${result.total_slots}</strong>
                    <span>bloków czasowych</span>
                </div>
            </div>
            <div class="git-entries-list">
                ${result.entries.slice(0, 20).map(e => `
                    <div class="git-entry-item">
                        <span class="entry-date">${e.work_date}</span>
                        <span class="entry-slot">${e.time_slot}</span>
                        <span class="entry-hours">${e.hours}h</span>
                        <span class="entry-commits">${e.commits.length} commitów</span>
                    </div>
                `).join('')}
                ${result.entries.length > 20 ? `<div class="more-entries">... i ${result.entries.length - 20} więcej</div>` : ''}
            </div>
            <div class="git-success-message">
                ✅ Harmonogram został wygenerowany. Przejdź do zakładki "Harmonogram prac" aby zobaczyć wynik.
            </div>
        `;
        
        showToast(`Utworzono ${result.entries_created} wpisów w harmonogramie`, 'success');
        
    } catch (e) {
        console.error('Error generating git timesheet:', e);
        resultDiv.innerHTML = `<p class="error">Błąd: ${e.message}</p>`;
        showToast('Błąd generowania harmonogramu', 'error');
    }
}

// ==================== DOCUMENT GENERATOR ====================
let docTemplatesCache = [];
let currentDocCategory = '';

async function loadDocTemplates() {
    try {
        const result = await apiCall('/doc-generator/templates');
        docTemplatesCache = result.templates || [];
        renderDocTemplates();
        
        // Load filter options
        const filterResult = await apiCall('/doc-generator/filter-options');
        
        const projectSelect = document.getElementById('docgen-project-filter');
        if (projectSelect && filterResult.projects) {
            const currentVal = projectSelect.value;
            projectSelect.innerHTML = '<option value="">-- Wszystkie projekty --</option>';
            filterResult.projects.forEach(p => {
                projectSelect.innerHTML += `<option value="${p.id}">${p.name || p.code}</option>`;
            });
            projectSelect.value = currentVal || PROJECT_ID;
        }
        
        const yearSelect = document.getElementById('docgen-year-filter');
        if (yearSelect && filterResult.years) {
            const currentYear = yearSelect.value;
            yearSelect.innerHTML = '<option value="">-- Rok --</option>';
            filterResult.years.forEach(y => {
                yearSelect.innerHTML += `<option value="${y}">${y}</option>`;
            });
            yearSelect.value = currentYear || new Date().getFullYear();
        }
    } catch (e) {
        console.error('Error loading doc templates:', e);
        showToast('Błąd ładowania szablonów', 'error');
    }
}

function filterDocTemplates(category) {
    currentDocCategory = category;
    document.querySelectorAll('.docgen-categories .category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });
    renderDocTemplates();
}

function renderDocTemplates() {
    const container = document.getElementById('docgen-templates');
    if (!container) return;
    
    let templates = docTemplatesCache;
    if (currentDocCategory) {
        templates = templates.filter(t => t.category === currentDocCategory);
    }
    
    if (templates.length === 0) {
        container.innerHTML = '<div class="empty-state">Brak szablonów do wyświetlenia</div>';
        return;
    }
    
    const categoryIcons = {
        project: '📁', financial: '💰', timesheet: '⏱️',
        legal: '📜', tax: '🧾', report: '📊'
    };
    
    const timeScopeLabels = {
        none: '', monthly: 'Miesięczny', quarterly: 'Kwartalny',
        yearly: 'Roczny', project: 'Projektowy', custom: 'Własny'
    };
    
    container.innerHTML = templates.map(t => `
        <div class="docgen-template-card" data-template-id="${t.id}">
            <div class="template-header">
                <span class="template-icon">${categoryIcons[t.category] || '📄'}</span>
                <h3>${t.name}</h3>
            </div>
            <p class="template-description">${t.description}</p>
            <div class="template-meta">
                <span class="template-scope">${timeScopeLabels[t.time_scope] || ''}</span>
                <span class="template-version">v${t.version}</span>
            </div>
            <div class="template-actions">
                <button class="btn btn-sm btn-secondary" onclick="previewDocData('${t.id}')">
                    👁️ Podgląd danych
                </button>
                <button class="btn btn-sm btn-secondary" onclick="downloadDemoDoc('${t.id}')">
                    📥 Demo
                </button>
                <button class="btn btn-sm btn-primary" onclick="openDocGenerateModal('${t.id}')">
                    ✨ Generuj
                </button>
            </div>
        </div>
    `).join('');
}

async function previewDocData(templateId) {
    const projectId = document.getElementById('docgen-project-filter')?.value || PROJECT_ID;
    const year = document.getElementById('docgen-year-filter')?.value || new Date().getFullYear();
    const month = document.getElementById('docgen-month-filter')?.value || null;
    
    try {
        showToast('Pobieranie danych...', 'info');
        const result = await apiCall('/doc-generator/preview-data', {
            method: 'POST',
            body: JSON.stringify({
                template_id: templateId,
                params: { project_id: projectId, year: parseInt(year), month: month ? parseInt(month) : null }
            })
        });
        
        // Show data in a modal
        const modal = document.getElementById('doc-preview-modal');
        if (!modal) {
            // Create modal if it doesn't exist
            const modalHtml = `
                <div id="doc-preview-modal" class="modal">
                    <div class="modal-content modal-lg">
                        <span class="modal-close" onclick="closeDocPreviewModal()">&times;</span>
                        <h2>Podgląd danych dla szablonu</h2>
                        <div id="doc-preview-content"></div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }
        
        const content = document.getElementById('doc-preview-content') || document.querySelector('#doc-preview-modal .modal-content');
        content.innerHTML = `
            <h3>Parametry</h3>
            <pre>${JSON.stringify(result.params, null, 2)}</pre>
            <h3>Dane źródłowe</h3>
            ${Object.entries(result.data || {}).map(([key, value]) => `
                <details open>
                    <summary><strong>${key}</strong> (${Array.isArray(value) ? value.length + ' rekordów' : 'obiekt'})</summary>
                    <pre style="max-height: 300px; overflow: auto;">${JSON.stringify(value, null, 2)}</pre>
                </details>
            `).join('')}
            ${result.errors ? `<div class="alert alert-warning">Błędy: ${result.errors.join(', ')}</div>` : ''}
        `;
        
        document.getElementById('doc-preview-modal').classList.add('active');
        
    } catch (e) {
        showToast('Błąd pobierania danych: ' + e.message, 'error');
    }
}

function closeDocPreviewModal() {
    const modal = document.getElementById('doc-preview-modal');
    if (modal) modal.classList.remove('active');
}

async function downloadDemoDoc(templateId) {
    try {
        const result = await apiCall(`/doc-generator/demo/${templateId}`);
        
        const blob = new Blob([result.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${templateId}_demo.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast('Demo pobrane', 'success');
    } catch (e) {
        showToast('Błąd pobierania demo: ' + e.message, 'error');
    }
}

async function openDocGenerateModal(templateId) {
    const template = docTemplatesCache.find(t => t.id === templateId);
    if (!template) return;
    
    const projectId = document.getElementById('docgen-project-filter')?.value || PROJECT_ID;
    const year = document.getElementById('docgen-year-filter')?.value || new Date().getFullYear();
    const month = document.getElementById('docgen-month-filter')?.value || '';
    
    // Create or show generate modal
    let modal = document.getElementById('doc-generate-modal');
    if (!modal) {
        const modalHtml = `
            <div id="doc-generate-modal" class="modal">
                <div class="modal-content modal-lg">
                    <span class="modal-close" onclick="closeDocGenerateModal()">&times;</span>
                    <h2 id="docgen-modal-title">Generuj dokument</h2>
                    <div id="docgen-modal-body"></div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modal = document.getElementById('doc-generate-modal');
    }
    
    document.getElementById('docgen-modal-title').textContent = `Generuj: ${template.name}`;
    document.getElementById('docgen-modal-body').innerHTML = `
        <form id="docgen-form" onsubmit="generateDocument(event, '${templateId}')">
            <div class="form-group">
                <label>Projekt:</label>
                <select id="docgen-form-project" required>
                    <option value="${projectId}" selected>Wybrany projekt</option>
                </select>
            </div>
            <div class="form-group">
                <label>Rok:</label>
                <input type="number" id="docgen-form-year" value="${year}" min="2020" max="2030">
            </div>
            ${template.time_scope === 'monthly' ? `
            <div class="form-group">
                <label>Miesiąc:</label>
                <select id="docgen-form-month">
                    <option value="">-- Wybierz --</option>
                    <option value="1" ${month==='1'?'selected':''}>Styczeń</option>
                    <option value="2" ${month==='2'?'selected':''}>Luty</option>
                    <option value="3" ${month==='3'?'selected':''}>Marzec</option>
                    <option value="4" ${month==='4'?'selected':''}>Kwiecień</option>
                    <option value="5" ${month==='5'?'selected':''}>Maj</option>
                    <option value="6" ${month==='6'?'selected':''}>Czerwiec</option>
                    <option value="7" ${month==='7'?'selected':''}>Lipiec</option>
                    <option value="8" ${month==='8'?'selected':''}>Sierpień</option>
                    <option value="9" ${month==='9'?'selected':''}>Wrzesień</option>
                    <option value="10" ${month==='10'?'selected':''}>Październik</option>
                    <option value="11" ${month==='11'?'selected':''}>Listopad</option>
                    <option value="12" ${month==='12'?'selected':''}>Grudzień</option>
                </select>
            </div>
            ` : ''}
            <div class="form-group checkbox-group">
                <label><input type="checkbox" id="docgen-use-llm"> Użyj LLM do wzbogacenia treści</label>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeDocGenerateModal()">Anuluj</button>
                <button type="submit" class="btn btn-primary">✨ Generuj dokument</button>
            </div>
        </form>
        <div id="docgen-result" style="display:none;">
            <h3>Wygenerowany dokument</h3>
            <div class="docgen-result-actions">
                <button class="btn btn-sm btn-secondary" onclick="copyDocContent()">📋 Kopiuj</button>
                <button class="btn btn-sm btn-secondary" onclick="downloadDocContent()">📥 Pobierz MD</button>
                <button class="btn btn-sm btn-secondary" onclick="editDocContent()">✏️ Edytuj</button>
            </div>
            <div id="docgen-result-content" class="markdown-preview"></div>
        </div>
    `;
    
    modal.classList.add('active');
}

function closeDocGenerateModal() {
    const modal = document.getElementById('doc-generate-modal');
    if (modal) modal.classList.remove('active');
}

let generatedDocContent = '';

async function generateDocument(event, templateId) {
    event.preventDefault();
    
    const projectId = document.getElementById('docgen-form-project')?.value || PROJECT_ID;
    const year = parseInt(document.getElementById('docgen-form-year')?.value) || new Date().getFullYear();
    const monthEl = document.getElementById('docgen-form-month');
    const month = monthEl ? (monthEl.value ? parseInt(monthEl.value) : null) : null;
    const useLlm = document.getElementById('docgen-use-llm')?.checked || false;
    
    try {
        showToast('Generowanie dokumentu...', 'info');
        
        const result = await apiCall('/doc-generator/generate', {
            method: 'POST',
            body: JSON.stringify({
                template_id: templateId,
                params: { project_id: projectId, year, month },
                use_llm: useLlm,
                llm_model: 'llama3.2'
            })
        });
        
        generatedDocContent = result.content;
        
        const resultDiv = document.getElementById('docgen-result');
        const contentDiv = document.getElementById('docgen-result-content');
        
        if (resultDiv && contentDiv) {
            resultDiv.style.display = 'block';
            // Use markdown renderer if available
            if (typeof renderMarkdown === 'function') {
                contentDiv.innerHTML = renderMarkdown(result.content);
            } else {
                contentDiv.innerHTML = `<pre>${result.content}</pre>`;
            }
        }
        
        showToast('Dokument wygenerowany', 'success');
        
    } catch (e) {
        showToast('Błąd generowania: ' + e.message, 'error');
    }
}

function copyDocContent() {
    if (generatedDocContent) {
        navigator.clipboard.writeText(generatedDocContent).then(() => {
            showToast('Skopiowano do schowka', 'success');
        });
    }
}

function downloadDocContent() {
    if (generatedDocContent) {
        const blob = new Blob([generatedDocContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dokument_${new Date().toISOString().slice(0,10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

function editDocContent() {
    const contentDiv = document.getElementById('docgen-result-content');
    if (!contentDiv) return;
    
    contentDiv.innerHTML = `
        <textarea id="docgen-edit-textarea" style="width:100%; height:400px; font-family:monospace;">${generatedDocContent}</textarea>
        <div class="form-actions" style="margin-top:10px;">
            <button class="btn btn-secondary" onclick="cancelDocEdit()">Anuluj</button>
            <button class="btn btn-primary" onclick="saveDocEdit()">Zapisz zmiany</button>
        </div>
    `;
}

function cancelDocEdit() {
    const contentDiv = document.getElementById('docgen-result-content');
    if (contentDiv && typeof renderMarkdown === 'function') {
        contentDiv.innerHTML = renderMarkdown(generatedDocContent);
    }
}

function saveDocEdit() {
    const textarea = document.getElementById('docgen-edit-textarea');
    if (textarea) {
        generatedDocContent = textarea.value;
        cancelDocEdit();
        showToast('Zmiany zapisane', 'success');
    }
}

// ==================== DOCUMENT ANNOTATIONS ====================
async function loadDocAnnotations() {
    const container = document.getElementById('doc-annotations-list');
    if (!container) return;
    
    container.innerHTML = '<div class="loading">Ładowanie dokumentów...</div>';
    
    try {
        const result = await apiCall('/documents/notes?limit=100');
        const items = result.items || [];
        
        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">Brak dokumentów do wyświetlenia</div>';
            return;
        }
        
        container.innerHTML = items.map(doc => `
            <div class="doc-annotation-card" data-doc-id="${doc.id}">
                <div class="doc-annotation-header">
                    <div class="doc-info">
                        <span class="doc-icon">${getDocTypeIcon(doc.document_type)}</span>
                        <div class="doc-details">
                            <h4>${doc.filename}</h4>
                            <span class="doc-type">${doc.document_type}</span>
                            <span class="doc-date">${doc.created_at ? new Date(doc.created_at).toLocaleDateString('pl-PL') : ''}</span>
                        </div>
                    </div>
                    <div class="doc-actions">
                        <a href="${doc.file_url}" target="_blank" class="btn btn-sm btn-secondary">📄 Otwórz</a>
                        <button class="btn btn-sm btn-secondary" onclick="showDocumentDetail('${doc.id}')">👁️ Szczegóły</button>
                    </div>
                </div>
                ${doc.ocr_excerpt ? `
                <div class="doc-ocr-excerpt">
                    <strong>OCR:</strong> ${doc.ocr_excerpt.substring(0, 200)}${doc.ocr_excerpt.length > 200 ? '...' : ''}
                </div>
                ` : ''}
                <div class="doc-annotation-content">
                    <label>Adnotacja / notatka kontekstowa:</label>
                    <textarea 
                        id="annotation-${doc.id}" 
                        class="doc-annotation-textarea"
                        placeholder="Dodaj notatkę o tym dokumencie dla kontekstu B+R..."
                        onchange="saveDocAnnotation('${doc.id}')"
                    >${doc.notes || ''}</textarea>
                    <span class="annotation-status" id="annotation-status-${doc.id}">
                        ${doc.notes_updated_at ? `Zapisano: ${new Date(doc.notes_updated_at).toLocaleString('pl-PL')}` : ''}
                    </span>
                </div>
            </div>
        `).join('');
        
    } catch (e) {
        container.innerHTML = `<div class="error">Błąd ładowania: ${e.message}</div>`;
    }
}

function getDocTypeIcon(type) {
    const icons = {
        invoice: '🧾', receipt: '🧾', contract: '📜',
        report: '📊', timesheet: '⏱️', other: '📄'
    };
    return icons[type] || '📄';
}

async function saveDocAnnotation(docId) {
    const textarea = document.getElementById(`annotation-${docId}`);
    const statusEl = document.getElementById(`annotation-status-${docId}`);
    if (!textarea) return;
    
    const notes = textarea.value;
    
    try {
        await apiCall(`/documents/${docId}/notes`, {
            method: 'PUT',
            body: JSON.stringify({ notes })
        });
        
        if (statusEl) {
            statusEl.textContent = `Zapisano: ${new Date().toLocaleString('pl-PL')}`;
        }
    } catch (e) {
        showToast('Błąd zapisu adnotacji', 'error');
    }
}

// Expose functions globally
window.loadDocTemplates = loadDocTemplates;
window.filterDocTemplates = filterDocTemplates;
window.previewDocData = previewDocData;
window.closeDocPreviewModal = closeDocPreviewModal;
window.downloadDemoDoc = downloadDemoDoc;
window.openDocGenerateModal = openDocGenerateModal;
window.closeDocGenerateModal = closeDocGenerateModal;
window.generateDocument = generateDocument;
window.copyDocContent = copyDocContent;
window.downloadDocContent = downloadDocContent;
window.editDocContent = editDocContent;
window.cancelDocEdit = cancelDocEdit;
window.saveDocEdit = saveDocEdit;
window.loadDocAnnotations = loadDocAnnotations;
window.saveDocAnnotation = saveDocAnnotation;
