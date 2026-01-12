/**
 * System B+R - Main Application JavaScript
 */

const API_BASE = '/api';
const PROJECT_ID = '00000000-0000-0000-0000-000000000001';
let currentFiscalYear = 2025;

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.page));
});

function navigateTo(page) {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    
    const loaders = { dashboard: loadDashboard, upload: loadRecentDocuments, 
                      expenses: loadExpenses, reports: loadReports, clarifications: loadClarifications,
                      integrations: loadIntegrations };
    if (loaders[page]) loaders[page]();
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

// Upload
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', (e) => { e.preventDefault(); uploadArea.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
fileInput.addEventListener('change', () => handleFiles(fileInput.files));

function handleFiles(files) { Array.from(files).forEach(uploadFile); }

async function uploadFile(file) {
    const itemId = `upload-${Date.now()}`;
    const documentType = document.getElementById('document-type').value;
    
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
        const response = await fetch(`${API_BASE}/documents/upload?project_id=${PROJECT_ID}&document_type=${documentType}`, { method: 'POST', body: formData });
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
            docs.map(d => `<div class="document-item"><span>📄 ${d.filename}</span><span class="status-badge ${d.ocr_status}">${getStatusLabel(d.ocr_status)}</span></div>`).join('');
        document.getElementById('recent-documents').innerHTML = html;
        document.getElementById('uploaded-documents').innerHTML = html;
    } catch (e) { console.error('Error:', e); }
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

// Init
document.addEventListener('DOMContentLoaded', loadDashboard);
