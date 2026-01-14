"""
MD Render - Markdown to HTML and PDF rendering library.

Provides:
- md2html: Convert Markdown to HTML with styling
- html2pdf: Convert HTML to PDF using WeasyPrint
- md2pdf: Direct Markdown to PDF conversion
"""

from .converter import (
    md2html,
    html2pdf,
    md2pdf,
    MarkdownRenderer,
    PDFRenderer,
)
from .styles import (
    get_default_css,
    get_br_document_css,
    StylePreset,
)

__version__ = "0.1.0"

__all__ = [
    "md2html",
    "html2pdf",
    "md2pdf",
    "MarkdownRenderer",
    "PDFRenderer",
    "get_default_css",
    "get_br_document_css",
    "StylePreset",
]
