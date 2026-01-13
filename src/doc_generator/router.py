"""
Document Generator API Router

Provides endpoints for listing templates, previewing data, and generating documents.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..api.database import get_db
from .engine import get_doc_engine, DocumentEngine
from .templates import DocumentCategory, TimeScope

logger = structlog.get_logger()
router = APIRouter(prefix="/doc-generator", tags=["Document Generator"])


class GenerateRequest(BaseModel):
    """Request to generate a document"""
    template_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    use_llm: bool = False
    llm_model: str = "llama3.2"


class DataPreviewRequest(BaseModel):
    """Request to preview data for a template"""
    template_id: str
    params: Dict[str, Any] = Field(default_factory=dict)


def get_engine() -> DocumentEngine:
    """Dependency to get document engine"""
    return get_doc_engine()


@router.get("/templates")
async def list_templates(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    time_scope: Optional[str] = Query(default=None, description="Filter by time scope"),
    engine: DocumentEngine = Depends(get_engine)
):
    """
    List all available document templates.
    
    Returns templates with their metadata including:
    - ID and name
    - Description
    - Category (project, financial, timesheet, legal, tax, report)
    - Time scope (none, monthly, quarterly, yearly, project, custom)
    - Required parameters
    """
    templates = await engine.list_templates()
    
    if category:
        templates = [t for t in templates if t.get("category") == category]
    if time_scope:
        templates = [t for t in templates if t.get("time_scope") == time_scope]
    
    return {
        "templates": templates,
        "total": len(templates),
        "categories": [c.value for c in DocumentCategory],
        "time_scopes": [s.value for s in TimeScope]
    }


@router.get("/templates/{template_id}")
async def get_template_detail(
    template_id: str,
    engine: DocumentEngine = Depends(get_engine)
):
    """
    Get detailed information about a specific template.
    
    Returns:
    - Full template metadata
    - Template content (markdown)
    - Demo content if available
    - LLM prompt if available
    - Data requirements with source descriptions
    """
    template = await engine.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    return template


@router.get("/data-sources")
async def list_data_sources(
    engine: DocumentEngine = Depends(get_engine)
):
    """
    List all available data sources.
    
    Data sources provide the underlying data for document generation:
    - SQL queries for database data
    - REST API calls for external services
    - Curl commands for web data
    """
    sources = await engine.list_data_sources()
    return {
        "sources": sources,
        "total": len(sources)
    }


@router.post("/preview-data")
async def preview_template_data(
    request: DataPreviewRequest,
    db: AsyncSession = Depends(get_db),
    engine: DocumentEngine = Depends(get_engine)
):
    """
    Preview the data that will be used for document generation.
    
    This endpoint fetches all data required by the template without
    generating the final document. Useful for:
    - Verifying data availability
    - Reviewing data before generation
    - Debugging data issues
    """
    result = await engine.fetch_template_data(
        template_id=request.template_id,
        params=request.params,
        db=db
    )
    
    if "error" in result and not result.get("data"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/generate")
async def generate_document(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    engine: DocumentEngine = Depends(get_engine)
):
    """
    Generate a document from a template.
    
    Parameters:
    - template_id: ID of the template to use
    - params: Parameters for data fetching (project_id, year, month, etc.)
    - use_llm: If true, use LLM to enhance the generated content
    - llm_model: LLM model to use (default: llama3.2)
    
    Returns:
    - Generated document content in markdown format
    - Metadata about generation
    """
    result = await engine.generate_document(
        template_id=request.template_id,
        params=request.params,
        db=db,
        use_llm=request.use_llm,
        llm_model=request.llm_model
    )
    
    if "error" in result and not result.get("content"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/demo/{template_id}")
async def get_demo_document(
    template_id: str,
    engine: DocumentEngine = Depends(get_engine)
):
    """
    Get a demo version of a document template.
    
    Returns pre-filled example content to show what the final
    document will look like.
    """
    result = await engine.get_demo_document(template_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/categories")
async def list_categories():
    """List all document categories with descriptions"""
    return {
        "categories": [
            {"id": "project", "name": "Projekty", "description": "Dokumenty projektowe B+R"},
            {"id": "financial", "name": "Finansowe", "description": "Ewidencje wydatków i kosztów"},
            {"id": "timesheet", "name": "Czas pracy", "description": "Rejestry czasu pracy"},
            {"id": "legal", "name": "Prawne", "description": "Umowy i dokumenty prawne"},
            {"id": "tax", "name": "Podatkowe", "description": "Dokumenty dla celów podatkowych"},
            {"id": "report", "name": "Raporty", "description": "Raporty i podsumowania"}
        ]
    }


@router.get("/filter-options")
async def get_filter_options(
    project_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available filter options for document generation.
    
    Returns available years and months based on existing data.
    """
    from sqlalchemy import text
    
    years_query = """
        SELECT DISTINCT EXTRACT(YEAR FROM invoice_date)::int as year
        FROM read_models.expenses
        WHERE (:project_id IS NULL OR project_id = :project_id)
        AND invoice_date IS NOT NULL
        ORDER BY year DESC
    """
    
    result = await db.execute(text(years_query), {"project_id": project_id})
    years = [row[0] for row in result.fetchall()]
    
    projects_query = """
        SELECT id, name, code
        FROM read_models.projects
        ORDER BY created_at DESC
        LIMIT 50
    """
    result = await db.execute(text(projects_query))
    projects = [{"id": str(row[0]), "name": row[1], "code": row[2]} for row in result.fetchall()]
    
    return {
        "years": years if years else [datetime.now().year],
        "months": list(range(1, 13)),
        "projects": projects
    }
