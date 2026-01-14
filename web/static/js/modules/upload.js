/**
 * Upload/Documents Module
 */

function setupUploadListeners() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    
    if (dropZone) {
        dropZone.addEventListener('dragover', e => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });
        dropZone.addEventListener('click', () => fileInput?.click());
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', e => handleFiles(e.target.files));
    }
}

function handleFiles(files) { 
    Array.from(files).forEach(uploadFile); 
}

async function uploadFile(file) {
    const itemId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const list = document.getElementById('upload-list');
    
    if (list) {
        list.innerHTML += `
            <div class="upload-item" id="${itemId}">
                <span class="filename">${file.name}</span>
                <span class="status">Przesyłanie...</span>
                <div class="progress-bar"><div class="progress" style="width: 0%"></div></div>
            </div>
        `;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', PROJECT_ID);
    
    try {
        const response = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Upload failed');
        
        const doc = await response.json();
        const item = document.getElementById(itemId);
        if (item) {
            item.querySelector('.status').textContent = 'Przetwarzanie OCR...';
            item.querySelector('.progress').style.width = '50%';
        }
        
        pollDocumentStatus(doc.id, itemId);
    } catch (e) {
        const item = document.getElementById(itemId);
        if (item) {
            item.querySelector('.status').textContent = 'Błąd';
            item.classList.add('error');
        }
        showToast(`Błąd przesyłania: ${file.name}`, 'error');
    }
}

async function pollDocumentStatus(docId, itemId) {
    const maxAttempts = 60;
    let attempts = 0;
    
    const poll = async () => {
        try {
            const doc = await apiCall(`/documents/${docId}`);
            const item = document.getElementById(itemId);
            
            if (doc.status === 'processed' || doc.status === 'approved') {
                if (item) {
                    item.querySelector('.status').textContent = 'Gotowy';
                    item.querySelector('.progress').style.width = '100%';
                    item.classList.add('success');
                }
                loadRecentDocuments();
                return;
            }
            
            if (doc.status === 'error') {
                if (item) {
                    item.querySelector('.status').textContent = 'Błąd OCR';
                    item.classList.add('error');
                }
                return;
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 2000);
            }
        } catch (e) {
            console.error('Poll error:', e);
        }
    };
    
    poll();
}

async function loadRecentDocuments() {
    const container = document.getElementById('recent-documents');
    if (!container) return;
    
    try {
        const docs = await apiCall('/documents/?limit=20');
        
        if (!docs.length) {
            container.innerHTML = '<p class="empty">Brak dokumentów</p>';
            return;
        }
        
        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Plik</th>
                        <th>Status</th>
                        <th>Data</th>
                        <th>Akcje</th>
                    </tr>
                </thead>
                <tbody>
                    ${docs.map(d => `
                        <tr>
                            <td>${d.filename}</td>
                            <td><span class="status-badge status-${d.status}">${d.status}</span></td>
                            <td>${formatDate(d.created_at)}</td>
                            <td>
                                <button class="btn btn-sm" onclick="showDocumentDetail('${d.id}')">👁️</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteDocument('${d.id}')">🗑️</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        container.innerHTML = '<p class="error">Błąd ładowania dokumentów</p>';
    }
}

async function deleteDocument(docId) {
    const confirmed = await openConfirmModal({
        title: 'Usuń dokument',
        message: 'Czy na pewno chcesz usunąć ten dokument?',
        confirmText: 'Usuń'
    });
    if (!confirmed) return;
    
    try {
        await apiCall(`/documents/${docId}`, { method: 'DELETE' });
        showToast('Dokument usunięty', 'success');
        loadRecentDocuments();
    } catch (e) {
        showToast('Błąd usuwania dokumentu', 'error');
    }
}

async function retryOcr(docId) {
    try {
        showToast('Ponowne przetwarzanie OCR...', 'info');
        await apiCall(`/documents/${docId}/retry-ocr`, { method: 'POST' });
        showToast('OCR uruchomiony ponownie', 'success');
    } catch (e) {
        showToast('Błąd OCR', 'error');
    }
}

function getDocTypeName(type) {
    const types = {
        'invoice': 'Faktura',
        'receipt': 'Paragon',
        'contract': 'Umowa',
        'other': 'Inny'
    };
    return types[type] || type || 'Nieznany';
}

// Export
window.UploadModule = {
    setupUploadListeners,
    handleFiles,
    uploadFile,
    pollDocumentStatus,
    loadRecentDocuments,
    deleteDocument,
    retryOcr,
    getDocTypeName
};
