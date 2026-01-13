"""
PDF Renderer for BR Documentation Generator.

Converts markdown documentation to professional PDF using WeasyPrint.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

log = structlog.get_logger()


# Professional CSS template for B+R documentation
PROFESSIONAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

@page {
    size: A4;
    margin: 2.5cm 2cm;
    
    @top-center {
        content: string(header-text);
        font-size: 9pt;
        color: #666;
    }
    
    @bottom-center {
        content: "Strona " counter(page) " z " counter(pages);
        font-size: 9pt;
        color: #666;
    }
    
    @bottom-left {
        content: string(footer-text);
        font-size: 8pt;
        color: #888;
    }
}

@page :first {
    @top-center { content: none; }
    @bottom-center { content: none; }
    @bottom-left { content: none; }
}

body {
    font-family: 'Open Sans', 'DejaVu Sans', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
}

h1 {
    font-size: 24pt;
    font-weight: 700;
    color: #1a365d;
    margin-top: 0;
    margin-bottom: 1em;
    padding-bottom: 0.5em;
    border-bottom: 3px solid #2c5282;
    page-break-after: avoid;
}

h2 {
    font-size: 16pt;
    font-weight: 600;
    color: #2c5282;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h3 {
    font-size: 13pt;
    font-weight: 600;
    color: #4a5568;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
}

h4 {
    font-size: 11pt;
    font-weight: 600;
    color: #4a5568;
    margin-top: 1em;
    margin-bottom: 0.3em;
}

p {
    margin-bottom: 0.8em;
    text-align: justify;
    orphans: 3;
    widows: 3;
}

ul, ol {
    margin-left: 1.5em;
    margin-bottom: 1em;
}

li {
    margin-bottom: 0.3em;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th {
    background-color: #2c5282;
    color: white;
    font-weight: 600;
    text-align: left;
    padding: 0.6em 0.8em;
    border: 1px solid #2c5282;
}

td {
    padding: 0.5em 0.8em;
    border: 1px solid #e2e8f0;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

code {
    font-family: 'Consolas', 'DejaVu Sans Mono', monospace;
    font-size: 9pt;
    background-color: #f7fafc;
    padding: 0.15em 0.3em;
    border-radius: 3px;
}

pre {
    background-color: #2d3748;
    color: #e2e8f0;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.4;
    page-break-inside: avoid;
}

pre code {
    background-color: transparent;
    padding: 0;
    color: inherit;
}

blockquote {
    border-left: 4px solid #2c5282;
    margin: 1em 0;
    padding: 0.5em 1em;
    background-color: #f7fafc;
    font-style: italic;
}

.cover-page {
    page-break-after: always;
    text-align: center;
    padding-top: 5cm;
}

.cover-page h1 {
    font-size: 28pt;
    border: none;
    margin-bottom: 0.3em;
}

.cover-page .subtitle {
    font-size: 14pt;
    color: #4a5568;
    margin-bottom: 2em;
}

.cover-page .company {
    font-size: 16pt;
    font-weight: 600;
    color: #2c5282;
    margin-top: 3cm;
}

.cover-page .date {
    font-size: 12pt;
    color: #666;
    margin-top: 1em;
}

.cover-page .logo {
    max-width: 200px;
    max-height: 100px;
    margin-bottom: 2cm;
}

.toc {
    page-break-after: always;
}

.toc h2 {
    border-bottom: 2px solid #2c5282;
    padding-bottom: 0.3em;
}

.toc ul {
    list-style: none;
    margin-left: 0;
}

.toc li {
    padding: 0.3em 0;
    border-bottom: 1px dotted #e2e8f0;
}

.toc a {
    color: #2c5282;
    text-decoration: none;
}

.summary-box {
    background-color: #ebf8ff;
    border: 1px solid #90cdf4;
    border-radius: 5px;
    padding: 1em;
    margin: 1em 0;
}

.warning-box {
    background-color: #fefcbf;
    border: 1px solid #f6e05e;
    border-radius: 5px;
    padding: 1em;
    margin: 1em 0;
}

.cost-table {
    background-color: #f0fff4;
}

.cost-table th {
    background-color: #276749;
}

.total-row {
    font-weight: 700;
    background-color: #c6f6d5 !important;
}

.header-text {
    string-set: header-text content();
}

.footer-text {
    string-set: footer-text content();
}

/* Print optimizations */
h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
}

table, figure, pre {
    page-break-inside: avoid;
}

img {
    max-width: 100%;
    height: auto;
}
"""

MINIMAL_CSS = """
body {
    font-family: Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    margin: 2cm;
}

h1 { font-size: 20pt; color: #333; }
h2 { font-size: 16pt; color: #444; }
h3 { font-size: 13pt; color: #555; }

table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 0.5em; }
th { background: #f0f0f0; }

code { font-family: monospace; background: #f5f5f5; padding: 0.1em 0.3em; }
pre { background: #f5f5f5; padding: 1em; overflow-x: auto; }
"""


class PDFRenderer:
    """
    Renders markdown documentation to professional PDF.
    
    Features:
    - Multiple templates (professional, minimal, detailed)
    - Company logo embedding
    - Header/footer customization
    - Table of contents generation
    - Cost table highlighting
    """
    
    TEMPLATES = {
        "professional": PROFESSIONAL_CSS,
        "minimal": MINIMAL_CSS,
        "detailed": PROFESSIONAL_CSS,  # Same as professional with more sections
    }
    
    def __init__(
        self,
        template: str = "professional",
        company_logo: Optional[str] = None,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        custom_css: Optional[str] = None
    ):
        """
        Initialize PDF renderer.
        
        Args:
            template: Template name (professional, minimal, detailed)
            company_logo: Path to company logo image
            header: Header text for pages
            footer: Footer text for pages
            custom_css: Additional CSS to apply
        """
        self.template = template
        self.company_logo = company_logo
        self.header = header
        self.footer = footer
        self.custom_css = custom_css
        self.font_config = FontConfiguration()
        
        log.info(
            "pdf_renderer_initialized",
            template=template,
            has_logo=bool(company_logo)
        )
    
    def _get_css(self) -> str:
        """Get combined CSS for rendering."""
        base_css = self.TEMPLATES.get(self.template, PROFESSIONAL_CSS)
        
        if self.custom_css:
            base_css += f"\n\n/* Custom CSS */\n{self.custom_css}"
        
        return base_css
    
    def _create_cover_page(
        self,
        title: str,
        subtitle: Optional[str] = None,
        company_name: Optional[str] = None,
        fiscal_year: Optional[int] = None
    ) -> str:
        """Generate HTML for cover page."""
        logo_html = ""
        if self.company_logo and Path(self.company_logo).exists():
            logo_html = f'<img src="file://{self.company_logo}" class="logo" alt="Logo">'
        
        date_str = datetime.now().strftime("%d %B %Y")
        
        return f"""
        <div class="cover-page">
            {logo_html}
            <h1>{title}</h1>
            {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
            {f'<div class="company">{company_name}</div>' if company_name else ''}
            {f'<div class="date">Rok podatkowy: {fiscal_year}</div>' if fiscal_year else ''}
            <div class="date">{date_str}</div>
        </div>
        """
    
    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML with extensions."""
        extensions = [
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'nl2br',
            'sane_lists',
        ]
        
        extension_configs = {
            'codehilite': {
                'css_class': 'highlight',
                'guess_lang': False,
            },
            'toc': {
                'title': 'Spis Treści',
                'toc_depth': 3,
            }
        }
        
        html = markdown.markdown(
            markdown_content,
            extensions=extensions,
            extension_configs=extension_configs
        )
        
        return html
    
    def _enhance_html(
        self,
        html: str,
        title: Optional[str] = None,
        company_name: Optional[str] = None,
        fiscal_year: Optional[int] = None
    ) -> str:
        """Enhance HTML with cover page, headers, and formatting."""
        # Add header/footer markers
        header_marker = ""
        footer_marker = ""
        
        if self.header:
            header_marker = f'<div class="header-text">{self.header}</div>'
        
        if self.footer:
            footer_text = self.footer.replace("{company_name}", company_name or "")
            footer_marker = f'<div class="footer-text">{footer_text}</div>'
        
        # Create cover page
        cover_page = ""
        if title:
            cover_page = self._create_cover_page(
                title=title,
                subtitle="Dokumentacja Projektu Badawczo-Rozwojowego",
                company_name=company_name,
                fiscal_year=fiscal_year
            )
        
        # Enhance cost tables
        html = html.replace('<table>', '<table class="cost-table">')
        
        # Full HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html lang="pl">
        <head>
            <meta charset="UTF-8">
            <title>{title or 'Dokumentacja B+R'}</title>
        </head>
        <body>
            {header_marker}
            {footer_marker}
            {cover_page}
            {html}
        </body>
        </html>
        """
        
        return full_html
    
    def render(
        self,
        markdown_content: str,
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render markdown content to PDF.
        
        Args:
            markdown_content: Markdown documentation content
            output_path: Path for output PDF file
            metadata: Document metadata (title, author, keywords, etc.)
        
        Returns:
            Path to generated PDF file
        """
        metadata = metadata or {}
        
        log.info(
            "rendering_pdf",
            output_path=output_path,
            content_length=len(markdown_content)
        )
        
        try:
            # Convert markdown to HTML
            html_content = self._convert_markdown_to_html(markdown_content)
            
            # Enhance with cover page and formatting
            full_html = self._enhance_html(
                html_content,
                title=metadata.get("title"),
                company_name=metadata.get("company_name"),
                fiscal_year=metadata.get("fiscal_year")
            )
            
            # Get CSS
            css_content = self._get_css()
            
            # Create WeasyPrint HTML object
            html_doc = HTML(string=full_html)
            css_doc = CSS(string=css_content, font_config=self.font_config)
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Render to PDF
            html_doc.write_pdf(
                output_path,
                stylesheets=[css_doc],
                font_config=self.font_config
            )
            
            log.info(
                "pdf_rendered_successfully",
                output_path=output_path,
                file_size=output_file.stat().st_size
            )
            
            return str(output_file.absolute())
            
        except Exception as e:
            log.error(
                "pdf_render_failed",
                error=str(e),
                output_path=output_path
            )
            raise
    
    async def render_async(
        self,
        markdown_content: str,
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Async wrapper for render method."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.render(markdown_content, output_path, metadata)
        )
    
    def render_from_file(
        self,
        markdown_path: str,
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render markdown file to PDF.
        
        Args:
            markdown_path: Path to markdown file
            output_path: Path for output PDF
            metadata: Document metadata
        
        Returns:
            Path to generated PDF
        """
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        return self.render(markdown_content, output_path, metadata)


def render_documentation_to_pdf(
    markdown_content: str,
    output_path: str,
    company_name: Optional[str] = None,
    company_logo: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    template: str = "professional"
) -> str:
    """
    Convenience function to render B+R documentation to PDF.
    
    Args:
        markdown_content: Markdown documentation
        output_path: Output PDF path
        company_name: Company name for cover page
        company_logo: Path to company logo
        fiscal_year: Fiscal year for documentation
        template: Template name
    
    Returns:
        Path to generated PDF
    """
    renderer = PDFRenderer(
        template=template,
        company_logo=company_logo,
        header="Dokumentacja B+R",
        footer=f"Poufne - {company_name}" if company_name else "Poufne"
    )
    
    return renderer.render(
        markdown_content,
        output_path,
        metadata={
            "title": "Dokumentacja Projektu B+R",
            "company_name": company_name,
            "fiscal_year": fiscal_year
        }
    )
