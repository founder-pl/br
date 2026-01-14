"""
CSS styles for document rendering.
"""
from enum import Enum


class StylePreset(str, Enum):
    """Available style presets"""
    DEFAULT = "default"
    BR_DOCUMENT = "br_document"
    MINIMAL = "minimal"
    PRINT = "print"


def get_default_css() -> str:
    """Get default CSS for HTML documents"""
    return """
/* Base styles */
:root {
    --primary-color: #2563eb;
    --text-color: #1f2937;
    --muted-color: #6b7280;
    --border-color: #e5e7eb;
    --bg-color: #ffffff;
    --code-bg: #f3f4f6;
}

* {
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-color);
    background: var(--bg-color);
    margin: 0;
    padding: 20px;
}

.document {
    max-width: 800px;
    margin: 0 auto;
    padding: 40px;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
    line-height: 1.3;
}

h1 { font-size: 2em; border-bottom: 2px solid var(--primary-color); padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1.1em; }

p {
    margin: 1em 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.9em;
}

th, td {
    padding: 10px 12px;
    border: 1px solid var(--border-color);
    text-align: left;
}

th {
    background: var(--code-bg);
    font-weight: 600;
}

tr:nth-child(even) {
    background: #f9fafb;
}

/* Code */
code {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.9em;
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 3px;
}

pre {
    background: var(--code-bg);
    padding: 16px;
    overflow-x: auto;
    border-radius: 6px;
    border: 1px solid var(--border-color);
}

pre code {
    background: none;
    padding: 0;
}

/* Lists */
ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin: 0.5em 0;
}

/* Links */
a {
    color: var(--primary-color);
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid var(--primary-color);
    margin: 1em 0;
    padding: 0.5em 1em;
    background: #f8fafc;
    color: var(--muted-color);
}

/* TOC */
.toc {
    background: #f8fafc;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 20px;
    margin-bottom: 2em;
}

.toc ul {
    margin: 0;
    padding-left: 1.5em;
}

/* Footnotes */
.footnotes {
    margin-top: 3em;
    padding-top: 1em;
    border-top: 1px solid var(--border-color);
    font-size: 0.9em;
    color: var(--muted-color);
}

.footnotes a {
    color: var(--primary-color);
}

/* Print styles */
@media print {
    body {
        padding: 0;
    }
    .document {
        box-shadow: none;
        padding: 0;
        max-width: none;
    }
}
"""


def get_br_document_css() -> str:
    """Get CSS styled for B+R documentation"""
    return """
/* B+R Document Styles */
:root {
    --primary-color: #1e40af;
    --accent-color: #059669;
    --warning-color: #d97706;
    --error-color: #dc2626;
    --text-color: #1f2937;
    --muted-color: #6b7280;
    --border-color: #d1d5db;
    --bg-color: #ffffff;
}

@page {
    size: A4;
    margin: 2cm;
    @top-right {
        content: "Dokumentacja B+R";
        font-size: 10px;
        color: #6b7280;
    }
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 10px;
    }
}

body {
    font-family: 'Times New Roman', 'Georgia', serif;
    font-size: 12pt;
    line-height: 1.5;
    color: var(--text-color);
}

.document {
    max-width: 100%;
}

/* Header with company info */
.document-header {
    border-bottom: 2px solid var(--primary-color);
    padding-bottom: 1em;
    margin-bottom: 2em;
}

h1 {
    font-size: 18pt;
    color: var(--primary-color);
    border-bottom: none;
    text-align: center;
    margin-bottom: 1em;
}

h2 {
    font-size: 14pt;
    color: var(--primary-color);
    border-bottom: 1px solid var(--border-color);
    page-break-after: avoid;
}

h3 {
    font-size: 12pt;
    font-weight: bold;
}

/* Financial tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th {
    background: #e5e7eb;
    font-weight: bold;
    text-align: left;
}

th, td {
    padding: 8px 10px;
    border: 1px solid var(--border-color);
}

/* Currency amounts - right align */
td.amount, th.amount {
    text-align: right;
    font-family: 'Consolas', monospace;
}

/* Summary rows */
tr.summary {
    font-weight: bold;
    background: #f3f4f6;
}

tr.total {
    font-weight: bold;
    background: #dbeafe;
}

/* Qualified B+R highlight */
.br-qualified {
    background: #dcfce7;
}

.br-not-qualified {
    background: #fef2f2;
}

/* Nexus indicator */
.nexus-value {
    font-size: 16pt;
    font-weight: bold;
    color: var(--accent-color);
}

.nexus-warning {
    color: var(--warning-color);
}

/* Signature block */
.signature-block {
    margin-top: 3em;
    page-break-inside: avoid;
}

.signature-line {
    border-top: 1px solid black;
    width: 200px;
    margin-top: 3em;
    padding-top: 5px;
    text-align: center;
    font-size: 10pt;
}

/* Legal references */
.legal-ref {
    font-style: italic;
    color: var(--muted-color);
    font-size: 10pt;
}

/* Footnotes for variable sources */
.footnotes {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 1px solid var(--border-color);
    font-size: 9pt;
}

.footnotes h2 {
    font-size: 11pt;
}

.footnote-ref {
    vertical-align: super;
    font-size: 8pt;
    color: var(--primary-color);
}

/* Print optimizations */
@media print {
    .no-print {
        display: none;
    }
    
    h2, h3 {
        page-break-after: avoid;
    }
    
    table, figure {
        page-break-inside: avoid;
    }
}
"""


def get_minimal_css() -> str:
    """Get minimal CSS for simple documents"""
    return """
body {
    font-family: system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 8px;
    border: 1px solid #ddd;
    text-align: left;
}

th { background: #f5f5f5; }

code {
    background: #f5f5f5;
    padding: 2px 4px;
}
"""


def get_style_preset(preset: StylePreset) -> str:
    """Get CSS for a style preset"""
    if preset == StylePreset.DEFAULT:
        return get_default_css()
    elif preset == StylePreset.BR_DOCUMENT:
        return get_br_document_css()
    elif preset == StylePreset.MINIMAL:
        return get_minimal_css()
    elif preset == StylePreset.PRINT:
        return get_br_document_css()  # Use B+R styles for print
    return get_default_css()
