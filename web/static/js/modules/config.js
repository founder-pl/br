/**
 * AI Config Module
 */

async function loadAIConfig() {
    try {
        const config = await apiCall('/config/ai');
        
        document.getElementById('config-llm-provider').value = config.llm_provider || 'openai';
        document.getElementById('config-llm-model').value = config.llm_model || 'gpt-4';
        document.getElementById('config-ocr-provider').value = config.ocr_provider || 'tesseract';
        document.getElementById('config-auto-categorize').checked = config.auto_categorize !== false;
        document.getElementById('config-auto-justify').checked = config.auto_justify !== false;
        document.getElementById('config-currency-auto').checked = config.currency_auto_convert !== false;
        
    } catch (e) {
        console.error('Error loading AI config:', e);
        showToast('Błąd ładowania konfiguracji', 'error');
    }
}

async function saveAIConfig() {
    try {
        const config = {
            llm_provider: document.getElementById('config-llm-provider')?.value,
            llm_model: document.getElementById('config-llm-model')?.value,
            ocr_provider: document.getElementById('config-ocr-provider')?.value,
            auto_categorize: document.getElementById('config-auto-categorize')?.checked,
            auto_justify: document.getElementById('config-auto-justify')?.checked,
            currency_auto_convert: document.getElementById('config-currency-auto')?.checked
        };
        
        await apiCall('/config/ai', {
            method: 'PUT',
            body: JSON.stringify(config)
        });
        
        showToast('Konfiguracja zapisana', 'success');
    } catch (e) {
        console.error('Error saving AI config:', e);
        showToast('Błąd zapisu konfiguracji', 'error');
    }
}

async function testLLMConnection() {
    try {
        showToast('Testowanie połączenia...', 'info');
        const result = await apiCall('/config/ai/test-llm', { method: 'POST' });
        
        if (result.success) {
            showToast('Połączenie LLM działa poprawnie', 'success');
        } else {
            showToast(`Błąd LLM: ${result.error}`, 'error');
        }
    } catch (e) {
        showToast('Błąd testu LLM', 'error');
    }
}

async function testOCRConnection() {
    try {
        showToast('Testowanie OCR...', 'info');
        const result = await apiCall('/config/ai/test-ocr', { method: 'POST' });
        
        if (result.success) {
            showToast('OCR działa poprawnie', 'success');
        } else {
            showToast(`Błąd OCR: ${result.error}`, 'error');
        }
    } catch (e) {
        showToast('Błąd testu OCR', 'error');
    }
}

// Export
window.ConfigModule = {
    loadAIConfig,
    saveAIConfig,
    testLLMConnection,
    testOCRConnection
};
