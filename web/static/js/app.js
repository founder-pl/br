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
                      expenses: loadExpenses, reports: loadReports, clarifications: loadClarifications,
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

async function showDocumentDetail(docId, options = {}) {
    const { updateUrl = true } = options;
    try {
        if (updateUrl) {
            setUrlParam('doc', docId, true);
        }
        const doc = await apiCall(`/documents/${docId}/detail`);
        const modal = document.getElementById('document-modal');
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
            ${doc.extracted_data && Object.keys(doc.extracted_data).length > 0 ? `
                <div class="doc-detail-section">
                    <h4>Wyodrębnione dane</h4>
                    <div class="extracted-data">
                        ${Object.entries(doc.extracted_data)
                            .filter(([k]) => !k.startsWith('_'))
                            .map(([k, v]) => `<div class="data-row"><span class="data-key">${k}:</span> <span class="data-value">${v}</span></div>`).join('')}
                    </div>
                </div>
            ` : ''}
            ${doc.ocr_text ? `
                <div class="doc-detail-section">
                    <h4>Tekst OCR</h4>
                    <pre class="ocr-text">${doc.ocr_text}</pre>
                </div>
            ` : ''}
            ${doc.validation_errors && doc.validation_errors.length > 0 ? `
                <div class="doc-detail-section error-section">
                    <h4>Błędy</h4>
                    <ul>${doc.validation_errors.map(e => `<li>${e}</li>`).join('')}</ul>
                </div>
            ` : ''}
            <div class="doc-detail-actions">
                <button class="btn btn-primary" onclick="retryOcr('${docId}'); closeDocumentModal();">🔄 Powtórz OCR</button>
                <button class="btn btn-success" onclick="approveDocument('${docId}')">✅ Zatwierdź</button>
                <button class="btn btn-danger" onclick="deleteDocument('${docId}'); closeDocumentModal();">🗑️ Usuń</button>
            </div>
        `;
        modal.classList.add('active');
    } catch (e) { showToast('Błąd ładowania szczegółów', 'error'); }
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

// Expenses
async function loadExpenses() {
    try {
        const status = document.getElementById('expense-filter-status').value;
        const brQualified = document.getElementById('expense-filter-br').value;
        let url = `/expenses/?project_id=${PROJECT_ID}&year=${currentFiscalYear}`;
        if (status) url += `&status=${status}`;
        if (brQualified) url += `&br_qualified=${brQualified}`;
        
        const expenses = await apiCall(url);
        document.getElementById('expenses-table-body').innerHTML = expenses.length === 0 ? 
            '<tr><td colspan="8" class="empty-state">Brak wydatków</td></tr>' :
            expenses.map(e => `<tr>
                <td>${e.invoice_date || '-'}</td><td>${e.invoice_number || '-'}</td><td>${e.vendor_name || '-'}</td>
                <td>${formatCurrency(e.gross_amount)}</td><td>${getCategoryName(e.br_category) || '-'}</td>
                <td>${e.br_qualified ? (e.br_deduction_rate * 100) + '%' : '-'}</td>
                <td><span class="status-badge ${e.status}">${getStatusLabel(e.status)}</span></td>
                <td><button class="btn btn-small btn-secondary" onclick="showExpenseDetails('${e.id}')">Szczegóły</button></td>
            </tr>`).join('');
    } catch (e) { console.error('Error:', e); }
}

async function showExpenseDetails(id) {
    try {
        const e = await apiCall(`/expenses/${id}`);
        document.getElementById('expense-modal-content').innerHTML = `
            <p><strong>Nr faktury:</strong> ${e.invoice_number || '-'}</p>
            <p><strong>Data:</strong> ${e.invoice_date || '-'}</p>
            <p><strong>Dostawca:</strong> ${e.vendor_name || '-'} (NIP: ${e.vendor_nip || '-'})</p>
            <p><strong>Kwota brutto:</strong> ${formatCurrency(e.gross_amount)}</p>
            <hr><h4>Klasyfikacja B+R</h4>
            <p><strong>Kwalifikowany:</strong> ${e.br_qualified ? '✅ Tak' : '❌ Nie'}</p>
            <p><strong>Kategoria:</strong> ${getCategoryName(e.br_category) || '-'}</p>
            <p><strong>Stawka:</strong> ${e.br_deduction_rate * 100}%</p>
            <p><strong>Uzasadnienie:</strong> ${e.br_qualification_reason || '-'}</p>
            <div style="margin-top:1rem;">
                <button class="btn btn-primary" onclick="classifyExpense('${e.id}')">Zmień klasyfikację</button>
                <button class="btn btn-secondary" onclick="reclassifyWithLLM('${e.id}')">Reklasyfikuj AI</button>
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
function getStatusLabel(s) { return { pending: 'Oczekuje', processing: 'Przetwarzanie', completed: 'Gotowe', failed: 'Błąd', draft: 'Szkic', classified: 'Sklasyfikowane', generated: 'Wygenerowany' }[s] || s; }
function getCategoryName(c) { return { personnel_employment: 'Wynagrodzenia (umowa o pracę)', personnel_civil: 'Wynagrodzenia (cywilnoprawne)', materials: 'Materiały', equipment: 'Sprzęt', depreciation: 'Amortyzacja', expertise: 'Ekspertyzy', external_services: 'Usługi zewnętrzne' }[c] || c; }
function showToast(msg, type = 'info') { const t = document.createElement('div'); t.className = `toast ${type}`; t.textContent = msg; document.getElementById('toast-container').appendChild(t); setTimeout(() => t.remove(), 4000); }

// Modal
document.querySelector('.modal-close').addEventListener('click', () => document.getElementById('expense-modal').classList.remove('active'));
document.getElementById('expense-modal').addEventListener('click', (e) => { if (e.target.id === 'expense-modal') e.target.classList.remove('active'); });

// Filters
document.getElementById('expense-filter-status').addEventListener('change', loadExpenses);
document.getElementById('expense-filter-br').addEventListener('change', loadExpenses);
document.getElementById('report-year').addEventListener('change', loadReports);

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
