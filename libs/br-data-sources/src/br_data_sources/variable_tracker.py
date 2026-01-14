"""
Variable tracking for document generation with source URLs.

Enables verification of all variables in generated documents.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TrackedVariable:
    """A variable tracked with its source URL for verification"""
    name: str
    value: Any
    source_name: str
    source_url: str
    path: str = ""
    description: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    
    def to_footnote_ref(self, index: int) -> str:
        """Generate markdown footnote reference"""
        return f"[^{index}]"
    
    def to_footnote_def(self, index: int) -> str:
        """Generate markdown footnote definition"""
        return f"[^{index}]: Źródło: [{self.name}]({self.source_url})"
    
    def to_inline_ref(self) -> str:
        """Generate inline markdown reference"""
        return f"[{self.value}]({self.source_url})"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "path": self.path,
            "fetched_at": self.fetched_at.isoformat(),
        }


class VariableTracker:
    """
    Track all variables used in document generation.
    
    Provides URLs for verification of each variable value.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:81",
        project_id: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.variables: List[TrackedVariable] = []
        self._index = 0
    
    def track(
        self,
        name: str,
        value: Any,
        source_name: str,
        path: str = "",
        description: Optional[str] = None,
    ) -> TrackedVariable:
        """
        Track a variable with its source.
        
        Args:
            name: Variable name
            value: Variable value
            source_name: Data source name
            path: Additional path for the variable
            description: Optional description
            
        Returns:
            TrackedVariable with source URL
        """
        self._index += 1
        
        # Build source URL
        if self.project_id:
            url = f"{self.base_url}/api/project/{self.project_id}/variable/{source_name}"
            if path:
                url = f"{url}/{path}"
        else:
            url = f"{self.base_url}/api/variable/{source_name}"
            if path:
                url = f"{url}/{path}"
        
        var = TrackedVariable(
            name=name,
            value=value,
            source_name=source_name,
            source_url=url,
            path=path,
            description=description,
        )
        
        self.variables.append(var)
        return var
    
    def track_invoice(
        self,
        invoice_id: str,
        variable_name: str,
        value: Any,
    ) -> TrackedVariable:
        """
        Track an invoice-specific variable.
        
        Args:
            invoice_id: Invoice ID
            variable_name: Variable name within invoice
            value: Variable value
            
        Returns:
            TrackedVariable
        """
        url = f"{self.base_url}/api/invoice/{invoice_id}/variable/{variable_name}"
        
        var = TrackedVariable(
            name=variable_name,
            value=value,
            source_name="invoice",
            source_url=url,
            path=f"{invoice_id}/{variable_name}",
        )
        
        self.variables.append(var)
        return var
    
    def get_footnotes_markdown(self) -> str:
        """
        Generate markdown footnotes section.
        
        Returns:
            Markdown string with all footnotes
        """
        if not self.variables:
            return ""
        
        lines = [
            "",
            "---",
            "",
            "## Przypisy źródłowe",
            "",
        ]
        
        for i, var in enumerate(self.variables, 1):
            lines.append(var.to_footnote_def(i))
        
        return "\n".join(lines)
    
    def get_footnote_refs(self) -> Dict[str, str]:
        """
        Get mapping of variable names to footnote references.
        
        Returns:
            Dict mapping variable name to footnote markdown
        """
        refs = {}
        for i, var in enumerate(self.variables, 1):
            refs[var.name] = var.to_footnote_ref(i)
        return refs
    
    def to_json(self) -> List[dict]:
        """Export all tracked variables as JSON"""
        return [var.to_dict() for var in self.variables]
    
    def clear(self):
        """Clear all tracked variables"""
        self.variables = []
        self._index = 0
