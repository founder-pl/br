/**
 * Reports Module
 */

let reportsCache = [];

async function loadReports() {
    const container = document.getElementById('reports-list');
    if (!container) return;
    
    const year = document.getElementById('report-year')?.value || currentFiscalYear;
    
    try {
        reportsCache = await apiCall(`/reports/monthly/${PROJECT_ID}/${year}`);
        
        if (!reportsCache.length) {
            container.innerHTML = '<p class="empty">Brak raportów dla wybranego roku</p>';
            return;
        }
        
        const months = ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
                        'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień'];
        
        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Miesiąc</th>
                        <th>Wydatki</th>
                        <th>B+R</th>
                        <th>Przychody</th>
                        <th>Status</th>
                        <th>Akcje</th>
                    </tr>
                </thead>
                <tbody>
                    ${reportsCache.map(r => `
                        <tr>
                            <td>${months[r.month - 1]} ${r.fiscal_year}</td>
                            <td>${formatCurrency(r.total_expenses)}</td>
                            <td>${formatCurrency(r.br_expenses)}</td>
                            <td>${formatCurrency(r.total_revenues)}</td>
                            <td><span class="status-badge status-${r.status}">${r.status}</span></td>
                            <td>
                                <button class="btn btn-sm" onclick="showReportDetails(${r.fiscal_year}, ${r.month})">👁️</button>
                                <button class="btn btn-sm btn-primary" onclick="regenerateReport(${r.fiscal_year}, ${r.month})">🔄</button>
                                <button class="btn btn-sm btn-success" onclick="exportReport(${r.fiscal_year}, ${r.month})">📥</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (e) {
        console.error('Error loading reports:', e);
        container.innerHTML = '<p class="error">Błąd ładowania raportów</p>';
    }
}

async function showReportDetails(year, month) {
    navigateTo('expenses', { year, month });
    setTimeout(() => {
        document.getElementById('expense-filter-year').value = year;
        document.getElementById('expense-filter-month').value = month;
        loadExpenses();
    }, 100);
}

async function regenerateReport(year, month) {
    try {
        showToast('Regenerowanie raportu...', 'info');
        await apiCall('/reports/monthly/generate', {
            method: 'POST',
            body: JSON.stringify({
                project_id: PROJECT_ID,
                fiscal_year: year,
                month: month,
                regenerate: true,
                preprocess: true
            })
        });
        showToast('Raport zregenerowany', 'success');
        loadReports();
    } catch (e) {
        showToast('Błąd regenerowania raportu', 'error');
    }
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
    if (!month || month < 1 || month > 12) { 
        showToast('Nieprawidłowy miesiąc', 'error'); 
        return; 
    }
    try { 
        await apiCall('/reports/monthly/generate', { 
            method: 'POST', 
            body: JSON.stringify({ project_id: PROJECT_ID, fiscal_year: parseInt(year), month: parseInt(month), regenerate: true, preprocess: true }) 
        }); 
        showToast('Wygenerowano', 'success'); 
        loadReports(); 
    } catch (e) { 
        showToast('Błąd', 'error'); 
    }
}

async function exportReport(year, month) {
    try {
        const response = await fetch(`${API_BASE}/reports/export/monthly?project_id=${PROJECT_ID}&year=${year}&month=${month}`);
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `raport_${year}_${month}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
        
        showToast('Raport wyeksportowany', 'success');
    } catch (e) {
        showToast('Błąd eksportu', 'error');
    }
}

async function exportAllExpenses() {
    try {
        const year = document.getElementById('report-year')?.value || currentFiscalYear;
        const response = await fetch(`${API_BASE}/reports/export/expenses?project_id=${PROJECT_ID}&year=${year}`);
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `wydatki_${year}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
        
        showToast('Wydatki wyeksportowane', 'success');
    } catch (e) {
        showToast('Błąd eksportu', 'error');
    }
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
    } catch (e) {
        showToast('Błąd przetwarzania', 'error');
    }
}

// Export
window.ReportsModule = {
    reportsCache,
    loadReports,
    showReportDetails,
    regenerateReport,
    regenerateAllMonthlyReports,
    generateMonthlyReport,
    exportReport,
    exportAllExpenses,
    processAllExpensesForYear
};
