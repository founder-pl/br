"""
Document Templates - Base classes and types
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class DocumentCategory(str, Enum):
    PROJECT = "project"
    FINANCIAL = "financial"
    TIMESHEET = "timesheet"
    LEGAL = "legal"
    TAX = "tax"
    REPORT = "report"


class TimeScope(str, Enum):
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PROJECT = "project"
    CUSTOM = "custom"


@dataclass
class TemplateDataRequirement:
    """Defines a data source requirement for a template"""
    source_name: str
    required_params: List[str]
    optional_params: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class DocumentTemplate:
    """Document template definition"""
    id: str
    name: str
    description: str
    category: DocumentCategory
    time_scope: TimeScope
    data_requirements: List[TemplateDataRequirement]
    template_content: str
    demo_content: Optional[str] = None
    llm_prompt: Optional[str] = None
    output_format: str = "markdown"
    version: str = "1.0"
    
    def get_required_params(self) -> List[str]:
        """Get all required parameters across data sources"""
        params = set()
        for req in self.data_requirements:
            params.update(req.required_params)
        return list(params)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "time_scope": self.time_scope.value,
            "required_params": self.get_required_params(),
            "output_format": self.output_format,
            "version": self.version
        }
