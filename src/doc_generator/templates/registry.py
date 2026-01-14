"""
Document Templates - Registry class
"""
from typing import Any, Dict, List, Optional

from .base import DocumentTemplate

# Import all template definitions
from .project import get_project_templates
from .financial import get_financial_templates
from .tax import get_tax_templates
from .legal import get_legal_templates


class TemplateRegistry:
    """Registry for document templates"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._templates = {}
            cls._instance._initialize_templates()
        return cls._instance
    
    def _initialize_templates(self):
        """Initialize all B+R and IP Box document templates"""
        # Register project templates
        for template in get_project_templates():
            self.register(template)
        
        # Register financial templates
        for template in get_financial_templates():
            self.register(template)
        
        # Register tax templates
        for template in get_tax_templates():
            self.register(template)
        
        # Register legal templates
        for template in get_legal_templates():
            self.register(template)
    
    def register(self, template: DocumentTemplate):
        """Register a template"""
        self._templates[template.id] = template
    
    def get(self, template_id: str) -> Optional[DocumentTemplate]:
        """Get template by ID"""
        return self._templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        return [t.to_dict() for t in self._templates.values()]
    
    def get_by_category(self, category: str) -> List[DocumentTemplate]:
        """Get templates by category"""
        return [t for t in self._templates.values() if t.category.value == category]


_registry_instance = None


def get_template_registry() -> TemplateRegistry:
    """Get or create template registry singleton"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TemplateRegistry()
    return _registry_instance
