"""
Expenses Router Package - Split into logical modules for maintainability

Original expenses.py (1702 LOC) split into:
- models.py: Pydantic models and BR_CATEGORIES (~150 LOC)
- crud.py: Basic CRUD operations (~280 LOC)
- validation.py: Validation endpoints (~150 LOC)
- classification.py: Classification and categorization (~280 LOC)
- revenues.py: Revenue management (~220 LOC)
- documentation.py: Documentation generation (~300 LOC)

Total: ~1380 LOC (split across 6 files, avg ~230 LOC each)
"""

from fastapi import APIRouter

from .crud import router as crud_router
from .validation import router as validation_router
from .classification import router as classification_router
from .revenues import router as revenues_router
from .documentation import router as documentation_router

router = APIRouter(tags=["Expenses"])

# Include all sub-routers (order matters for path matching)
router.include_router(validation_router)  # /validate-*, /categorize first
router.include_router(revenues_router)    # /revenues/* before /{expense_id}
router.include_router(documentation_router)  # /project/* endpoints
router.include_router(classification_router)  # /{expense_id}/classify etc
router.include_router(crud_router)        # Base CRUD last (has /{expense_id})

__all__ = ["router"]
