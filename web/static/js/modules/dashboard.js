/**
 * Dashboard Module
 */

const DEFAULT_DASHBOARD_LAYOUT = [
    'summary', 'recent-docs', 'categories', 'top-vendors',
    'timesheet', 'git-activity', 'monthly-trend', 'clarifications'
];

function getDashboardLayout() {
    const saved = localStorage.getItem('dashboardLayout');
    return saved ? JSON.parse(saved) : DEFAULT_DASHBOARD_LAYOUT;
}

function saveDashboardLayout(layout) {
    localStorage.setItem('dashboardLayout', JSON.stringify(layout));
}

function toggleDashboardConfig() {
    const panel = document.getElementById('dashboard-config');
    if (panel) panel.classList.toggle('hidden');
    updateModuleSelect();
}

function updateModuleSelect() {
    const select = document.getElementById('module-select');
    if (!select) return;
    const current = getDashboardLayout();
    const allModules = ['summary', 'recent-docs', 'categories', 'top-vendors', 
                        'timesheet', 'git-activity', 'monthly-trend', 'clarifications'];
    const available = allModules.filter(m => !current.includes(m));
    select.innerHTML = '<option value="">Wybierz moduł...</option>' +
        available.map(m => `<option value="${m}">${getModuleName(m)}</option>`).join('');
}

function getModuleName(id) {
    const names = {
        'summary': 'Podsumowanie',
        'recent-docs': 'Ostatnie dokumenty',
        'categories': 'Kategorie wydatków',
        'top-vendors': 'Top dostawcy',
        'timesheet': 'Czas pracy',
        'git-activity': 'Aktywność Git',
        'monthly-trend': 'Trend miesięczny',
        'clarifications': 'Wyjaśnienia'
    };
    return names[id] || id;
}

function addDashboardModule(moduleId) {
    if (!moduleId) return;
    const layout = getDashboardLayout();
    if (!layout.includes(moduleId)) {
        layout.push(moduleId);
        saveDashboardLayout(layout);
        renderDashboard();
    }
}

function removeDashboardModule(moduleId) {
    const layout = getDashboardLayout().filter(m => m !== moduleId);
    saveDashboardLayout(layout);
    renderDashboard();
}

function resetDashboardConfig() {
    localStorage.removeItem('dashboardLayout');
    renderDashboard();
    showToast('Układ dashboardu zresetowany', 'success');
}

function renderDashboard() {
    const grid = document.getElementById('dashboard-grid');
    if (!grid) return;
    const layout = getDashboardLayout();
    grid.innerHTML = layout.map(moduleId => `
        <div class="dashboard-module" data-module="${moduleId}" id="module-${moduleId}">
            <div class="module-header">
                <h3>${getModuleName(moduleId)}</h3>
                <button class="btn-icon" onclick="removeDashboardModule('${moduleId}')" title="Usuń">×</button>
            </div>
            <div class="module-content" id="content-${moduleId}">
                <div class="loading">Ładowanie...</div>
            </div>
        </div>
    `).join('');
    updateModuleSelect();
    loadDashboardModules();
}

async function loadDashboard() {
    renderDashboard();
}

async function loadDashboardModules() {
    const layout = getDashboardLayout();
    
    try {
        const summary = await apiCall(`/reports/summary/${PROJECT_ID}/${currentFiscalYear}`);
        
        for (const moduleId of layout) {
            const container = document.getElementById(`content-${moduleId}`);
            if (!container) continue;
            
            switch (moduleId) {
                case 'summary':
                    loadSummaryModule(container, summary);
                    break;
                case 'recent-docs':
                    await loadRecentDocsModule(container);
                    break;
                case 'categories':
                    loadCategoryModule(container, summary);
                    break;
                case 'top-vendors':
                    await loadTopVendorsModule(container);
                    break;
                case 'timesheet':
                    await loadTimesheetModule(container);
                    break;
                case 'git-activity':
                    await loadGitActivityModule(container);
                    break;
                case 'monthly-trend':
                    await loadMonthlyTrendModule(container);
                    break;
                case 'clarifications':
                    await loadClarificationsModule(container);
                    break;
            }
        }
    } catch (e) {
        console.error('Dashboard error:', e);
    }
}

function loadSummaryModule(container, summary) {
    container.innerHTML = `
        <div class="summary-stats">
            <div class="stat-item">
                <span class="stat-value">${formatCurrency(summary.total_expenses)}</span>
                <span class="stat-label">Wydatki ogółem</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${formatCurrency(summary.br_expenses)}</span>
                <span class="stat-label">Kwalifikowane B+R</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${summary.documents_count || 0}</span>
                <span class="stat-label">Dokumenty</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${summary.pending_documents || 0}</span>
                <span class="stat-label">Do weryfikacji</span>
            </div>
        </div>
    `;
}

async function loadRecentDocsModule(container) {
    try {
        const docs = await apiCall('/documents/?limit=5');
        if (!docs.length) {
            container.innerHTML = '<p class="empty">Brak dokumentów</p>';
            return;
        }
        container.innerHTML = `<ul class="doc-list">${docs.map(d => `
            <li onclick="showDocumentDetail('${d.id}')">
                <span class="doc-name">${d.filename}</span>
                <span class="doc-status status-${d.status}">${d.status}</span>
            </li>
        `).join('')}</ul>`;
    } catch (e) {
        container.innerHTML = '<p class="error">Błąd ładowania</p>';
    }
}

function loadCategoryModule(container, summary) {
    const cats = summary.categories || {};
    if (Object.keys(cats).length === 0) {
        container.innerHTML = '<p class="empty">Brak danych</p>';
        return;
    }
    container.innerHTML = `<ul class="category-list">${Object.entries(cats).map(([cat, data]) => `
        <li>
            <span class="cat-name">${cat || 'Bez kategorii'}</span>
            <span class="cat-value">${formatCurrency(data.amount || data)}</span>
        </li>
    `).join('')}</ul>`;
}

async function loadTopVendorsModule(container) {
    try {
        const vendors = await apiCall(`/reports/top-vendors/${PROJECT_ID}/${currentFiscalYear}?limit=5`);
        if (!vendors.length) {
            container.innerHTML = '<p class="empty">Brak danych</p>';
            return;
        }
        container.innerHTML = `<ul class="vendor-list">${vendors.map(v => `
            <li>
                <span class="vendor-name">${v.vendor_name || 'Nieznany'}</span>
                <span class="vendor-value">${formatCurrency(v.total_amount)}</span>
            </li>
        `).join('')}</ul>`;
    } catch (e) {
        container.innerHTML = '<p class="error">Błąd ładowania</p>';
    }
}

async function loadTimesheetModule(container) {
    try {
        const data = await apiCall(`/timesheet/summary/${PROJECT_ID}?year=${currentFiscalYear}`);
        container.innerHTML = `
            <div class="timesheet-summary">
                <p><strong>${data.total_hours || 0}</strong> godzin B+R</p>
                <p><strong>${data.entries_count || 0}</strong> wpisów</p>
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<p class="empty">Brak danych</p>';
    }
}

async function loadGitActivityModule(container) {
    try {
        const data = await apiCall(`/git-timesheet/summary?project_id=${PROJECT_ID}&year=${currentFiscalYear}`);
        container.innerHTML = `
            <div class="git-summary">
                <p><strong>${data.total_commits || 0}</strong> commitów</p>
                <p><strong>${data.total_hours || 0}</strong> godzin</p>
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<p class="empty">Brak danych</p>';
    }
}

async function loadMonthlyTrendModule(container) {
    try {
        const reports = await apiCall(`/reports/monthly/${PROJECT_ID}/${currentFiscalYear}`);
        if (!reports.length) {
            container.innerHTML = '<p class="empty">Brak danych</p>';
            return;
        }
        const months = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'];
        container.innerHTML = `<div class="trend-chart">${reports.slice(-6).map(r => `
            <div class="trend-bar">
                <div class="bar" style="height: ${Math.min(100, (r.total_expenses / 5000) * 100)}%"></div>
                <span class="month">${months[r.month - 1]}</span>
            </div>
        `).join('')}</div>`;
    } catch (e) {
        container.innerHTML = '<p class="error">Błąd ładowania</p>';
    }
}

async function loadClarificationsModule(container) {
    try {
        const data = await apiCall('/clarifications/?limit=5&unanswered_only=true');
        const count = data.length || 0;
        container.innerHTML = `
            <div class="clarifications-summary">
                <p><strong>${count}</strong> pytań do wyjaśnienia</p>
                ${count > 0 ? '<button class="btn btn-sm btn-primary" onclick="navigateTo(\'expenses\')">Zobacz</button>' : ''}
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<p class="empty">Brak wyjaśnień</p>';
    }
}

// Export
window.DashboardModule = {
    getDashboardLayout,
    saveDashboardLayout,
    toggleDashboardConfig,
    addDashboardModule,
    removeDashboardModule,
    resetDashboardConfig,
    renderDashboard,
    loadDashboard,
    loadDashboardModules
};
