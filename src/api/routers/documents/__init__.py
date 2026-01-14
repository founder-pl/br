"""
Documents Router Package - Split into logical modules for maintainability

Original documents.py (1087 LOC) split into:
- models.py: Pydantic models (~50 LOC)
- upload.py: Upload and OCR processing (~300 LOC)
- crud.py: Basic CRUD operations (~200 LOC)
- notes.py: Document notes management (~100 LOC)
- extraction.py: LLM extraction and data sync (~350 LOC)
"""

from fastapi import APIRouter

from .upload import router as upload_router
from .crud import router as crud_router
from .notes import router as notes_router
from .extraction import router as extraction_router

router = APIRouter(tags=["Documents"])

# Include all sub-routers (order matters for path matching)
router.include_router(upload_router)      # /upload, /sync-expenses
router.include_router(notes_router)       # /notes
router.include_router(extraction_router)  # /{id}/llm-extract, /{id}/re-extract
router.include_router(crud_router)        # Base CRUD (/{id})

__all__ = ["router"]
