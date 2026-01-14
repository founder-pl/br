/**
 * Document Generator Module
 */

let docTemplatesCache = [];
let docProjectsCache = [];
let currentDocCategory = '';

async function loadDocTemplates() {
    try {
        const result = await apiCall('/doc-generator/templates');
        docTemplatesCache = result.templates || [];
        
        const filterResult = await apiCall('/doc-generator/filter-options');
        docProjectsCache = filterResult.projects || [];
        
        const projectSelect = document.getElementById('docgen-project-filter');
        if (projectSelect && filterResult.projects) {
            projectSelect.innerHTML = filterResult.projects.map(p => 
                `<option value="${p.id}">${p.name}</option>`
            ).join('');
        }
        
        renderDocCategories();
        renderDocTemplates();
    } catch (e) {
        console.error('Error loading doc templates:', e);
        showToast('Błąd ładowania szablonów', 'error');
    }
}

function renderDocCategories() {
    const container = document.getElementById('docgen-categories');
    if (!container) return;
    
    const categories = [...new Set(docTemplatesCache.map(t => t.category))];
    container.innerHTML = `
        <button class="category-btn ${!currentDocCategory ? 'active' : ''}" 
                onclick="filterDocCategory('')">Wszystkie</button>
        ${categories.map(cat => `
            <button class="category-btn ${currentDocCategory === cat ? 'active' : ''}"
                    onclick="filterDocCategory('${cat}')">${getCategoryName(cat)}</button>
        `).join('')}
    `;
}

function getCategoryName(category) {
    const names = {
        'tax': 'Podatkowe',
        'report': 'Raporty',
        'legal': 'Prawne',
        'procedure': 'Procedury'
    };
    return names[category] || category;
}

function filterDocCategory(category) {
    currentDocCategory = category;
    renderDocCategories();
    renderDocTemplates();
}

function renderDocTemplates() {
    const container = document.getElementById('docgen-templates-list');
    if (!container) return;
    
    const filtered = currentDocCategory 
        ? docTemplatesCache.filter(t => t.category === currentDocCategory)
        : docTemplatesCache;
    
    if (filtered.length === 0) {
        container.innerHTML = '<p class="empty">Brak szablonów w tej kategorii</p>';
        return;
    }
    
    container.innerHTML = filtered.map(t => `
        <div class="template-card" onclick="showDocTemplateDetail('${t.id}')">
            <h4>${t.name}</h4>
            <p>${t.description || ''}</p>
            <div class="template-meta">
                <span class="badge badge-${t.category}">${getCategoryName(t.category)}</span>
                <span class="time-scope">${getTimeScopeName(t.time_scope)}</span>
            </div>
        </div>
    `).join('');
}

function getTimeScopeName(scope) {
    const names = {
        'monthly': 'Miesięczny',
        'yearly': 'Roczny',
        'project': 'Projektowy'
    };
    return names[scope] || scope;
}

async function showDocTemplateDetail(templateId) {
    try {
        const template = await apiCall(`/doc-generator/templates/${templateId}`);
        
        const projectId = document.getElementById('docgen-project-filter')?.value || PROJECT_ID;
        const year = document.getElementById('docgen-year')?.value || currentFiscalYear;
        const month = document.getElementById('docgen-month')?.value || new Date().getMonth() + 1;
        
        document.getElementById('docgen-detail-title').textContent = template.name;
        document.getElementById('docgen-detail-desc').textContent = template.description || '';
        
        const requirementsHtml = (template.data_requirements || []).map(r => 
            `<li><strong>${r.source_name}</strong>: ${r.description || ''}</li>`
        ).join('');
        document.getElementById('docgen-detail-requirements').innerHTML = 
            requirementsHtml || '<li>Brak wymagań</li>';
        
        document.getElementById('docgen-generate-btn').onclick = () => 
            generateDocument(templateId, projectId, year, month);
        document.getElementById('docgen-preview-btn').onclick = () => 
            previewDocumentData(templateId, projectId, year, month);
        
        document.getElementById('docgen-detail-modal').classList.add('active');
        
        document.getElementById('docgen-preview-content').innerHTML = '';
        document.getElementById('docgen-generated-content').innerHTML = '';
        
    } catch (e) {
        console.error('Error loading template:', e);
        showToast('Błąd ładowania szablonu', 'error');
    }
}

function closeDocDetailModal() {
    document.getElementById('docgen-detail-modal')?.classList.remove('active');
}

async function generateDocument(templateId, projectId, year, month) {
    try {
        showToast('Generowanie dokumentu...', 'info');
        
        const result = await apiCall('/doc-generator/generate', {
            method: 'POST',
            body: JSON.stringify({
                template_id: templateId,
                params: { project_id: projectId, year: parseInt(year), month: parseInt(month) },
                use_llm: document.getElementById('docgen-use-llm')?.checked || false
            })
        });
        
        const contentEl = document.getElementById('docgen-generated-content');
        if (contentEl) {
            contentEl.innerHTML = `
                <div class="generated-doc">
                    <div class="doc-header">
                        <h4>${result.template_name}</h4>
                        <span class="generated-at">Wygenerowano: ${result.generated_at}</span>
                    </div>
                    <div class="doc-content markdown-content">${marked.parse(result.content)}</div>
                    <div class="doc-actions">
                        <button class="btn btn-sm btn-secondary" onclick="copyDocContent()">📋 Kopiuj</button>
                        <button class="btn btn-sm btn-primary" onclick="downloadDocContent('${result.template_name}')">💾 Pobierz</button>
                    </div>
                </div>
            `;
        }
        
        showToast('Dokument wygenerowany', 'success');
    } catch (e) {
        console.error('Error generating document:', e);
        showToast('Błąd generowania dokumentu', 'error');
    }
}

async function previewDocumentData(templateId, projectId, year, month) {
    try {
        const result = await apiCall('/doc-generator/preview-data', {
            method: 'POST',
            body: JSON.stringify({
                template_id: templateId,
                params: { project_id: projectId, year: parseInt(year), month: parseInt(month) }
            })
        });
        
        const previewEl = document.getElementById('docgen-preview-content');
        if (previewEl) {
            previewEl.innerHTML = `<pre class="data-preview">${JSON.stringify(result.data, null, 2)}</pre>`;
        }
    } catch (e) {
        console.error('Error previewing data:', e);
        showToast('Błąd podglądu danych', 'error');
    }
}

function copyDocContent() {
    const content = document.querySelector('.doc-content')?.textContent || '';
    navigator.clipboard.writeText(content).then(() => {
        showToast('Skopiowano do schowka', 'success');
    }).catch(() => {
        showToast('Błąd kopiowania', 'error');
    });
}

function downloadDocContent(filename) {
    const content = document.querySelector('.doc-content')?.innerHTML || '';
    const blob = new Blob([content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename.replace(/\s+/g, '_')}.html`;
    a.click();
    URL.revokeObjectURL(url);
}

// Export
window.DocGeneratorModule = {
    docTemplatesCache,
    docProjectsCache,
    loadDocTemplates,
    renderDocCategories,
    filterDocCategory,
    renderDocTemplates,
    showDocTemplateDetail,
    closeDocDetailModal,
    generateDocument,
    previewDocumentData,
    copyDocContent,
    downloadDocContent
};
