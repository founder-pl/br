"""
Expenses CRUD - Basic Create, Read, Update, Delete operations
"""
import uuid
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db
from ...services.expense_service import get_expense_service
from .models import (
    ExpenseCreate, ExpenseResponse, ExpenseStatusUpdate, 
    ProcessAllRequest, BRCategory, BR_CATEGORIES
)

logger = structlog.get_logger()
router = APIRouter()


def _row_to_expense_response(row) -> ExpenseResponse:
    """Convert database row to ExpenseResponse"""
    return ExpenseResponse(
        id=str(row[0]),
        project_id=str(row[1]),
        document_id=str(row[2]) if row[2] else None,
        invoice_number=row[3],
        invoice_date=row[4],
        vendor_name=row[5],
        vendor_nip=row[6],
        net_amount=float(row[7]),
        vat_amount=float(row[8]),
        gross_amount=float(row[9]),
        currency=row[10],
        expense_category=row[11],
        br_category=row[12],
        br_qualified=row[13] or False,
        br_qualification_reason=row[14],
        br_deduction_rate=float(row[15]) if row[15] else 1.0,
        ip_qualified=row[16] or False,
        ip_category=row[17],
        nexus_category=row[18],
        llm_classification=row[19],
        llm_confidence=float(row[20]) if row[20] else None,
        manual_override=row[21] or False,
        status=row[22],
        needs_clarification=row[23] or False,
        clarification_questions=row[24] or [],
        created_at=row[25]
    )


@router.get("/categories", response_model=List[BRCategory])
async def get_br_categories():
    """Get list of B+R expense categories according to art. 26e PIT"""
    return BR_CATEGORIES


@router.post("/process-all")
async def process_all_expenses(
    request: ProcessAllRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process all expenses for a project (validation, categorization, etc.)"""
    service = get_expense_service(db)
    result = await service.process_all(
        project_id=request.project_id,
        year=request.fiscal_year,
        month=request.month
    )
    return {"status": "processed", **result}


@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new expense record"""
    from .classification import classify_expense_with_llm
    
    expense_id = str(uuid.uuid4())
    
    await db.execute(
        text("""
        INSERT INTO read_models.expenses 
        (id, project_id, document_id, invoice_number, invoice_date, 
         vendor_name, vendor_nip, net_amount, vat_amount, gross_amount, 
         currency, expense_category, status)
        VALUES (:id, :project_id, :document_id, :invoice_number, :invoice_date,
                :vendor_name, :vendor_nip, :net_amount, :vat_amount, :gross_amount,
                :currency, :expense_category, 'draft')
        """),
        {
            "id": expense_id,
            "project_id": expense.project_id,
            "document_id": expense.document_id,
            "invoice_number": expense.invoice_number,
            "invoice_date": expense.invoice_date,
            "vendor_name": expense.vendor_name,
            "vendor_nip": expense.vendor_nip,
            "net_amount": float(expense.net_amount),
            "vat_amount": float(expense.vat_amount),
            "gross_amount": float(expense.gross_amount),
            "currency": expense.currency,
            "expense_category": expense.expense_category
        }
    )
    
    background_tasks.add_task(classify_expense_with_llm, expense_id)
    logger.info("Expense created", expense_id=expense_id)
    
    return await get_expense(expense_id, db)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, db: AsyncSession = Depends(get_db)):
    """Get expense details"""
    result = await db.execute(
        text("""
        SELECT id, project_id, document_id, invoice_number, invoice_date,
               vendor_name, vendor_nip, net_amount, vat_amount, gross_amount,
               currency, expense_category, br_category, br_qualified,
               br_qualification_reason, br_deduction_rate, ip_qualified,
               ip_category, nexus_category, llm_classification, llm_confidence,
               manual_override, status, needs_clarification, clarification_questions,
               created_at
        FROM read_models.expenses WHERE id = :id
        """),
        {"id": expense_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return _row_to_expense_response(row)


@router.get("/", response_model=List[ExpenseResponse])
async def list_expenses(
    project_id: Optional[str] = Query(default=None),
    br_qualified: Optional[bool] = Query(default=None),
    ip_qualified: Optional[bool] = Query(default=None),
    status: Optional[str] = Query(default=None),
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db)
):
    """List expenses with filtering"""
    query = """
        SELECT id, project_id, document_id, invoice_number, invoice_date,
               vendor_name, vendor_nip, net_amount, vat_amount, gross_amount,
               currency, expense_category, br_category, br_qualified,
               br_qualification_reason, br_deduction_rate, ip_qualified,
               ip_category, nexus_category, llm_classification, llm_confidence,
               manual_override, status, needs_clarification, clarification_questions,
               created_at
        FROM read_models.expenses WHERE 1=1
    """
    params = {}
    
    if project_id:
        query += " AND project_id = :project_id"
        params["project_id"] = project_id
    
    if br_qualified is not None:
        query += " AND br_qualified = :br_qualified"
        params["br_qualified"] = br_qualified
    
    if ip_qualified is not None:
        query += " AND ip_qualified = :ip_qualified"
        params["ip_qualified"] = ip_qualified
    
    if status:
        query += " AND status = :status"
        params["status"] = status
    
    if year:
        query += " AND EXTRACT(YEAR FROM invoice_date) = :year"
        params["year"] = year
    
    if month:
        query += " AND EXTRACT(MONTH FROM invoice_date) = :month"
        params["month"] = month
    
    query += " ORDER BY invoice_date DESC NULLS LAST LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [_row_to_expense_response(row) for row in rows]


@router.put("/{expense_id}/status")
async def update_expense_status(
    expense_id: str,
    status_update: ExpenseStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update expense status"""
    valid_statuses = ['draft', 'classified', 'approved', 'rejected']
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.execute(
        text("SELECT id FROM read_models.expenses WHERE id = :id"),
        {"id": expense_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await db.execute(
        text("UPDATE read_models.expenses SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"id": expense_id, "status": status_update.status}
    )
    
    logger.info("Expense status updated", expense_id=expense_id, status=status_update.status)
    return {"status": "updated", "expense_id": expense_id, "new_status": status_update.status}


@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an expense"""
    result = await db.execute(
        text("SELECT id FROM read_models.expenses WHERE id = :id"),
        {"id": expense_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await db.execute(
        text("DELETE FROM read_models.expenses WHERE id = :id"),
        {"id": expense_id}
    )
    await db.commit()
    
    logger.info("Expense deleted", expense_id=expense_id)
    return {"status": "deleted", "expense_id": expense_id}


@router.put("/{expense_id}/vendor")
async def update_expense_vendor(
    expense_id: str,
    vendor_name: str = Query(...),
    vendor_nip: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Update vendor information for an expense"""
    result = await db.execute(
        text("SELECT id FROM read_models.expenses WHERE id = :id"),
        {"id": expense_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if vendor_nip:
        from src.ocr.extractors import validate_nip
        if not validate_nip(vendor_nip):
            raise HTTPException(status_code=400, detail=f"Nieprawidłowy NIP: {vendor_nip}")
    
    await db.execute(
        text("""
            UPDATE read_models.expenses SET
                vendor_name = :vendor_name,
                vendor_nip = :vendor_nip,
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": expense_id, "vendor_name": vendor_name, "vendor_nip": vendor_nip}
    )
    await db.commit()
    
    logger.info("Vendor updated", expense_id=expense_id, vendor=vendor_name)
    
    return {
        "status": "updated",
        "expense_id": expense_id,
        "vendor_name": vendor_name,
        "vendor_nip": vendor_nip
    }
