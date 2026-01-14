# MD Render

Markdown to HTML and PDF rendering library for B+R documentation.

## Installation

```bash
pip install -e libs/md-render
```

## Features

- **md2html**: Convert Markdown to styled HTML
- **html2pdf**: Convert HTML to PDF using WeasyPrint
- **md2pdf**: Direct Markdown to PDF conversion
- **Style presets**: Default, B+R Document, Minimal, Print

## Usage

### Basic Conversion

```python
from md_render import md2html, html2pdf, md2pdf

# Markdown to HTML
markdown_content = """
# Raport B+R

## Podsumowanie

| Kategoria | Kwota |
|-----------|-------|
| Wynagrodzenia | 50 000 zł |
| Materiały | 10 000 zł |
"""

html = md2html(markdown_content, title="Raport B+R 2025")

# HTML to PDF
pdf_bytes = html2pdf(html, output_path="report.pdf")

# Direct Markdown to PDF
pdf_bytes = md2pdf(markdown_content, output_path="report.pdf")
```

### Custom Styling

```python
from md_render import MarkdownRenderer, get_br_document_css

renderer = MarkdownRenderer(css=get_br_document_css())
html = renderer.render(
    markdown_content,
    title="Karta Projektowa B+R",
    include_toc=True
)
```

### Style Presets

```python
from md_render import StylePreset
from md_render.styles import get_style_preset

css = get_style_preset(StylePreset.BR_DOCUMENT)
```

## API Reference

### Functions

- `md2html(content, title, css, include_toc)` - Convert MD to HTML
- `html2pdf(html, output_path, css)` - Convert HTML to PDF
- `md2pdf(content, output_path, title, css)` - Convert MD to PDF

### Classes

- `MarkdownRenderer` - Configurable MD→HTML renderer
- `PDFRenderer` - HTML→PDF renderer with WeasyPrint

## License

MIT © Softreck
