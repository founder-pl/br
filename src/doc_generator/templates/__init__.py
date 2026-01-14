"""
Document Templates Package - Split into logical modules

Original templates.py (1001 LOC) split into:
- base.py: Base classes (DocumentCategory, TimeScope, TemplateDataRequirement, DocumentTemplate)
- project.py: Project templates (project_card)
- financial.py: Financial templates (expense_registry, timesheet_monthly)
- tax.py: Tax templates (nexus_calculation, br_annual_summary)
- legal.py: Legal templates (br_contract, ip_box_procedure, tax_interpretation_request)
- registry.py: TemplateRegistry class
"""

from .base import DocumentCategory, TimeScope, TemplateDataRequirement, DocumentTemplate
from .registry import TemplateRegistry, get_template_registry

__all__ = [
    "DocumentCategory",
    "TimeScope", 
    "TemplateDataRequirement",
    "DocumentTemplate",
    "TemplateRegistry",
    "get_template_registry"
]
