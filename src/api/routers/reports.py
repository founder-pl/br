"""
Reports Router - Monthly B+R reports for US
"""
import uuid
from datetime import datetime
from typing import Optional, List
import json

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..database import get_db
from ..config import settings

logger = structlog.get_logger()
router = APIRouter()


class MonthlyReportResponse(BaseModel):
    id: str
    project_id: str
    fiscal_year: int
    month: int
    total_expenses: float
    br_expenses: float
    br_deduction: float
    ip_expenses: float
    total_revenues: float
    ip_revenues: float
    documents_count: int
    pending_documents: int
    needs_clarification: int
    status: str
    generated_at: Optional[datetime]
    report_data: Optional[dict]
    created_at: datetime


class ReportGenerateRequest(BaseModel):
    project_id: str = "00000000-0000-0000-0000-000000000001"
    fiscal_year: int
    month: int = Field(ge=1, le=12)
    regenerate: bool = False


class AnnualBRSummary(BaseModel):
    fiscal_year: int
    company_name: str
    company_nip: str
    project_name: str
    personnel_employment: float = 0
    personnel_civil: float = 0
    materials: float = 0
    equipment: float = 0
    depreciation: float = 0
    expertise: float = 0
    external_services: float = 0
    total_br_costs: float = 0
    total_br_deduction: float = 0
    monthly_expenses: List[dict]


class IPBoxSummary(BaseModel):
    fiscal_year: int
    company_name: str
    company_nip: str
    ip_revenues: float = 0
    nexus_a: float = 0
    nexus_b: float = 0
    nexus_c: float = 0
    nexus_d: float = 0
    nexus_ratio: float = 0
    qualified_income: float = 0
    tax_5_percent: float = 0


@router.post("/monthly/generate", response_model=MonthlyReportResponse)
async def generate_monthly_report(
    request: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate or regenerate monthly B+R report"""
    existing = await db.execute(
        text("""SELECT id FROM read_models.monthly_reports 
        WHERE project_id = :project_id AND fiscal_year = :year AND month = :month"""),
        {"project_id": request.project_id, "year": request.fiscal_year, "month": request.month}
    )
    existing_row = existing.fetchone()
    
    if existing_row and not request.regenerate:
        return await get_monthly_report(str(existing_row[0]), db)
    
    report_id = str(existing_row[0]) if existing_row else str(uuid.uuid4())
    report_data = await calculate_monthly_report(db, request.project_id, request.fiscal_year, request.month)
    
    if existing_row:
        await db.execute(
        text("""UPDATE read_models.monthly_reports SET
                total_expenses = :total_expenses, br_expenses = :br_expenses,
                br_deduction = :br_deduction, ip_expenses = :ip_expenses,
                total_revenues = :total_revenues, ip_revenues = :ip_revenues,
                documents_count = :doc_count, pending_documents = :pending,
                needs_clarification = :needs_clarification, status = 'generated',
                generated_at = NOW(), report_data = :report_data::jsonb, updated_at = NOW()
            WHERE id = :id"""),
            {"id": report_id, **report_data}
        )
    else:
        await db.execute(
        text("""INSERT INTO read_models.monthly_reports
            (id, project_id, fiscal_year, month, total_expenses, br_expenses,
             br_deduction, ip_expenses, total_revenues, ip_revenues,
             documents_count, pending_documents, needs_clarification,
             status, generated_at, report_data)
            VALUES (:id, :project_id, :fiscal_year, :month, :total_expenses,
                    :br_expenses, :br_deduction, :ip_expenses, :total_revenues,
                    :ip_revenues, :doc_count, :pending, :needs_clarification,
                    'generated', NOW(), :report_data::jsonb)"""),
            {"id": report_id, "project_id": request.project_id, "fiscal_year": request.fiscal_year,
             "month": request.month, **report_data}
        )
    
    logger.info("Monthly report generated", year=request.fiscal_year, month=request.month)
    return await get_monthly_report(report_id, db)


async def calculate_monthly_report(db: AsyncSession, project_id: str, year: int, month: int) -> dict:
    expense_result = await db.execute(
        text("""SELECT COALESCE(SUM(gross_amount), 0), 
            COALESCE(SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN br_qualified THEN gross_amount * br_deduction_rate ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN ip_qualified THEN gross_amount ELSE 0 END), 0)
        FROM read_models.expenses WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM invoice_date) = :year AND EXTRACT(MONTH FROM invoice_date) = :month"""),
        {"project_id": project_id, "year": year, "month": month}
    )
    e = expense_result.fetchone()
    
    revenue_result = await db.execute(
        text("""SELECT COALESCE(SUM(gross_amount), 0), 
            COALESCE(SUM(CASE WHEN ip_qualified THEN gross_amount ELSE 0 END), 0)
        FROM read_models.revenues WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM invoice_date) = :year AND EXTRACT(MONTH FROM invoice_date) = :month"""),
        {"project_id": project_id, "year": year, "month": month}
    )
    r = revenue_result.fetchone()
    
    doc_result = await db.execute(
        text("""SELECT COUNT(*), SUM(CASE WHEN ocr_status = 'pending' THEN 1 ELSE 0 END)
        FROM read_models.documents WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM created_at) = :year AND EXTRACT(MONTH FROM created_at) = :month"""),
        {"project_id": project_id, "year": year, "month": month}
    )
    d = doc_result.fetchone()
    
    clarification_count = (await db.execute(
        text("""SELECT COUNT(*) FROM read_models.expenses WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM invoice_date) = :year AND EXTRACT(MONTH FROM invoice_date) = :month
        AND needs_clarification = true"""),
        {"project_id": project_id, "year": year, "month": month}
    )).scalar() or 0
    
    return {
        "total_expenses": float(e[0]), "br_expenses": float(e[1]),
        "br_deduction": float(e[2]), "ip_expenses": float(e[3]),
        "total_revenues": float(r[0]) if r else 0, "ip_revenues": float(r[1]) if r else 0,
        "doc_count": int(d[0]) if d else 0, "pending": int(d[1]) if d else 0,
        "needs_clarification": int(clarification_count), "report_data": "{}"
    }


@router.get("/monthly/{report_id}", response_model=MonthlyReportResponse)
async def get_monthly_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("""SELECT id, project_id, fiscal_year, month, total_expenses, br_expenses,
               br_deduction, ip_expenses, total_revenues, ip_revenues,
               documents_count, pending_documents, needs_clarification,
               status, generated_at, report_data, created_at
        FROM read_models.monthly_reports WHERE id = :id"""),
        {"id": report_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return MonthlyReportResponse(
        id=str(row[0]), project_id=str(row[1]), fiscal_year=row[2], month=row[3],
        total_expenses=float(row[4] or 0), br_expenses=float(row[5] or 0),
        br_deduction=float(row[6] or 0), ip_expenses=float(row[7] or 0),
        total_revenues=float(row[8] or 0), ip_revenues=float(row[9] or 0),
        documents_count=row[10] or 0, pending_documents=row[11] or 0,
        needs_clarification=row[12] or 0, status=row[13],
        generated_at=row[14], report_data=row[15], created_at=row[16]
    )


@router.get("/monthly", response_model=List[MonthlyReportResponse])
async def list_monthly_reports(
    project_id: Optional[str] = Query(default=None),
    fiscal_year: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    query = """SELECT id, project_id, fiscal_year, month, total_expenses, br_expenses,
               br_deduction, ip_expenses, total_revenues, ip_revenues,
               documents_count, pending_documents, needs_clarification,
               status, generated_at, report_data, created_at
        FROM read_models.monthly_reports WHERE 1=1"""
    params = {}
    if project_id:
        query += " AND project_id = :project_id"
        params["project_id"] = project_id
    if fiscal_year:
        query += " AND fiscal_year = :fiscal_year"
        params["fiscal_year"] = fiscal_year
    query += " ORDER BY fiscal_year DESC, month DESC"
    
    result = await db.execute(text(query), params)
    return [MonthlyReportResponse(
        id=str(r[0]), project_id=str(r[1]), fiscal_year=r[2], month=r[3],
        total_expenses=float(r[4] or 0), br_expenses=float(r[5] or 0),
        br_deduction=float(r[6] or 0), ip_expenses=float(r[7] or 0),
        total_revenues=float(r[8] or 0), ip_revenues=float(r[9] or 0),
        documents_count=r[10] or 0, pending_documents=r[11] or 0,
        needs_clarification=r[12] or 0, status=r[13],
        generated_at=r[14], report_data=r[15], created_at=r[16]
    ) for r in result.fetchall()]


@router.get("/annual/br-summary", response_model=AnnualBRSummary)
async def get_annual_br_summary(
    fiscal_year: int = Query(...),
    project_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db)
):
    project_result = await db.execute(
        text("SELECT name FROM read_models.projects WHERE id = :id"), {"id": project_id}
    )
    project_row = project_result.fetchone()
    project_name = project_row[0] if project_row else "Unknown"
    
    category_result = await db.execute(
        text("""SELECT br_category, SUM(gross_amount), SUM(gross_amount * br_deduction_rate)
        FROM read_models.expenses WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM invoice_date) = :year AND br_qualified = true
        GROUP BY br_category"""),
        {"project_id": project_id, "year": fiscal_year}
    )
    
    categories = {}
    total_costs = 0
    total_deduction = 0
    for row in category_result.fetchall():
        cat = row[0] or "other"
        amount = float(row[1] or 0)
        deduction = float(row[2] or 0)
        categories[cat] = amount
        total_costs += amount
        total_deduction += deduction
    
    monthly_result = await db.execute(
        text("""SELECT EXTRACT(MONTH FROM invoice_date), SUM(gross_amount),
               SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END)
        FROM read_models.expenses WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM invoice_date) = :year
        GROUP BY EXTRACT(MONTH FROM invoice_date) ORDER BY 1"""),
        {"project_id": project_id, "year": fiscal_year}
    )
    monthly = [{"month": int(r[0]), "total": float(r[1] or 0), "br": float(r[2] or 0)}
               for r in monthly_result.fetchall()]
    
    return AnnualBRSummary(
        fiscal_year=fiscal_year, company_name=settings.COMPANY_NAME,
        company_nip=settings.COMPANY_NIP, project_name=project_name,
        personnel_employment=categories.get("personnel_employment", 0),
        personnel_civil=categories.get("personnel_civil", 0),
        materials=categories.get("materials", 0),
        equipment=categories.get("equipment", 0),
        depreciation=categories.get("depreciation", 0),
        expertise=categories.get("expertise", 0),
        external_services=categories.get("external_services", 0),
        total_br_costs=total_costs, total_br_deduction=total_deduction,
        monthly_expenses=monthly
    )


@router.get("/annual/ip-box-summary", response_model=IPBoxSummary)
async def get_annual_ip_box_summary(
    fiscal_year: int = Query(...),
    project_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db)
):
    ip_revenues = float((await db.execute(
        text("""SELECT COALESCE(SUM(gross_amount), 0) FROM read_models.revenues 
        WHERE project_id = :project_id AND EXTRACT(YEAR FROM invoice_date) = :year
        AND ip_qualified = true"""),
        {"project_id": project_id, "year": fiscal_year}
    )).scalar() or 0)
    
    nexus_result = await db.execute(
        text("""SELECT nexus_category, COALESCE(SUM(gross_amount), 0)
        FROM read_models.expenses WHERE project_id = :project_id
        AND EXTRACT(YEAR FROM invoice_date) = :year AND ip_qualified = true
        GROUP BY nexus_category"""),
        {"project_id": project_id, "year": fiscal_year}
    )
    
    nexus = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}
    for row in nexus_result.fetchall():
        if row[0] in nexus:
            nexus[row[0]] = float(row[1] or 0)
    
    total_nexus = sum(nexus.values())
    nexus_ratio = min(((nexus["a"] + nexus["b"]) * 1.3) / total_nexus, 1.0) if total_nexus > 0 else 1.0
    qualified_income = ip_revenues * nexus_ratio
    
    return IPBoxSummary(
        fiscal_year=fiscal_year, company_name=settings.COMPANY_NAME,
        company_nip=settings.COMPANY_NIP, ip_revenues=ip_revenues,
        nexus_a=nexus["a"], nexus_b=nexus["b"], nexus_c=nexus["c"], nexus_d=nexus["d"],
        nexus_ratio=nexus_ratio, qualified_income=qualified_income,
        tax_5_percent=qualified_income * 0.05
    )
