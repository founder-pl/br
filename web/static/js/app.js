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
                      projects: loadProjects, expenses: () => { loadProjectsForFilter(); loadExpenses(); },
                      reports: loadReports, clarifications: loadClarifications, timesheet: initTimesheet,
                      integrations: loadIntegrations, logs: initLogStreams, 'ai-config': loadAIConfig };
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

// Dashboard
async function loadDashboard() {
    try {
        const summary = await apiCall(`/projects/${PROJECT_ID}/summary`);
        document.getElementById('total-expenses').textContent = formatCurrency(summary.total_expenses);
        document.getElementById('br-expenses').textContent = formatCurrency(summary.br_qualified_expenses);
        document.getElementById('br-deduction').textContent = formatCurrency(summary.br_deduction_amount);
        document.getElementById('ip-expenses').textContent = formatCurrency(summary.ip_qualified_expenses);
        document.getElementById('clarification-badge').textContent = summary.needs_clarification || 0;
        await loadRecentDocuments();
        
        if (summary.expenses_by_category && Object.keys(summary.expenses_by_category).length > 0) {
            document.getElementById('category-breakdown').innerHTML = Object.entries(summary.expenses_by_category)
                .map(([cat, amount]) => `<div class="category-item"><span>${getCategoryName(cat)}</span><span>${formatCurrency(amount)}</span></div>`).join('');
        }
    } catch (error) { console.error('Dashboard error:', error); }
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
        document.getElementById('recent-documents').innerHTML = html;
        document.getElementById('uploaded-documents').innerHTML = html;
    } catch (e) { console.error('Error:', e); }
}

function getDocTypeName(type) {
    const types = { invoice: 'Faktura', receipt: 'Paragon', contract: 'Umowa', protocol: 'Protokół', report: 'Raport', other: 'Inny', auto: 'Auto' };
    return types[type] || type;
}

async function deleteDocument(docId) {
    if (!confirm('Czy na pewno chcesz usunąć ten dokument?')) return;
    try {
        await apiCall(`/documents/${docId}`, { method: 'DELETE' });
        // Optimistic UI update
        document.querySelectorAll(`.document-item[data-id="${docId}"]`).forEach(el => el.remove());
        showToast('Dokument usunięty', 'success');
        loadRecentDocuments();
    } catch (e) { showToast('Błąd usuwania dokumentu', 'error'); }
}

async function retryOcr(docId) {
    try {
        await apiCall(`/documents/${docId}/reprocess`, { method: 'POST' });
        showToast('OCR uruchomiony ponownie', 'success');
        loadRecentDocuments();
    } catch (e) { showToast('Błąd uruchamiania OCR', 'error'); }
}

let currentDocData = null;

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
        const extractedData = doc.extracted_data || {};
        
        document.getElementById('document-modal-content').innerHTML = `
            <div class="doc-detail-header">
                <h3>📄 ${doc.filename}</h3>
                <span class="status-badge ${doc.ocr_status}">${getStatusLabel(doc.ocr_status)}</span>
            </div>
            <div class="doc-detail-info">
                <p><strong>Typ:</strong> ${getDocTypeName(doc.document_type)}</p>
                <p><strong>Pewność OCR:</strong> ${doc.ocr_confidence ? (doc.ocr_confidence * 100).toFixed(1) + '%' : '-'}</p>
                <p><strong>Data dodania:</strong> ${new Date(doc.created_at).toLocaleString('pl-PL')}</p>
            </div>
            <div class="doc-detail-section">
                <h4>Wyodrębnione dane <button class="btn btn-sm" onclick="toggleEditMode()">✏️ Edytuj</button></h4>
                <div class="extracted-data" id="extracted-data-view">
                    ${Object.entries(extractedData)
                        .filter(([k]) => !k.startsWith('_'))
                        .map(([k, v]) => `<div class="data-row"><span class="data-key">${k}:</span> <span class="data-value">${v}</span></div>`).join('') || '<p class="empty-state">Brak danych</p>'}
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
                <button class="btn btn-success" onclick="createExpenseFromDoc('${docId}')">💰 Utwórz wydatek</button>
                <button class="btn btn-danger" onclick="deleteDocument('${docId}'); closeDocumentModal();">🗑️ Usuń</button>
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
    const extractedData = { ...(currentDocData?.extracted_data || {}) };
    
    fields.forEach(field => {
        const input = document.getElementById(`edit-${field}`);
        if (input && input.value) {
            extractedData[field] = field.includes('amount') ? parseFloat(input.value) : input.value;
        }
    });
    
    try {
        await fetch(`${API_BASE}/documents/${docId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
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

// Expenses
let selectedExpenses = new Set();

async function loadExpenses() {
    try {
        const projectFilter = document.getElementById('expense-filter-project')?.value;
        const status = document.getElementById('expense-filter-status').value;
        const brQualified = document.getElementById('expense-filter-br').value;
        
        let url = `/expenses/?year=${currentFiscalYear}`;
        if (projectFilter) url += `&project_id=${projectFilter}`;
        if (status) url += `&status=${status}`;
        if (brQualified) url += `&br_qualified=${brQualified}`;
        
        const expenses = await apiCall(url);
        selectedExpenses.clear();
        updateBulkActionsBar();
        
        document.getElementById('expenses-table-body').innerHTML = expenses.length === 0 ? 
            '<tr><td colspan="10" class="empty-state">Brak wydatków</td></tr>' :
            expenses.map(e => `<tr>
                <td><input type="checkbox" class="expense-checkbox" data-id="${e.id}" onchange="toggleExpenseSelection('${e.id}', this.checked)"></td>
                <td><span class="project-tag">${getProjectName(e.project_id)}</span></td>
                <td>${e.invoice_date || '-'}</td>
                <td>${e.invoice_number || '-'}</td>
                <td>${e.vendor_name || '-'}</td>
                <td>${formatCurrencyWithCode(e.gross_amount, e.currency)}</td>
                <td>${getCategoryName(e.br_category) || '-'}</td>
                <td>
                    <select class="status-select status-${e.status}" onchange="changeExpenseStatus('${e.id}', this.value)">
                        <option value="draft" ${e.status === 'draft' ? 'selected' : ''}>Szkic</option>
                        <option value="classified" ${e.status === 'classified' ? 'selected' : ''}>Sklasyfikowany</option>
                        <option value="approved" ${e.status === 'approved' ? 'selected' : ''}>Zatwierdzony</option>
                        <option value="rejected" ${e.status === 'rejected' ? 'selected' : ''}>Odrzucony</option>
                    </select>
                </td>
                <td>
                    ${e.document_id ? `<button class="btn btn-small btn-outline" onclick="showDocumentDetail('${e.document_id}')" title="Pokaż dokument">📄</button>` : ''}
                    <button class="btn btn-small btn-secondary" onclick="showExpenseDetails('${e.id}')">Szczegóły</button>
                    <button class="btn btn-small btn-danger" onclick="deleteExpense('${e.id}')" title="Usuń">🗑️</button>
                </td>
            </tr>`).join('');
    } catch (e) { console.error('Error:', e); }
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
    try {
        const br = await apiCall(`/reports/annual/br-summary?fiscal_year=${year}&project_id=${PROJECT_ID}`);
        document.getElementById('annual-br-summary').innerHTML = `
            <p><strong>Projekt:</strong> ${br.project_name}</p>
            <p><strong>Suma kosztów B+R:</strong> ${formatCurrency(br.total_br_costs)}</p>
            <p><strong>Kwota odliczenia:</strong> <span style="color:var(--success);font-size:1.25rem">${formatCurrency(br.total_br_deduction)}</span></p>`;
        
        const ip = await apiCall(`/reports/annual/ip-box-summary?fiscal_year=${year}&project_id=${PROJECT_ID}`);
        document.getElementById('annual-ip-summary').innerHTML = `
            <p><strong>Przychody IP:</strong> ${formatCurrency(ip.ip_revenues)}</p>
            <p><strong>Wskaźnik nexus:</strong> ${(ip.nexus_ratio * 100).toFixed(2)}%</p>
            <p><strong>Podatek 5%:</strong> <span style="color:var(--success);font-size:1.25rem">${formatCurrency(ip.tax_5_percent)}</span></p>`;
        
        const monthly = await apiCall(`/reports/monthly?fiscal_year=${year}&project_id=${PROJECT_ID}`);
        const months = ['','Sty','Lut','Mar','Kwi','Maj','Cze','Lip','Sie','Wrz','Paź','Lis','Gru'];
        document.getElementById('monthly-reports-list').innerHTML = monthly.length === 0 ? '<p class="empty-state">Brak raportów</p>' :
            monthly.map(r => `<div class="document-item"><span>${months[r.month]} ${r.fiscal_year}</span><span>B+R: ${formatCurrency(r.br_expenses)}</span></div>`).join('');
    } catch (e) { console.error('Error:', e); }
}

async function generateMonthlyReport() {
    const year = document.getElementById('report-year').value;
    const month = prompt('Miesiąc (1-12):');
    if (!month || month < 1 || month > 12) { showToast('Nieprawidłowy miesiąc', 'error'); return; }
    try { await apiCall('/reports/monthly/generate', { method: 'POST', body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: parseInt(year), month: parseInt(month), regenerate: true }) }); showToast('Wygenerowano', 'success'); loadReports(); }
    catch (e) { showToast('Błąd', 'error'); }
}

async function generateAllReports() {
    for (let m = 1; m <= new Date().getMonth() + 1; m++) {
        try { await apiCall('/reports/monthly/generate', { method: 'POST', body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: currentFiscalYear, month: m, regenerate: false }) }); }
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

async function deleteExpense(id) {
    if (!confirm('Czy na pewno chcesz usunąć ten wydatek?')) return;
    try {
        await apiCall(`/expenses/${id}`, { method: 'DELETE' });
        showToast('Wydatek usunięty', 'success');
        document.getElementById('expense-modal').classList.remove('active');
        loadExpenses(); loadDashboard();
    } catch (e) { showToast('Błąd usuwania', 'error'); }
}

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
        
        // Render markdown content
        preview.innerHTML = `
            <div class="doc-content-header">
                <strong>${filename}</strong>
                <div class="doc-actions">
                    <button class="btn btn-sm btn-secondary" onclick="viewDocHistory('${projectId}', '${filename}')">📜 Historia</button>
                    <button class="btn btn-sm btn-secondary" onclick="downloadDoc('${projectId}', '${filename}')">⬇️ MD</button>
                    <button class="btn btn-sm btn-primary" onclick="downloadPdf('${projectId}', '${filename}')">📄 PDF</button>
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

function downloadDoc(projectId, filename) {
    // Download markdown file
    window.open(`${API_BASE}/expenses/project/${projectId}/docs/${filename}`, '_blank');
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
                    <button class="btn btn-sm btn-secondary" onclick="viewDocHistory('${projectId}', '${filename}')">📜 Historia</button>
                    <button class="btn btn-sm btn-secondary" onclick="viewDocContent('${projectId}', '${filename}')">← Aktualna</button>
                </div>
            </div>
            <div class="doc-markdown version-preview">${renderMarkdown(data.content)}</div>`;
    } catch (e) {
        showToast('Błąd ładowania wersji', 'error');
    }
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
            
            for (let slotIdx = 0; slotIdx < TIME_SLOTS.length; slotIdx++) {
                const slot = TIME_SLOTS[slotIdx];
                const rowClass = isWeekend ? 'weekend' : '';
                
                html += `<tr class="${rowClass}">`;
                
                // Day column (only on first slot)
                if (slotIdx === 0) {
                    html += `<td rowspan="${TIME_SLOTS.length}" class="day-cell ${isWeekend ? 'weekend' : ''}">${day} ${dayNames[dayOfWeek]}</td>`;
                }
                
                // Time slot
                html += `<td class="slot-cell">${slot.label}</td>`;
                
                // Project columns - CHECKBOXES
                let daySlotTotal = 0;
                for (const p of projects) {
                    const key = `${p.id}_${dateStr}_${slot.id}`;
                    const hours = timesheetData[key] || 0;
                    const checked = hours > 0;
                    daySlotTotal += hours;
                    
                    html += `<td class="check-cell">
                        <input type="checkbox" ${checked ? 'checked' : ''} 
                               data-project="${p.id}" data-date="${dateStr}" data-slot="${slot.id}"
                               onchange="toggleTimesheetBlock(this)" class="ts-checkbox">
                    </td>`;
                }
                
                // Row total
                html += `<td class="total-cell">${daySlotTotal > 0 ? daySlotTotal : ''}</td>`;
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
    const hours = checkbox.checked ? 4 : 0;
    const key = `${checkbox.dataset.project}_${checkbox.dataset.date}_${checkbox.dataset.slot}`;
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
        
        // Update row total
        const row = checkbox.closest('tr');
        const checkboxes = row.querySelectorAll('.ts-checkbox');
        let total = 0;
        checkboxes.forEach(cb => { if (cb.checked) total += 4; });
        row.querySelector('.total-cell').textContent = total > 0 ? total : '';
        
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
