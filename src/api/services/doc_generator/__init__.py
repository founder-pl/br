"""
B+R Documentation Generator Package

Original doc_generator.py (996 LOC) split into:
- version_control.py: DocumentVersionControl class (~90 LOC)
- prompts.py: LLM prompts and constants (~70 LOC)
- llm.py: LLM generation and refinement (~130 LOC)
- templates.py: Template generation functions (~400 LOC)
- generator.py: ExpenseDocumentGenerator main class (~200 LOC)

Total: ~890 LOC (avg ~178 LOC/module)
"""

from .generator import ExpenseDocumentGenerator, get_doc_generator
from .version_control import DocumentVersionControl
from .prompts import (
    BR_EXPENSE_DOC_PROMPT,
    LLM_REFINEMENT_PROMPT,
    CATEGORY_NAMES,
    CATEGORY_NAMES_WITH_RATES,
    MONTH_NAMES_PL,
)
from .llm import generate_with_llm, refine_with_llm
from .templates import (
    build_expense_prompt,
    generate_expense_template,
    generate_summary_template,
    build_expense_details,
    format_doc_link,
)

__all__ = [
    # Main class and factory
    "ExpenseDocumentGenerator",
    "get_doc_generator",
    # Version control
    "DocumentVersionControl",
    # Prompts
    "BR_EXPENSE_DOC_PROMPT",
    "LLM_REFINEMENT_PROMPT",
    "CATEGORY_NAMES",
    "CATEGORY_NAMES_WITH_RATES",
    "MONTH_NAMES_PL",
    # LLM functions
    "generate_with_llm",
    "refine_with_llm",
    # Template functions
    "build_expense_prompt",
    "generate_expense_template",
    "generate_summary_template",
    "build_expense_details",
    "format_doc_link",
]
