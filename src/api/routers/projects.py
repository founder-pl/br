"""
Projects Router - B+R project management
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db
from ..config import settings

logger = structlog.get_logger()
router = APIRouter()


class ProjectCreate(BaseModel):
    """Create project request"""
    name: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    fiscal_year: int = Field(default=2025, ge=2020, le=2030)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectUpdate(BaseModel):
    """Update project request"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectResponse(BaseModel):
    """Project response"""
    id: str
    name: str
    description: Optional[str]
    status: str
    start_date: Optional[date]
    end_date: Optional[date]
    fiscal_year: int
    total_expenses: float
    br_qualified_expenses: float
    ip_qualified_expenses: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Project summary with B+R statistics"""
    id: str
    name: str
    fiscal_year: int
    
    # Expense totals
    total_expenses: float
    br_qualified_expenses: float
    br_deduction_amount: float
    ip_qualified_expenses: float
    
    # Document counts
    documents_count: int
    pending_documents: int
    needs_clarification: int
    
    # Category breakdown
    expenses_by_category: dict


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new B+R project"""
    project_id = str(uuid.uuid4())
    
    await db.execute(
        text("""
        INSERT INTO read_models.projects 
        (id, name, description, fiscal_year, start_date, end_date, status)
        VALUES (:id, :name, :description, :fiscal_year, :start_date, :end_date, 'active')
        """),
        {
            "id": project_id,
            "name": project.name,
            "description": project.description,
            "fiscal_year": project.fiscal_year,
            "start_date": project.start_date,
            "end_date": project.end_date
        }
    )
    
    logger.info("Project created", project_id=project_id, name=project.name)
    return await get_project(project_id, db)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get project details"""
    result = await db.execute(
        text("""
        SELECT id, name, description, status, start_date, end_date,
               fiscal_year, total_expenses, br_qualified_expenses,
               ip_qualified_expenses, created_at, updated_at
        FROM read_models.projects WHERE id = :id
        """),
        {"id": project_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=str(row[0]),
        name=row[1],
        description=row[2],
        status=row[3],
        start_date=row[4],
        end_date=row[5],
        fiscal_year=row[6],
        total_expenses=float(row[7] or 0),
        br_qualified_expenses=float(row[8] or 0),
        ip_qualified_expenses=float(row[9] or 0),
        created_at=row[10],
        updated_at=row[11]
    )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    fiscal_year: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """List all projects"""
    query = """
        SELECT id, name, description, status, start_date, end_date,
               fiscal_year, total_expenses, br_qualified_expenses,
               ip_qualified_expenses, created_at, updated_at
        FROM read_models.projects WHERE 1=1
    """
    params = {}
    
    if fiscal_year:
        query += " AND fiscal_year = :fiscal_year"
        params["fiscal_year"] = fiscal_year
    
    if status:
        query += " AND status = :status"
        params["status"] = status
    
    query += " ORDER BY created_at DESC"
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [
        ProjectResponse(
            id=str(row[0]),
            name=row[1],
            description=row[2],
            status=row[3],
            start_date=row[4],
            end_date=row[5],
            fiscal_year=row[6],
            total_expenses=float(row[7] or 0),
            br_qualified_expenses=float(row[8] or 0),
            ip_qualified_expenses=float(row[9] or 0),
            created_at=row[10],
            updated_at=row[11]
        )
        for row in rows
    ]


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project details"""
    updates = []
    params = {"id": project_id}
    
    if project.name:
        updates.append("name = :name")
        params["name"] = project.name
    
    if project.description is not None:
        updates.append("description = :description")
        params["description"] = project.description
    
    if project.status:
        updates.append("status = :status")
        params["status"] = project.status
    
    if project.start_date:
        updates.append("start_date = :start_date")
        params["start_date"] = project.start_date
    
    if project.end_date:
        updates.append("end_date = :end_date")
        params["end_date"] = project.end_date
    
    if updates:
        updates.append("updated_at = NOW()")
        await db.execute(
            text(f"UPDATE read_models.projects SET {', '.join(updates)} WHERE id = :id"),
            params
        )
    
    return await get_project(project_id, db)


@router.get("/{project_id}/summary", response_model=ProjectSummary)
async def get_project_summary(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed project summary with B+R statistics"""
    # Get project
    project = await get_project(project_id, db)
    
    # Get expense statistics
    expense_result = await db.execute(
        text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END) as br_total,
            SUM(CASE WHEN br_qualified THEN gross_amount * br_deduction_rate ELSE 0 END) as br_deduction,
            SUM(CASE WHEN ip_qualified THEN gross_amount ELSE 0 END) as ip_total
        FROM read_models.expenses WHERE project_id = :project_id
        """),
        {"project_id": project_id}
    )
    expense_row = expense_result.fetchone()
    
    # Get document counts
    doc_result = await db.execute(
        text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN ocr_status = 'pending' THEN 1 ELSE 0 END) as pending
        FROM read_models.documents WHERE project_id = :project_id
        """),
        {"project_id": project_id}
    )
    doc_row = doc_result.fetchone()
    
    # Get clarification count
    clarification_result = await db.execute(
        text("""
        SELECT COUNT(*) FROM read_models.expenses 
        WHERE project_id = :project_id AND needs_clarification = true
        """),
        {"project_id": project_id}
    )
    clarification_count = clarification_result.scalar() or 0
    
    # Get expenses by category
    category_result = await db.execute(
        text("""
        SELECT br_category, SUM(gross_amount) as total
        FROM read_models.expenses 
        WHERE project_id = :project_id AND br_qualified = true
        GROUP BY br_category
        """),
        {"project_id": project_id}
    )
    category_rows = category_result.fetchall()
    expenses_by_category = {row[0]: float(row[1]) for row in category_rows if row[0]}
    
    return ProjectSummary(
        id=project.id,
        name=project.name,
        fiscal_year=project.fiscal_year,
        total_expenses=float(expense_row[0] or 0) if expense_row else 0,
        br_qualified_expenses=float(expense_row[1] or 0) if expense_row else 0,
        br_deduction_amount=float(expense_row[2] or 0) if expense_row else 0,
        ip_qualified_expenses=float(expense_row[3] or 0) if expense_row else 0,
        documents_count=int(doc_row[0] or 0) if doc_row else 0,
        pending_documents=int(doc_row[1] or 0) if doc_row else 0,
        needs_clarification=int(clarification_count),
        expenses_by_category=expenses_by_category
    )


@router.post("/{project_id}/recalculate")
async def recalculate_project_totals(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Recalculate project expense totals"""
    # Calculate totals from expenses
    result = await db.execute(
        text("""
        SELECT 
            SUM(gross_amount) as total,
            SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END) as br_total,
            SUM(CASE WHEN ip_qualified THEN gross_amount ELSE 0 END) as ip_total
        FROM read_models.expenses WHERE project_id = :project_id
        """),
        {"project_id": project_id}
    )
    row = result.fetchone()
    
    # Update project
    await db.execute(
        text("""
        UPDATE read_models.projects SET
            total_expenses = :total,
            br_qualified_expenses = :br_total,
            ip_qualified_expenses = :ip_total,
            updated_at = NOW()
        WHERE id = :id
        """),
        {
            "id": project_id,
            "total": float(row[0] or 0),
            "br_total": float(row[1] or 0),
            "ip_total": float(row[2] or 0)
        }
    )
    
    return {"status": "recalculated", "project_id": project_id}


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project (only if no expenses attached)"""
    # Check if project exists
    result = await db.execute(
        text("SELECT id FROM read_models.projects WHERE id = :id"),
        {"id": project_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check for expenses
    expense_result = await db.execute(
        text("SELECT COUNT(*) FROM read_models.expenses WHERE project_id = :id"),
        {"id": project_id}
    )
    expense_count = expense_result.scalar() or 0
    
    if expense_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete project with {expense_count} expenses. Reassign expenses first."
        )
    
    await db.execute(
        text("DELETE FROM read_models.projects WHERE id = :id"),
        {"id": project_id}
    )
    
    logger.info("Project deleted", project_id=project_id)
    return {"status": "deleted", "project_id": project_id}


class BulkAssignRequest(BaseModel):
    """Bulk assign expenses to project"""
    expense_ids: List[str]
    project_id: str


@router.post("/bulk-assign-expenses")
async def bulk_assign_expenses(
    request: BulkAssignRequest,
    db: AsyncSession = Depends(get_db)
):
    """Assign multiple expenses to a project"""
    # Verify project exists
    result = await db.execute(
        text("SELECT id FROM read_models.projects WHERE id = :id"),
        {"id": request.project_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update expenses
    updated = 0
    for expense_id in request.expense_ids:
        result = await db.execute(
            text("UPDATE read_models.expenses SET project_id = :project_id, updated_at = NOW() WHERE id = :id"),
            {"id": expense_id, "project_id": request.project_id}
        )
        updated += 1
    
    logger.info("Bulk assigned expenses", project_id=request.project_id, count=updated)
    return {"status": "assigned", "project_id": request.project_id, "expenses_updated": updated}
