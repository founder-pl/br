"""
Expenses Router Package - Split into logical modules for maintainability

Original expenses.py (1702 LOC) split into:
- crud.py: Basic CRUD operations (create, read, update, delete)
- validation.py: Validation endpoints (pipeline, invoice, currency)
- classification.py: Classification and categorization
- revenues.py: Revenue management
- documentation.py: Documentation generation
"""

from fastapi import APIRouter

from .crud import router as crud_router
from .validation import router as validation_router
from .classification import router as classification_router
from .revenues import router as revenues_router
from .documentation import router as documentation_router

router = APIRouter(prefix="/expenses", tags=["Expenses"])

# Include all sub-routers
router.include_router(crud_router)
router.include_router(validation_router)
router.include_router(classification_router)
router.include_router(revenues_router)
router.include_router(documentation_router)

__all__ = ["router"]
