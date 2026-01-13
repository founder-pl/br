/**
 * BR Documentation Markdown Renderer
 * 
 * Converts Markdown to HTML with support for:
 * - Headers (h1, h2, h3)
 * - Tables with header detection
 * - Bold, italic, code inline formatting
 * - Numbered lists
 * - Horizontal rules
 * 
 * Usage:
 *   const html = MarkdownRenderer.render(markdownText);
 */

const MarkdownRenderer = (function() {
    'use strict';
    
    /**
     * Process inline formatting (bold, italic, code)
     */
    function processInlineFormatting(text) {
        if (!text) return '';
        return text
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    }
    
    /**
     * Check if a line is a table separator row (|---|---|)
     */
    function isTableSeparator(line) {
        if (!line) return false;
        const cleaned = line.replace(/\|/g, '').trim();
        return /^[-:\s]+$/.test(cleaned) && cleaned.length > 0;
    }
    
    /**
     * Check if line is a table row (starts and ends with |)
     */
    function isTableRow(line) {
        if (!line) return false;
        const trimmed = line.trim();
        return trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 2;
    }
    
    /**
     * Parse a table row into cells
     */
    function parseTableRow(row) {
        if (!row) return [];
        // Split by | and filter out empty strings from start/end
        const parts = row.split('|');
        // Remove first and last empty elements
        if (parts.length > 0 && parts[0].trim() === '') parts.shift();
        if (parts.length > 0 && parts[parts.length - 1].trim() === '') parts.pop();
        return parts.map(c => c.trim());
    }
    
    /**
     * Convert collected table rows to HTML
     */
    function renderTable(tableRows) {
        if (!tableRows || tableRows.length === 0) return '';
        
        // Find separator row index
        let separatorIdx = -1;
        for (let i = 0; i < tableRows.length; i++) {
            if (isTableSeparator(tableRows[i])) {
                separatorIdx = i;
                break;
            }
        }
        
        let html = '<table class="md-table">';
        
        // If we have a separator, rows before it are headers
        const hasHeader = separatorIdx > 0;
        
        for (let i = 0; i < tableRows.length; i++) {
            const row = tableRows[i];
            
            // Skip separator rows
            if (isTableSeparator(row)) {
                continue;
            }
            
            const cells = parseTableRow(row);
            if (cells.length === 0) continue;
            
            const isHeader = hasHeader && i < separatorIdx;
            const tag = isHeader ? 'th' : 'td';
            
            html += '<tr>' + cells.map(c => `<${tag}>${processInlineFormatting(c)}</${tag}>`).join('') + '</tr>';
        }
        
        html += '</table>';
        return html;
    }
    
    /**
     * Main render function - converts markdown to HTML
     */
    function render(markdown) {
        if (!markdown) return '';
        
        const lines = markdown.split('\n');
        let html = '';
        let inTable = false;
        let tableRows = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Table handling - check if current line is a table row
            if (isTableRow(line)) {
                if (!inTable) {
                    inTable = true;
                    tableRows = [];
                }
                tableRows.push(line);
                continue;
            } else if (inTable) {
                // End of table - render it
                html += renderTable(tableRows);
                inTable = false;
                tableRows = [];
            }
            
            // Headers (check for exact start)
            if (line.startsWith('### ')) {
                html += `<h3>${processInlineFormatting(line.substring(4))}</h3>`;
            } else if (line.startsWith('## ')) {
                html += `<h2>${processInlineFormatting(line.substring(3))}</h2>`;
            } else if (line.startsWith('# ')) {
                html += `<h1>${processInlineFormatting(line.substring(2))}</h1>`;
            } else if (line.trim() === '---') {
                html += '<hr>';
            } else if (line.trim() === '') {
                // Empty line - add spacing
                html += '<div class="spacer"></div>';
            } else {
                // Process inline formatting
                let processed = processInlineFormatting(line);
                
                // Numbered lists (1. Item)
                const listMatch = line.match(/^(\d+)\.\s+(.+)$/);
                if (listMatch) {
                    html += `<div class="list-item"><span class="list-num">${listMatch[1]}.</span> ${processInlineFormatting(listMatch[2])}</div>`;
                } else {
                    html += `<p>${processed}</p>`;
                }
            }
        }
        
        // Close any remaining table
        if (inTable && tableRows.length > 0) {
            html += renderTable(tableRows);
        }
        
        return html;
    }
    
    // Public API
    return {
        render: render,
        processInlineFormatting: processInlineFormatting,
        renderTable: renderTable
    };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MarkdownRenderer;
}
