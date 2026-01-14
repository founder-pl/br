/**
 * Projects Module
 */

let projectsCache = [];

async function loadProjects() {
    try {
        projectsCache = await apiCall('/projects/');
        
        if (projectsCache.length === 0) {
            document.getElementById('projects-list').innerHTML = `
                <div class="empty-state-card">
                    <p>Brak projektów B+R</p>
                    <button class="btn btn-primary" onclick="showCreateProjectModal()">➕ Utwórz projekt</button>
                </div>`;
            return;
        }
        
        document.getElementById('projects-list').innerHTML = projectsCache.map(p => `
            <div class="project-card" data-id="${p.id}">
                <div class="project-header">
                    <h3>${p.name}</h3>
                    <span class="project-year">${p.fiscal_year || '-'}</span>
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
        showToast('Błąd ładowania projektów', 'error'); 
    }
}

function showCreateProjectModal() {
    const name = prompt('Nazwa projektu:');
    if (!name) return;
    const description = prompt('Opis projektu (opcjonalnie):');
    const fiscalYear = prompt('Rok fiskalny:', new Date().getFullYear().toString());
    createProject(name, description, parseInt(fiscalYear) || new Date().getFullYear());
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

async function loadProjectsForFilter() {
    try {
        projectsCache = await apiCall('/projects/');
        
        const filterSelect = document.getElementById('expense-filter-project');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">Wszystkie projekty</option>' +
                projectsCache.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        }
        
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

async function viewProjectDocs(projectId) {
    navigateTo('doc-generator');
    setTimeout(() => {
        const projectSelect = document.getElementById('docgen-project-filter');
        if (projectSelect) projectSelect.value = projectId;
    }, 100);
}

async function generateProjectSummary(projectId) {
    showToast('Generowanie podsumowania...', 'info');
    try {
        await apiCall('/doc-generator/generate', {
            method: 'POST',
            body: JSON.stringify({
                template_id: 'project_card',
                params: { project_id: projectId, year: currentFiscalYear }
            })
        });
        showToast('Podsumowanie wygenerowane', 'success');
        viewProjectDocs(projectId);
    } catch (e) {
        showToast('Błąd generowania', 'error');
    }
}

// Export
window.ProjectsModule = {
    projectsCache,
    loadProjects,
    showCreateProjectModal,
    createProject,
    editProject,
    deleteProject,
    viewProjectExpenses,
    loadProjectsForFilter,
    getProjectName,
    viewProjectDocs,
    generateProjectSummary
};
