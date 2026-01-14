"""
Variable API Router - Integration with existing FastAPI app.

Provides endpoints for accessing variables with verification URLs.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from src.api.database import get_db

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["Variable API"])


class VariableResponse(BaseModel):
    """Response for a single variable"""
    name: str
    value: Any
    source: str
    path: str = ""
    fetched_at: datetime = Field(default_factory=datetime.now)
    verification_url: str = ""


class ProjectVariableResponse(BaseModel):
    """Response for project-level variable"""
    project_id: str
    variable: VariableResponse
    footnote: str = ""


class InvoiceDataResponse(BaseModel):
    """Response for invoice data"""
    invoice_id: str
    format: str
    data: Any
    document_id: Optional[str] = None
    ocr_confidence: Optional[float] = None


class NexusResponse(BaseModel):
    """Response for Nexus calculation"""
    project_id: str
    year: int
    a_direct: float = Field(description="Koszty B+R bezpośrednie")
    b_unrelated: float = Field(description="Koszty B+R od niepowiązanych")
    c_related: float = Field(description="Koszty B+R od powiązanych")
    d_ip: float = Field(description="Koszty zakupu gotowego IP")
    nexus: float = Field(description="Wskaźnik Nexus (0-1)")
    formula: str = "((a + b) × 1.3) / (a + b + c + d)"
    verification_urls: Dict[str, str] = Field(default_factory=dict)


def get_base_url(request: Request) -> str:
    """Get base URL from request"""
    return str(request.base_url).rstrip("/")


@router.get("/project/{project_id}/variable/{source_name}")
async def get_project_variable(
    project_id: str,
    source_name: str,
    path: Optional[str] = Query(None, description="Variable path within source"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> ProjectVariableResponse:
    """
    Get a variable for a project from a data source.
    
    URL format for document footnotes:
    /api/project/{project_id}/variable/{source_name}?path={field}
    
    Examples:
    - /api/project/uuid/variable/expenses_by_category?path=total_gross
    - /api/project/uuid/variable/nexus_calculation?path=nexus
    """
    base_url = get_base_url(request) if request else "http://localhost:81"
    
    # Map source names to queries
    source_queries = {
        "expenses_by_category": """
            SELECT 
                br_category as category,
                COUNT(*) as count,
                SUM(gross_amount) as total_gross,
                SUM(net_amount) as total_net,
                SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END) as qualified_amount
            FROM read_models.expenses
            WHERE project_id = :project_id
            GROUP BY br_category
        """,
        "expenses_summary": """
            SELECT 
                SUM(gross_amount) as total_gross,
                SUM(net_amount) as total_net,
                COUNT(*) as count
            FROM read_models.expenses
            WHERE project_id = :project_id
        """,
        "nexus_calculation": """
            WITH expense_categories AS (
                SELECT 
                    SUM(CASE WHEN br_category IN ('personnel_employment', 'personnel_civil', 'materials', 'equipment') 
                        THEN gross_amount ELSE 0 END) as a_direct,
                    SUM(CASE WHEN br_category = 'external_services'
                        THEN gross_amount ELSE 0 END) as b_unrelated,
                    SUM(0) as c_related,
                    SUM(CASE WHEN br_category = 'ip_purchase' THEN gross_amount ELSE 0 END) as d_ip
                FROM read_models.expenses
                WHERE project_id = :project_id AND br_qualified = true
            )
            SELECT 
                COALESCE(a_direct, 0) as a_direct, 
                COALESCE(b_unrelated, 0) as b_unrelated, 
                COALESCE(c_related, 0) as c_related, 
                COALESCE(d_ip, 0) as d_ip,
                CASE 
                    WHEN COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0) + COALESCE(c_related, 0) + COALESCE(d_ip, 0) = 0 THEN 1
                    ELSE LEAST(1, ((COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0)) * 1.3) / 
                         NULLIF(COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0) + COALESCE(c_related, 0) + COALESCE(d_ip, 0), 0))
                END as nexus
            FROM expense_categories
        """,
        "timesheet_summary": """
            SELECT 
                SUM(hours) as total_hours,
                COUNT(DISTINCT worker_id) as worker_count
            FROM read_models.timesheet_entries
            WHERE project_id = :project_id
        """,
        "revenues": """
            SELECT 
                SUM(gross_amount) as total_revenue,
                COUNT(*) as count
            FROM read_models.revenues
            WHERE project_id = :project_id
        """,
        "project_info": """
            SELECT id, name, description, start_date, end_date, status, fiscal_year
            FROM read_models.projects
            WHERE id = :project_id
            LIMIT 1
        """,
    }
    
    query = source_queries.get(source_name)
    if not query:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_name}")
    
    try:
        result = await db.execute(text(query), {"project_id": project_id})
        rows = result.fetchall()
        columns = result.keys()
        
        if not rows:
            value = None
        elif len(rows) == 1:
            row_dict = dict(zip(columns, rows[0]))
            value = row_dict.get(path) if path else row_dict
        else:
            data = [dict(zip(columns, row)) for row in rows]
            if path:
                value = sum(row.get(path, 0) or 0 for row in data)
            else:
                value = data
        
        verification_url = f"{base_url}/api/project/{project_id}/variable/{source_name}"
        if path:
            verification_url += f"?path={path}"
        
        return ProjectVariableResponse(
            project_id=project_id,
            variable=VariableResponse(
                name=path or source_name,
                value=value,
                source=source_name,
                path=path or "",
                verification_url=verification_url,
            ),
            footnote=f"[{path or source_name}]({verification_url})",
        )
    except Exception as e:
        logger.error("variable_fetch_error", error=str(e), source=source_name)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/variable/{source_name}/{path:path}")
async def get_project_variable_with_path(
    project_id: str,
    source_name: str,
    path: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> ProjectVariableResponse:
    """
    Get a specific variable field from a data source.
    
    URL: /api/project/{project_id}/variable/{source_name}/{field_path}
    """
    return await get_project_variable(
        project_id=project_id,
        source_name=source_name,
        path=path,
        request=request,
        db=db,
    )


@router.get("/invoice/{invoice_id}/variable/{variable_name}")
async def get_invoice_variable(
    invoice_id: str,
    variable_name: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> VariableResponse:
    """
    Get a variable from an invoice.
    
    URL: /api/invoice/{invoice_id}/variable/{variable_name}
    """
    base_url = get_base_url(request) if request else "http://localhost:81"
    
    query = """
        SELECT e.*, d.ocr_text, d.id as document_id
        FROM read_models.expenses e
        LEFT JOIN read_models.documents d ON e.document_id = d.id
        WHERE e.id = :invoice_id OR e.invoice_number = :invoice_id
        LIMIT 1
    """
    
    try:
        result = await db.execute(text(query), {"invoice_id": invoice_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_id}")
        
        row_dict = dict(zip(result.keys(), row))
        value = row_dict.get(variable_name)
        
        return VariableResponse(
            name=variable_name,
            value=value,
            source="invoice",
            path=variable_name,
            verification_url=f"{base_url}/api/invoice/{invoice_id}/variable/{variable_name}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("invoice_variable_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoice/{invoice_id}")
async def get_invoice_data(
    invoice_id: str,
    format: str = Query("json", description="Output format: json, plain_text, ocr"),
    db: AsyncSession = Depends(get_db),
) -> InvoiceDataResponse:
    """
    Get full invoice data.
    
    URL: /api/invoice/{invoice_id}?format=json|plain_text|ocr
    """
    query = """
        SELECT e.*, d.ocr_text, d.ocr_confidence, d.extracted_data, d.id as document_id
        FROM read_models.expenses e
        LEFT JOIN read_models.documents d ON e.document_id = d.id
        WHERE e.id = :invoice_id OR e.invoice_number = :invoice_id
        LIMIT 1
    """
    
    try:
        result = await db.execute(text(query), {"invoice_id": invoice_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_id}")
        
        row_dict = dict(zip(result.keys(), row))
        
        if format == "ocr":
            data = row_dict.get("ocr_text", "")
        elif format == "plain_text":
            data = f"""FAKTURA: {row_dict.get('invoice_number', 'N/A')}
Data: {row_dict.get('invoice_date', 'N/A')}
Sprzedawca: {row_dict.get('vendor_name', 'N/A')}
NIP: {row_dict.get('vendor_nip', 'N/A')}
Kwota brutto: {row_dict.get('gross_amount', 0)} PLN
Kwota netto: {row_dict.get('net_amount', 0)} PLN
Kategoria B+R: {row_dict.get('br_category', 'N/A')}
Kwalifikowany: {'Tak' if row_dict.get('br_qualified') else 'Nie'}"""
        else:
            data = {k: v for k, v in row_dict.items() if k != "ocr_text"}
        
        return InvoiceDataResponse(
            invoice_id=invoice_id,
            format=format,
            data=data,
            document_id=row_dict.get("document_id"),
            ocr_confidence=row_dict.get("ocr_confidence"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("invoice_data_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/nexus")
async def get_nexus_calculation(
    project_id: str,
    year: Optional[int] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> NexusResponse:
    """
    Get Nexus indicator calculation for IP Box.
    
    URL: /api/project/{project_id}/nexus?year=2025
    
    Returns all components (a, b, c, d), calculated Nexus value,
    and verification URLs for each component.
    """
    base_url = get_base_url(request) if request else "http://localhost:81"
    
    query = """
        WITH expense_categories AS (
            SELECT 
                SUM(CASE WHEN br_category IN ('personnel_employment', 'personnel_civil', 'materials', 'equipment') 
                    THEN gross_amount ELSE 0 END) as a_direct,
                SUM(CASE WHEN br_category = 'external_services'
                    THEN gross_amount ELSE 0 END) as b_unrelated,
                SUM(0) as c_related,
                SUM(CASE WHEN br_category = 'ip_purchase' THEN gross_amount ELSE 0 END) as d_ip
            FROM read_models.expenses
            WHERE project_id = :project_id AND br_qualified = true
        )
        SELECT 
            COALESCE(a_direct, 0) as a_direct, 
            COALESCE(b_unrelated, 0) as b_unrelated, 
            COALESCE(c_related, 0) as c_related, 
            COALESCE(d_ip, 0) as d_ip,
            CASE 
                WHEN COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0) + COALESCE(c_related, 0) + COALESCE(d_ip, 0) = 0 THEN 1
                ELSE LEAST(1, ((COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0)) * 1.3) / 
                     NULLIF(COALESCE(a_direct, 0) + COALESCE(b_unrelated, 0) + COALESCE(c_related, 0) + COALESCE(d_ip, 0), 0))
            END as nexus
        FROM expense_categories
    """
    
    try:
        result = await db.execute(text(query), {"project_id": project_id})
        row = result.fetchone()
        
        if not row:
            return NexusResponse(
                project_id=project_id,
                year=year or 2025,
                a_direct=0,
                b_unrelated=0,
                c_related=0,
                d_ip=0,
                nexus=1.0,
            )
        
        row_dict = dict(zip(result.keys(), row))
        
        return NexusResponse(
            project_id=project_id,
            year=year or 2025,
            a_direct=float(row_dict.get("a_direct", 0) or 0),
            b_unrelated=float(row_dict.get("b_unrelated", 0) or 0),
            c_related=float(row_dict.get("c_related", 0) or 0),
            d_ip=float(row_dict.get("d_ip", 0) or 0),
            nexus=float(row_dict.get("nexus", 1) or 1),
            verification_urls={
                "a_direct": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/a_direct",
                "b_unrelated": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/b_unrelated",
                "c_related": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/c_related",
                "d_ip": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/d_ip",
                "nexus": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/nexus",
            },
        )
    except Exception as e:
        logger.error("nexus_calculation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variables")
async def list_available_variables(request: Request = None) -> Dict[str, Any]:
    """
    List all available variable sources.
    
    URL: /api/variables
    """
    base_url = get_base_url(request) if request else "http://localhost:81"
    
    sources = [
        {
            "name": "project_info",
            "description": "Informacje o projekcie B+R",
            "fields": ["id", "name", "description", "start_date", "end_date", "status", "fiscal_year"],
            "url_pattern": f"{base_url}/api/project/{{project_id}}/variable/project_info/{{field}}",
        },
        {
            "name": "expenses_by_category",
            "description": "Wydatki pogrupowane według kategorii B+R",
            "fields": ["category", "count", "total_gross", "total_net", "qualified_amount"],
            "url_pattern": f"{base_url}/api/project/{{project_id}}/variable/expenses_by_category/{{field}}",
        },
        {
            "name": "expenses_summary",
            "description": "Podsumowanie wszystkich wydatków",
            "fields": ["total_gross", "total_net", "count"],
            "url_pattern": f"{base_url}/api/project/{{project_id}}/variable/expenses_summary/{{field}}",
        },
        {
            "name": "nexus_calculation",
            "description": "Obliczenie wskaźnika Nexus dla IP Box",
            "fields": ["a_direct", "b_unrelated", "c_related", "d_ip", "nexus"],
            "url_pattern": f"{base_url}/api/project/{{project_id}}/variable/nexus_calculation/{{field}}",
        },
        {
            "name": "timesheet_summary",
            "description": "Podsumowanie godzin pracy",
            "fields": ["total_hours", "worker_count"],
            "url_pattern": f"{base_url}/api/project/{{project_id}}/variable/timesheet_summary/{{field}}",
        },
        {
            "name": "revenues",
            "description": "Przychody z projektu (IP Box)",
            "fields": ["total_revenue", "count"],
            "url_pattern": f"{base_url}/api/project/{{project_id}}/variable/revenues/{{field}}",
        },
        {
            "name": "invoice",
            "description": "Dane pojedynczej faktury",
            "fields": ["gross_amount", "net_amount", "vendor_name", "vendor_nip", "invoice_date", "br_category"],
            "url_pattern": f"{base_url}/api/invoice/{{invoice_id}}/variable/{{field}}",
        },
    ]
    
    return {
        "sources": sources,
        "total": len(sources),
        "base_url": base_url,
        "usage": {
            "project_variable": f"{base_url}/api/project/{{project_id}}/variable/{{source}}/{{field}}",
            "invoice_variable": f"{base_url}/api/invoice/{{invoice_id}}/variable/{{field}}",
            "invoice_data": f"{base_url}/api/invoice/{{invoice_id}}?format=json|ocr|plain_text",
            "nexus": f"{base_url}/api/project/{{project_id}}/nexus",
        },
    }
