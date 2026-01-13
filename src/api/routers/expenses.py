"""
Expenses Router - B+R and IP Box expense management
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

import httpx
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db
from ..config import settings

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Models
# =============================================================================

class ExpenseCreate(BaseModel):
    """Create expense request"""
    document_id: Optional[str] = None
    project_id: str = "00000000-0000-0000-0000-000000000001"
    
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    vendor_name: Optional[str] = None
    vendor_nip: Optional[str] = None
    
    net_amount: Decimal
    vat_amount: Decimal = Decimal("0")
    gross_amount: Decimal
    currency: str = "PLN"
    
    expense_category: Optional[str] = None
    description: Optional[str] = None


class ExpenseResponse(BaseModel):
    """Expense response"""
    id: str
    project_id: str
    document_id: Optional[str]
    
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    vendor_name: Optional[str]
    vendor_nip: Optional[str]
    
    net_amount: float
    vat_amount: float
    gross_amount: float
    currency: str
    
    expense_category: Optional[str]
    br_category: Optional[str]
    br_qualified: bool
    br_qualification_reason: Optional[str]
    br_deduction_rate: float
    
    ip_qualified: bool
    ip_category: Optional[str]
    nexus_category: Optional[str]
    
    llm_classification: Optional[dict]
    llm_confidence: Optional[float]
    manual_override: bool
    
    status: str
    needs_clarification: bool
    clarification_questions: Optional[List[dict]]
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExpenseClassifyRequest(BaseModel):
    """Manual classification request"""
    br_qualified: Optional[bool] = None
    br_category: Optional[str] = None
    br_qualification_reason: Optional[str] = None
    br_deduction_rate: Optional[float] = None
    ip_qualified: Optional[bool] = None
    ip_category: Optional[str] = None
    nexus_category: Optional[str] = None


class BRCategory(BaseModel):
    """B+R expense category"""
    code: str
    name: str
    description: str
    deduction_rate: float
    examples: List[str]


# =============================================================================
# B+R Categories (zgodnie z art. 26e PIT)
# =============================================================================

BR_CATEGORIES = [
    BRCategory(
        code="personnel_employment",
        name="Wynagrodzenia pracowników (umowa o pracę)",
        description="Wynagrodzenia pracowników zatrudnionych na umowę o pracę, realizujących działalność B+R",
        deduction_rate=2.0,
        examples=["Pensje programistów", "Wynagrodzenia inżynierów", "Premie za projekty B+R"]
    ),
    BRCategory(
        code="personnel_civil",
        name="Wynagrodzenia (umowy cywilnoprawne)",
        description="Wynagrodzenia z tytułu umów zlecenie i o dzieło za działalność B+R",
        deduction_rate=2.0,
        examples=["Umowy zlecenie z konsultantami", "Umowy o dzieło za prototypy"]
    ),
    BRCategory(
        code="materials",
        name="Materiały i surowce",
        description="Materiały i surowce bezpośrednio związane z działalnością B+R",
        deduction_rate=1.0,
        examples=["Komponenty elektroniczne", "Licencje oprogramowania", "Materiały do prototypów"]
    ),
    BRCategory(
        code="equipment",
        name="Sprzęt specjalistyczny",
        description="Sprzęt specjalistyczny niebędący środkami trwałymi",
        deduction_rate=1.0,
        examples=["Narzędzia pomiarowe", "Sprzęt laboratoryjny", "Urządzenia testowe"]
    ),
    BRCategory(
        code="depreciation",
        name="Odpisy amortyzacyjne",
        description="Odpisy amortyzacyjne od środków trwałych używanych w B+R",
        deduction_rate=1.0,
        examples=["Amortyzacja komputerów", "Amortyzacja serwerów", "Amortyzacja sprzętu laboratoryjnego"]
    ),
    BRCategory(
        code="expertise",
        name="Ekspertyzy od jednostek naukowych",
        description="Ekspertyzy, opinie, usługi doradcze od jednostek naukowych",
        deduction_rate=1.0,
        examples=["Opinie uczelni", "Ekspertyzy instytutów badawczych", "Recenzje naukowe"]
    ),
    BRCategory(
        code="external_services",
        name="Usługi zewnętrzne B+R",
        description="Usługi od podmiotów zewnętrznych związane z działalnością B+R",
        deduction_rate=1.0,
        examples=["Testy laboratoryjne", "Certyfikacje", "Usługi prototypowania"]
    ),
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/categories", response_model=List[BRCategory])
async def get_br_categories():
    """Get list of B+R expense categories according to art. 26e PIT"""
    return BR_CATEGORIES


@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new expense record"""
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
    
    # Queue LLM classification
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


@router.get("/", response_model=List[ExpenseResponse])
async def list_expenses(
    project_id: Optional[str] = Query(default=None),
    br_qualified: Optional[bool] = Query(default=None),
    ip_qualified: Optional[bool] = Query(default=None),
    status: Optional[str] = Query(default=None),
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=100),
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
    
    return [
        ExpenseResponse(
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
        for row in rows
    ]


@router.put("/{expense_id}/classify", response_model=ExpenseResponse)
async def classify_expense_manually(
    expense_id: str,
    classification: ExpenseClassifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Manually classify expense for B+R or IP Box"""
    updates = []
    params = {"id": expense_id}
    
    if classification.br_qualified is not None:
        updates.append("br_qualified = :br_qualified")
        params["br_qualified"] = classification.br_qualified
    
    if classification.br_category:
        updates.append("br_category = :br_category")
        params["br_category"] = classification.br_category
    
    if classification.br_qualification_reason:
        updates.append("br_qualification_reason = :br_qualification_reason")
        params["br_qualification_reason"] = classification.br_qualification_reason
    
    if classification.br_deduction_rate:
        updates.append("br_deduction_rate = :br_deduction_rate")
        params["br_deduction_rate"] = classification.br_deduction_rate
    
    if classification.ip_qualified is not None:
        updates.append("ip_qualified = :ip_qualified")
        params["ip_qualified"] = classification.ip_qualified
    
    if classification.ip_category:
        updates.append("ip_category = :ip_category")
        params["ip_category"] = classification.ip_category
    
    if classification.nexus_category:
        updates.append("nexus_category = :nexus_category")
        params["nexus_category"] = classification.nexus_category
    
    if updates:
        updates.append("manual_override = true")
        updates.append("status = 'classified'")
        updates.append("updated_at = NOW()")
        
        await db.execute(
            text(f"UPDATE read_models.expenses SET {', '.join(updates)} WHERE id = :id"),
            params
        )
    
    logger.info("Expense classified manually", expense_id=expense_id)
    return await get_expense(expense_id, db)


@router.post("/{expense_id}/auto-classify")
async def trigger_auto_classification(
    expense_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger automatic LLM classification"""
    # Verify expense exists
    result = await db.execute(
        text("SELECT id FROM read_models.expenses WHERE id = :id"),
        {"id": expense_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    background_tasks.add_task(classify_expense_with_llm, expense_id)
    
    return {"status": "queued", "message": "Classification queued"}


class ExpenseStatusUpdate(BaseModel):
    """Status update request"""
    status: str


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
    
    logger.info("Expense deleted", expense_id=expense_id)
    return {"status": "deleted", "expense_id": expense_id}


@router.post("/{expense_id}/generate-doc")
async def generate_expense_documentation(
    expense_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate B+R documentation for a single expense"""
    from ..services.doc_generator import get_doc_generator
    
    # Get expense data
    result = await db.execute(
        text("""
        SELECT e.*, p.name as project_name, p.fiscal_year, p.description as project_description,
               d.ocr_text, d.extracted_data
        FROM read_models.expenses e
        JOIN read_models.projects p ON e.project_id = p.id
        LEFT JOIN read_models.documents d ON e.document_id = d.id
        WHERE e.id = :id
        """),
        {"id": expense_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Convert to dict
    expense = {
        'id': str(row[0]),
        'project_id': str(row[1]),
        'document_id': str(row[2]) if row[2] else None,
        'invoice_number': row[3],
        'invoice_date': str(row[4]) if row[4] else None,
        'vendor_name': row[5],
        'vendor_nip': row[6],
        'gross_amount': float(row[7] or 0),
        'net_amount': float(row[8] or 0),
        'vat_amount': float(row[9] or 0),
        'currency': row[10],
        'description': row[11],
        'expense_category': row[12],
        'br_category': row[13],
        'br_qualified': row[14],
        'br_deduction_rate': float(row[15] or 1.0),
        'br_qualification_reason': row[16],
        'status': row[17]
    }
    
    project = {
        'id': str(row[1]),
        'name': row[21],  # project_name
        'fiscal_year': row[22],
        'description': row[23]
    }
    
    document = None
    if row[24]:  # ocr_text
        document = {
            'ocr_text': row[24],
            'extracted_data': row[25]
        }
    
    # Generate documentation
    doc_generator = get_doc_generator()
    result = await doc_generator.generate_expense_documentation(expense, project, document)
    
    logger.info("Expense documentation generated", expense_id=expense_id, file=result.get('file_path'))
    return result


@router.post("/project/{project_id}/generate-summary")
async def generate_project_documentation_summary(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate B+R documentation summary for entire project"""
    from ..services.doc_generator import get_doc_generator
    
    # Get project
    proj_result = await db.execute(
        text("SELECT id, name, description, fiscal_year FROM read_models.projects WHERE id = :id"),
        {"id": project_id}
    )
    proj_row = proj_result.fetchone()
    
    if not proj_row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = {
        'id': str(proj_row[0]),
        'name': proj_row[1],
        'description': proj_row[2],
        'fiscal_year': proj_row[3]
    }
    
    # Get all expenses for project
    exp_result = await db.execute(
        text("""
        SELECT id, invoice_number, invoice_date, vendor_name, vendor_nip,
               gross_amount, net_amount, vat_amount, currency,
               br_category, br_qualified, br_deduction_rate, br_qualification_reason, status
        FROM read_models.expenses WHERE project_id = :project_id
        ORDER BY invoice_date
        """),
        {"project_id": project_id}
    )
    
    expenses = []
    for row in exp_result.fetchall():
        expenses.append({
            'id': str(row[0]),
            'invoice_number': row[1],
            'invoice_date': str(row[2]) if row[2] else None,
            'vendor_name': row[3],
            'vendor_nip': row[4],
            'gross_amount': float(row[5] or 0),
            'net_amount': float(row[6] or 0),
            'vat_amount': float(row[7] or 0),
            'currency': row[8],
            'br_category': row[9],
            'br_qualified': row[10],
            'br_deduction_rate': float(row[11] or 1.0),
            'br_qualification_reason': row[12],
            'status': row[13]
        })
    
    # Get timesheet summary for current year
    year = project['fiscal_year']
    timesheet_data = None
    try:
        ts_result = await db.execute(
            text("""
                SELECT p.name as project_name, SUM(t.hours) as total_hours
                FROM read_models.timesheet_entries t
                JOIN read_models.projects p ON t.project_id = p.id
                WHERE t.project_id = :project_id
                  AND EXTRACT(YEAR FROM t.work_date) = :year
                GROUP BY p.name
            """),
            {"project_id": project_id, "year": year}
        )
        by_project = [{"project_name": r[0], "total_hours": float(r[1])} for r in ts_result.fetchall()]
        
        worker_result = await db.execute(
            text("""
                SELECT w.name as worker_name, SUM(t.hours) as total_hours
                FROM read_models.timesheet_entries t
                JOIN read_models.workers w ON t.worker_id = w.id
                WHERE t.project_id = :project_id
                  AND EXTRACT(YEAR FROM t.work_date) = :year
                GROUP BY w.name
            """),
            {"project_id": project_id, "year": year}
        )
        by_worker = [{"worker_name": r[0], "total_hours": float(r[1])} for r in worker_result.fetchall()]
        
        total_hours = sum(p["total_hours"] for p in by_project)
        if total_hours > 0:
            timesheet_data = {
                "total_hours": total_hours,
                "by_project": by_project,
                "by_worker": by_worker
            }
    except Exception as e:
        logger.warning("Could not load timesheet data", error=str(e))
    
    # Get contractors from expenses
    contractors = []
    try:
        contr_result = await db.execute(
            text("""
                SELECT vendor_name, vendor_nip, SUM(gross_amount) as total, COUNT(*) as count
                FROM read_models.expenses
                WHERE project_id = :project_id AND vendor_name IS NOT NULL AND vendor_name != ''
                GROUP BY vendor_name, vendor_nip
                ORDER BY total DESC
            """),
            {"project_id": project_id}
        )
        contractors = [
            {"vendor_name": r[0], "vendor_nip": r[1], "total_amount": float(r[2]), "invoice_count": r[3]}
            for r in contr_result.fetchall()
        ]
    except Exception as e:
        logger.warning("Could not load contractors data", error=str(e))
    
    # Get revenues for this project
    revenues = []
    try:
        rev_result = await db.execute(
            text("""
                SELECT id, invoice_number, invoice_date, client_name, client_nip,
                       gross_amount, net_amount, currency, ip_description
                FROM read_models.revenues
                WHERE project_id = :project_id
                ORDER BY invoice_date
            """),
            {"project_id": project_id}
        )
        revenues = [
            {
                "id": str(r[0]),
                "invoice_number": r[1],
                "invoice_date": str(r[2]) if r[2] else None,
                "client_name": r[3],
                "client_nip": r[4],
                "gross_amount": float(r[5] or 0),
                "net_amount": float(r[6] or 0),
                "currency": r[7],
                "ip_description": r[8]
            }
            for r in rev_result.fetchall()
        ]
    except Exception as e:
        logger.warning("Could not load revenues data", error=str(e))
    
    # Generate summary documentation
    doc_generator = get_doc_generator()
    result = await doc_generator.generate_project_summary(project, expenses, timesheet_data, contractors, revenues)
    
    logger.info("Project summary generated", project_id=project_id, expenses=len(expenses), revenues=len(revenues))
    
    # Recalculate project totals after generating summary
    await db.execute(
        text("""
        UPDATE read_models.projects SET
            total_expenses = COALESCE((SELECT SUM(gross_amount) FROM read_models.expenses WHERE project_id = :id), 0),
            br_qualified_expenses = COALESCE((SELECT SUM(gross_amount) FROM read_models.expenses WHERE project_id = :id AND br_qualified = true), 0),
            updated_at = NOW()
        WHERE id = :id
        """),
        {"id": project_id}
    )
    
    return result


@router.get("/project/{project_id}/docs")
async def list_project_documentation(project_id: str):
    """List all generated documentation files for a project"""
    from pathlib import Path
    
    docs_dir = Path('/app/reports/br_docs') / project_id
    
    if not docs_dir.exists():
        return {"project_id": project_id, "files": []}
    
    files = []
    for f in sorted(docs_dir.glob('*.md'), reverse=True):
        files.append({
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime
        })
    
    return {"project_id": project_id, "files": files}


@router.get("/project/{project_id}/docs/{filename}")
async def get_documentation_content(project_id: str, filename: str):
    """Get content of a specific documentation file"""
    from pathlib import Path
    
    file_path = Path('/app/reports/br_docs') / project_id / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Documentation file not found")
    
    # Security check - ensure path is within docs directory
    if '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    content = file_path.read_text(encoding='utf-8')
    return {"filename": filename, "content": content, "project_id": project_id}


@router.get("/project/{project_id}/docs/{filename}/history")
async def get_documentation_history(project_id: str, filename: str):
    """Get version history for a documentation file"""
    from ..services.doc_generator import get_doc_generator
    
    if '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    doc_generator = get_doc_generator()
    history = doc_generator.get_document_history(project_id, filename)
    
    return {
        "project_id": project_id,
        "filename": filename,
        "history": history
    }


@router.get("/project/{project_id}/docs/{filename}/version/{commit}")
async def get_documentation_version(project_id: str, filename: str, commit: str):
    """Get document content at specific version"""
    from ..services.doc_generator import get_doc_generator
    
    if '..' in filename or '..' in commit:
        raise HTTPException(status_code=400, detail="Invalid parameters")
    
    doc_generator = get_doc_generator()
    content = doc_generator.get_document_at_version(project_id, filename, commit)
    
    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "project_id": project_id,
        "filename": filename,
        "commit": commit,
        "content": content
    }


@router.get("/project/{project_id}/docs/{filename}/pdf")
async def get_documentation_pdf(project_id: str, filename: str):
    """Generate and return PDF from markdown documentation"""
    from pathlib import Path
    from fastapi.responses import Response
    import subprocess
    import tempfile
    
    md_path = Path('/app/reports/br_docs') / project_id / filename
    
    if not md_path.exists() or not md_path.is_file():
        raise HTTPException(status_code=404, detail="Documentation file not found")
    
    if '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Read markdown content
    md_content = md_path.read_text(encoding='utf-8')
    
    # Convert to simple HTML with styling for PDF
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #1e40af; border-bottom: 2px solid #1e40af; padding-bottom: 10px; }}
        h2 {{ color: #1e40af; margin-top: 30px; }}
        h3 {{ color: #374151; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #1e40af; color: white; padding: 10px; text-align: left; }}
        td {{ border: 1px solid #e5e7eb; padding: 8px; }}
        tr:nth-child(even) td {{ background: #f9fafb; }}
        hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 30px 0; }}
        .footer {{ margin-top: 50px; font-size: 12px; color: #6b7280; font-style: italic; }}
    </style>
</head>
<body>
"""
    
    # Simple markdown to HTML conversion for PDF
    lines = md_content.split('\n')
    in_table = False
    table_html = ''
    
    for line in lines:
        # Table handling
        if line.strip().startswith('|') and line.strip().endswith('|'):
            if not in_table:
                in_table = True
                table_html = '<table>'
            
            # Check if separator
            cleaned = line.replace('|', '').strip()
            if cleaned and all(c in '-: ' for c in cleaned):
                continue
            
            cells = [c.strip() for c in line.split('|')[1:-1]]
            tag = 'th' if not table_html.count('<tr>') else 'td'
            table_html += '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
            continue
        elif in_table:
            table_html += '</table>'
            html_content += table_html
            in_table = False
            table_html = ''
        
        # Headers
        if line.startswith('### '):
            html_content += f'<h3>{line[4:]}</h3>'
        elif line.startswith('## '):
            html_content += f'<h2>{line[3:]}</h2>'
        elif line.startswith('# '):
            html_content += f'<h1>{line[2:]}</h1>'
        elif line.strip() == '---':
            html_content += '<hr>'
        elif line.strip():
            # Bold
            line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
            while '**' in line:
                line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
            html_content += f'<p>{line}</p>'
    
    if in_table:
        table_html += '</table>'
        html_content += table_html
    
    html_content += '</body></html>'
    
    # Try to generate PDF using weasyprint or return HTML
    pdf_filename = filename.replace('.md', '.pdf')
    
    try:
        # Try weasyprint
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{pdf_filename}"'}
        )
    except ImportError:
        # Fallback: return HTML for browser printing
        return Response(
            content=html_content.encode('utf-8'),
            media_type='text/html',
            headers={'Content-Disposition': f'inline; filename="{pdf_filename.replace(".pdf", ".html")}"'}
        )


async def classify_expense_with_llm(expense_id: str):
    """Background task to classify expense using LLM"""
    from ..database import get_db_context
    import json
    
    try:
        # Get expense data
        async with get_db_context() as db:
            result = await db.execute(
        text("""
                SELECT e.*, d.ocr_text, d.extracted_data
                FROM read_models.expenses e
                LEFT JOIN read_models.documents d ON e.document_id = d.id
                WHERE e.id = :id
                """),
                {"id": expense_id}
            )
            row = result.fetchone()
            
            if not row:
                return
        
        # Build prompt for LLM
        prompt = build_classification_prompt(row)
        
        # Call LLM service
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/v1/chat/completions",
                json={
                    "model": "br-classifier",
                    "messages": [
                        {"role": "system", "content": get_br_classifier_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0,
                    "max_tokens": 2000
                },
                headers={"Authorization": f"Bearer {settings.SECRET_KEY}"}
            )
        
        if response.status_code == 200:
            llm_result = response.json()
            classification = parse_llm_classification(
                llm_result['choices'][0]['message']['content']
            )
            
            # Update expense with classification
            async with get_db_context() as db:
                await db.execute(
        text("""
                    UPDATE read_models.expenses SET
                        br_qualified = :br_qualified,
                        br_category = :br_category,
                        br_qualification_reason = :br_reason,
                        br_deduction_rate = :br_rate,
                        ip_qualified = :ip_qualified,
                        nexus_category = :nexus,
                        llm_classification = CAST(:llm_data AS jsonb),
                        llm_confidence = :confidence,
                        needs_clarification = :needs_clarification,
                        clarification_questions = CAST(:questions AS jsonb),
                        status = 'classified',
                        updated_at = NOW()
                    WHERE id = :id
                    """),
                    {
                        "id": expense_id,
                        "br_qualified": classification.get('br_qualified', False),
                        "br_category": classification.get('br_category'),
                        "br_reason": classification.get('br_reason'),
                        "br_rate": classification.get('br_rate', 1.0),
                        "ip_qualified": classification.get('ip_qualified', False),
                        "nexus": classification.get('nexus_category'),
                        "llm_data": json.dumps(classification),
                        "confidence": classification.get('confidence', 0.5),
                        "needs_clarification": classification.get('needs_clarification', False),
                        "questions": json.dumps(classification.get('questions', []))
                    }
                )
            
            logger.info("Expense classified by LLM", 
                       expense_id=expense_id,
                       br_qualified=classification.get('br_qualified'))
    
    except Exception as e:
        logger.error("LLM classification failed", expense_id=expense_id, error=str(e))


def get_br_classifier_system_prompt() -> str:
    """System prompt for B+R expense classifier"""
    return """Jesteś ekspertem od polskiego prawa podatkowego, specjalizującym się w uldze B+R (art. 26e ustawy o PIT) oraz IP Box (art. 30ca-30cb).

Twoim zadaniem jest klasyfikacja wydatków pod kątem:
1. Kwalifikowalności do ulgi B+R
2. Kategorii kosztów kwalifikowanych
3. Stawki odliczenia (100% lub 200%)
4. Kwalifikowalności do IP Box (kategoria nexus: a, b, c, d)

KATEGORIE KOSZTÓW B+R (zgodnie z art. 26e PIT):
- personnel_employment (200%): wynagrodzenia pracowników B+R (umowa o pracę)
- personnel_civil (200%): umowy zlecenie/o dzieło za prace B+R
- materials (100%): materiały i surowce do B+R
- equipment (100%): sprzęt specjalistyczny niebędący ŚT
- depreciation (100%): odpisy amortyzacyjne ŚT używanych w B+R
- expertise (100%): ekspertyzy od jednostek naukowych
- external_services (100%): usługi zewnętrzne B+R

KATEGORIE NEXUS (dla IP Box):
- a: własna działalność B+R (najkorzystniejsza)
- b: nabycie B+R od podmiotów niepowiązanych
- c: nabycie B+R od podmiotów powiązanych
- d: nabycie kwalifikowanego IP

Odpowiadaj TYLKO w formacie JSON:
{
  "br_qualified": true/false,
  "br_category": "kategoria lub null",
  "br_reason": "uzasadnienie klasyfikacji",
  "br_rate": 1.0 lub 2.0,
  "ip_qualified": true/false,
  "nexus_category": "a/b/c/d lub null",
  "confidence": 0.0-1.0,
  "needs_clarification": true/false,
  "questions": ["pytanie1", "pytanie2"] lub []
}"""


def build_classification_prompt(expense_row) -> str:
    """Build prompt for expense classification"""
    return f"""Sklasyfikuj następujący wydatek dla projektu B+R:

DANE WYDATKU:
- Numer faktury: {expense_row[3] or 'brak'}
- Data: {expense_row[4] or 'brak'}
- Dostawca: {expense_row[5] or 'brak'}
- NIP dostawcy: {expense_row[6] or 'brak'}
- Kwota netto: {expense_row[7]} PLN
- Kwota brutto: {expense_row[9]} PLN
- Kategoria: {expense_row[11] or 'brak'}

TREŚĆ DOKUMENTU (OCR):
{expense_row[-2] or 'brak treści'}

DANE WYEKSTRAHOWANE:
{expense_row[-1] or 'brak danych'}

Czy ten wydatek kwalifikuje się do ulgi B+R? Jeśli tak, do jakiej kategorii?
Czy kwalifikuje się do IP Box (nexus)? Jeśli brakuje informacji, wskaż jakie pytania zadać."""


def parse_llm_classification(response: str) -> dict:
    """Parse LLM response to classification dict"""
    import json
    try:
        # Find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    
    # Default if parsing fails
    return {
        "br_qualified": False,
        "confidence": 0.3,
        "needs_clarification": True,
        "questions": ["Nie udało się automatycznie sklasyfikować wydatku. Proszę o ręczną klasyfikację."]
    }
