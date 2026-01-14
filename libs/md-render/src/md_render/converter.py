"""
Markdown and PDF conversion utilities.
"""
import io
from pathlib import Path
from typing import Optional, Union

import markdown
from markdown.extensions import codehilite, tables, toc, fenced_code
from jinja2 import Template
from weasyprint import HTML, CSS

from .styles import get_default_css, get_br_document_css


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
{{ css }}
    </style>
</head>
<body>
    <div class="document">
        {{ content }}
    </div>
    {% if footnotes %}
    <div class="footnotes">
        {{ footnotes }}
    </div>
    {% endif %}
</body>
</html>
"""


class MarkdownRenderer:
    """Configurable Markdown to HTML renderer"""
    
    def __init__(
        self,
        extensions: Optional[list] = None,
        extension_configs: Optional[dict] = None,
        css: Optional[str] = None,
    ):
        """
        Initialize Markdown renderer.
        
        Args:
            extensions: Markdown extensions to use
            extension_configs: Extension configurations
            css: Custom CSS styling
        """
        self.extensions = extensions or [
            "markdown.extensions.tables",
            "markdown.extensions.fenced_code",
            "markdown.extensions.codehilite",
            "markdown.extensions.toc",
            "markdown.extensions.footnotes",
            "markdown.extensions.attr_list",
            "markdown.extensions.def_list",
            "markdown.extensions.meta",
        ]
        self.extension_configs = extension_configs or {
            "codehilite": {
                "css_class": "highlight",
                "linenums": False,
            },
            "toc": {
                "title": "Spis treści",
                "toc_depth": 3,
            },
        }
        self.css = css or get_default_css()
        self._md = markdown.Markdown(
            extensions=self.extensions,
            extension_configs=self.extension_configs,
        )
    
    def render(
        self,
        md_content: str,
        title: str = "Dokument",
        include_toc: bool = False,
        footnotes: Optional[str] = None,
    ) -> str:
        """
        Render Markdown to HTML.
        
        Args:
            md_content: Markdown content
            title: Document title
            include_toc: Whether to include table of contents
            footnotes: Optional footnotes HTML
            
        Returns:
            Complete HTML document
        """
        # Reset MD instance for clean conversion
        self._md.reset()
        
        # Convert markdown to HTML
        html_content = self._md.convert(md_content)
        
        # Add TOC if requested
        if include_toc and hasattr(self._md, "toc"):
            html_content = f'<div class="toc">{self._md.toc}</div>\n{html_content}'
        
        # Render full HTML document
        template = Template(HTML_TEMPLATE)
        return template.render(
            title=title,
            css=self.css,
            content=html_content,
            footnotes=footnotes,
        )
    
    def render_fragment(self, md_content: str) -> str:
        """
        Render Markdown to HTML fragment (no wrapper).
        
        Args:
            md_content: Markdown content
            
        Returns:
            HTML fragment
        """
        self._md.reset()
        return self._md.convert(md_content)


class PDFRenderer:
    """HTML to PDF renderer using WeasyPrint"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        css: Optional[str] = None,
    ):
        """
        Initialize PDF renderer.
        
        Args:
            base_url: Base URL for resolving relative URLs
            css: Additional CSS for PDF
        """
        self.base_url = base_url
        self.css = css
    
    def render(
        self,
        html_content: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Render HTML to PDF.
        
        Args:
            html_content: HTML content to convert
            output_path: Optional path to save PDF
            
        Returns:
            PDF bytes
        """
        html = HTML(string=html_content, base_url=self.base_url)
        
        stylesheets = []
        if self.css:
            stylesheets.append(CSS(string=self.css))
        
        if output_path:
            html.write_pdf(output_path, stylesheets=stylesheets)
            with open(output_path, "rb") as f:
                return f.read()
        else:
            return html.write_pdf(stylesheets=stylesheets)
    
    def render_to_file(
        self,
        html_content: str,
        output_path: Union[str, Path],
    ) -> Path:
        """
        Render HTML to PDF file.
        
        Args:
            html_content: HTML content
            output_path: Output file path
            
        Returns:
            Path to created PDF
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html = HTML(string=html_content, base_url=self.base_url)
        
        stylesheets = []
        if self.css:
            stylesheets.append(CSS(string=self.css))
        
        html.write_pdf(output_path, stylesheets=stylesheets)
        return output_path


def md2html(
    md_content: str,
    title: str = "Dokument",
    css: Optional[str] = None,
    include_toc: bool = False,
) -> str:
    """
    Convert Markdown to HTML document.
    
    Args:
        md_content: Markdown content
        title: Document title
        css: Optional custom CSS
        include_toc: Include table of contents
        
    Returns:
        Complete HTML document
    """
    renderer = MarkdownRenderer(css=css)
    return renderer.render(md_content, title=title, include_toc=include_toc)


def html2pdf(
    html_content: str,
    output_path: Optional[Union[str, Path]] = None,
    css: Optional[str] = None,
) -> bytes:
    """
    Convert HTML to PDF.
    
    Args:
        html_content: HTML content
        output_path: Optional output file path
        css: Optional additional CSS
        
    Returns:
        PDF bytes
    """
    renderer = PDFRenderer(css=css)
    return renderer.render(html_content, output_path=output_path)


def md2pdf(
    md_content: str,
    output_path: Optional[Union[str, Path]] = None,
    title: str = "Dokument",
    css: Optional[str] = None,
    include_toc: bool = False,
) -> bytes:
    """
    Convert Markdown directly to PDF.
    
    Args:
        md_content: Markdown content
        output_path: Optional output file path
        title: Document title
        css: Optional custom CSS
        include_toc: Include table of contents
        
    Returns:
        PDF bytes
    """
    html = md2html(md_content, title=title, css=css, include_toc=include_toc)
    return html2pdf(html, output_path=output_path)
