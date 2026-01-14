"""
Footnote Generator for B+R Documents.

Adds source URL footnotes to generated documents for variable verification.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


@dataclass
class VariableFootnote:
    """A variable with its source URL for footnote generation"""
    name: str
    value: Any
    source_name: str
    path: str = ""
    base_url: str = "http://localhost:81"
    project_id: Optional[str] = None
    invoice_id: Optional[str] = None
    
    @property
    def source_url(self) -> str:
        """Generate the verification URL for this variable"""
        if self.invoice_id:
            return f"{self.base_url}/api/invoice/{self.invoice_id}/variable/{self.path or self.name}"
        elif self.project_id:
            url = f"{self.base_url}/api/project/{self.project_id}/variable/{self.source_name}"
            if self.path:
                url += f"/{self.path}"
            return url
        else:
            return f"{self.base_url}/api/variable/{self.source_name}/{self.path or self.name}"
    
    def to_footnote_ref(self, index: int) -> str:
        """Generate markdown footnote reference [^n]"""
        return f"[^{index}]"
    
    def to_footnote_def(self, index: int) -> str:
        """Generate markdown footnote definition"""
        return f"[^{index}]: Źródło: [{self.name}]({self.source_url})"


class FootnoteTracker:
    """
    Tracks all variables used in document generation and generates footnotes.
    
    Usage:
        tracker = FootnoteTracker(project_id="uuid", base_url="http://localhost:81")
        
        # Track variables
        ref = tracker.track("total_costs", 50000, "expenses_summary", "total_gross")
        
        # Use in document
        document = f"Koszty: **50 000 zł**{ref}"
        
        # Add footnotes section
        document += tracker.get_footnotes_section()
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        base_url: str = "http://localhost:81",
    ):
        self.project_id = project_id
        self.base_url = base_url.rstrip("/")
        self._footnotes: List[VariableFootnote] = []
        self._index = 0
    
    def track(
        self,
        name: str,
        value: Any,
        source_name: str,
        path: str = "",
        invoice_id: Optional[str] = None,
    ) -> str:
        """
        Track a variable and return its footnote reference.
        
        Args:
            name: Human-readable name for the variable
            value: The variable value
            source_name: Data source name (e.g., "expenses_summary")
            path: Field path within the source
            invoice_id: Optional invoice ID for invoice-specific variables
            
        Returns:
            Markdown footnote reference like "[^1]"
        """
        self._index += 1
        
        footnote = VariableFootnote(
            name=name,
            value=value,
            source_name=source_name,
            path=path,
            base_url=self.base_url,
            project_id=self.project_id,
            invoice_id=invoice_id,
        )
        
        self._footnotes.append(footnote)
        return footnote.to_footnote_ref(self._index)
    
    def track_nexus(self, component: str, value: float) -> str:
        """Track a Nexus calculation component"""
        return self.track(
            name=f"nexus_{component}",
            value=value,
            source_name="nexus_calculation",
            path=component,
        )
    
    def track_expense(self, field: str, value: Any, invoice_id: str) -> str:
        """Track an expense/invoice field"""
        return self.track(
            name=field,
            value=value,
            source_name="invoice",
            path=field,
            invoice_id=invoice_id,
        )
    
    def get_footnotes_section(self) -> str:
        """
        Generate the footnotes section for the document.
        
        Returns:
            Markdown string with all footnote definitions
        """
        if not self._footnotes:
            return ""
        
        lines = [
            "",
            "---",
            "",
            "## Przypisy źródłowe",
            "",
            "Każda zmienna w tym dokumencie jest weryfikowalna poprzez poniższe linki API:",
            "",
        ]
        
        for i, footnote in enumerate(self._footnotes, 1):
            lines.append(footnote.to_footnote_def(i))
        
        return "\n".join(lines)
    
    def get_verification_table(self) -> str:
        """
        Generate a verification table with all tracked variables.
        
        Returns:
            Markdown table with variable names, values, and URLs
        """
        if not self._footnotes:
            return ""
        
        lines = [
            "",
            "## Tabela weryfikacji zmiennych",
            "",
            "| Zmienna | Wartość | URL weryfikacji |",
            "|---------|---------|-----------------|",
        ]
        
        for footnote in self._footnotes:
            value_str = str(footnote.value)
            if len(value_str) > 30:
                value_str = value_str[:27] + "..."
            lines.append(f"| {footnote.name} | {value_str} | [{footnote.source_name}]({footnote.source_url}) |")
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear all tracked footnotes"""
        self._footnotes = []
        self._index = 0
    
    @property
    def count(self) -> int:
        """Number of tracked variables"""
        return len(self._footnotes)


def add_footnotes_to_document(
    content: str,
    variables: Dict[str, Dict[str, Any]],
    project_id: str,
    base_url: str = "http://localhost:81",
) -> str:
    """
    Add footnotes to an existing document for all recognized variables.
    
    Args:
        content: Original document content
        variables: Dict mapping variable patterns to their metadata
                   e.g., {"total_gross": {"value": 50000, "source": "expenses_summary"}}
        project_id: Project ID for URL generation
        base_url: Base URL for API
        
    Returns:
        Document with footnotes added
    """
    tracker = FootnoteTracker(project_id=project_id, base_url=base_url)
    
    for var_name, var_info in variables.items():
        source = var_info.get("source", "unknown")
        value = var_info.get("value")
        path = var_info.get("path", var_name)
        
        # Find and annotate the variable in content
        ref = tracker.track(var_name, value, source, path)
        
        # Try to find and annotate the value in the document
        if value is not None:
            # Try different formats for the value
            patterns = [
                # Currency format
                rf'(\*\*{re.escape(str(value))}[^*]*\*\*)',
                # Plain number
                rf'\b({re.escape(str(value))})\b',
            ]
            
            for pattern in patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, rf'\1{ref}', content, count=1)
                    break
    
    # Add footnotes section
    content += tracker.get_footnotes_section()
    
    return content


def generate_document_with_tracking(
    template: str,
    context: Dict[str, Any],
    project_id: str,
    base_url: str = "http://localhost:81",
    tracked_variables: Optional[List[str]] = None,
) -> tuple[str, FootnoteTracker]:
    """
    Generate a document from template while tracking specified variables.
    
    Args:
        template: Jinja2-style template string
        context: Template context with data
        project_id: Project ID for URL generation
        base_url: Base URL for API
        tracked_variables: List of variable paths to track (e.g., ["total_gross", "nexus.nexus"])
        
    Returns:
        Tuple of (rendered document, FootnoteTracker with all tracked variables)
    """
    from jinja2 import Template
    
    tracker = FootnoteTracker(project_id=project_id, base_url=base_url)
    
    # Track specified variables
    if tracked_variables:
        for var_path in tracked_variables:
            # Navigate context to get value
            parts = var_path.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            
            if value is not None:
                # Determine source from path
                source = parts[0] if len(parts) > 1 else "context"
                path = parts[-1]
                tracker.track(var_path, value, source, path)
    
    # Render template
    jinja_template = Template(template)
    content = jinja_template.render(**context)
    
    return content, tracker
