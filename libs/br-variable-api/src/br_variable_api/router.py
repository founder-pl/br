"""
FastAPI router for Variable API endpoints.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .auth import AuthContext, MultiAuth, get_current_auth
from .models import (
    VariableResponse,
    ProjectVariableResponse,
    InvoiceVariableResponse,
    InvoiceDataResponse,
    NexusCalculationResponse,
    VariableListResponse,
)

logger = structlog.get_logger()


def create_variable_router(
    get_db: Any,
    data_registry: Any,
    auth: Optional[MultiAuth] = None,
    prefix: str = "/api",
) -> APIRouter:
    """
    Create FastAPI router for Variable API.
    
    Args:
        get_db: Dependency for database session
        data_registry: DataSourceRegistry instance
        auth: Optional custom auth provider
        prefix: URL prefix for routes
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix=prefix, tags=["Variables API"])
    auth_dep = auth or get_current_auth
    
    @router.get("/project/{project_id}/variable/{source_name}")
    async def get_project_variable(
        project_id: str,
        source_name: str,
        path: Optional[str] = Query(None, description="Variable path within source"),
        request: Request = None,
        auth_ctx: AuthContext = Depends(auth_dep),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectVariableResponse:
        """
        Get a variable for a project from a data source.
        
        URL: /api/project/{project_id}/variable/{source_name}?path=field_name
        
        Examples:
        - /api/project/uuid/variable/expenses_by_category?path=total_gross
        - /api/project/uuid/variable/nexus_calculation?path=nexus
        """
        if not auth_ctx.has_scope("read"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do odczytu")
        
        # Fetch data from source
        result = await data_registry.fetch(
            source_name,
            {"project_id": project_id},
            db=db
        )
        
        if result.error:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Extract specific variable if path provided
        value = result.data
        if path and result.data:
            if isinstance(result.data, list) and len(result.data) > 0:
                value = result.data[0].get(path)
            elif isinstance(result.data, dict):
                value = result.data.get(path)
        
        base_url = str(request.base_url).rstrip("/") if request else "http://localhost:81"
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
            ),
            verification_url=verification_url,
        )
    
    @router.get("/project/{project_id}/variable/{source_name}/{path:path}")
    async def get_project_variable_with_path(
        project_id: str,
        source_name: str,
        path: str,
        request: Request = None,
        auth_ctx: AuthContext = Depends(auth_dep),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectVariableResponse:
        """
        Get a specific variable field from a data source.
        
        URL: /api/project/{project_id}/variable/{source_name}/{field_path}
        
        Example:
        - /api/project/uuid/variable/nexus_calculation/nexus
        - /api/project/uuid/variable/expenses_by_category/total_gross
        """
        if not auth_ctx.has_scope("read"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do odczytu")
        
        result = await data_registry.fetch(
            source_name,
            {"project_id": project_id},
            db=db
        )
        
        if result.error:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Navigate path
        value = result.data
        for part in path.split("/"):
            if isinstance(value, list) and len(value) > 0:
                value = value[0].get(part) if isinstance(value[0], dict) else None
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        
        base_url = str(request.base_url).rstrip("/") if request else "http://localhost:81"
        
        return ProjectVariableResponse(
            project_id=project_id,
            variable=VariableResponse(
                name=path.split("/")[-1],
                value=value,
                source=source_name,
                path=path,
            ),
            verification_url=f"{base_url}/api/project/{project_id}/variable/{source_name}/{path}",
        )
    
    @router.get("/invoice/{invoice_id}/variable/{variable_name}")
    async def get_invoice_variable(
        invoice_id: str,
        variable_name: str,
        format: str = Query("json", description="Output format: json, plain_text, ocr"),
        auth_ctx: AuthContext = Depends(auth_dep),
        db: AsyncSession = Depends(get_db),
    ) -> InvoiceVariableResponse:
        """
        Get a variable from an invoice.
        
        URL: /api/invoice/{invoice_id}/variable/{variable_name}
        
        Examples:
        - /api/invoice/inv-123/variable/gross_amount
        - /api/invoice/inv-123/variable/vendor_nip
        """
        if not auth_ctx.has_scope("read"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do odczytu")
        
        # Query invoice from expenses table
        from sqlalchemy import text
        query = """
            SELECT e.*, d.ocr_text, d.id as document_id
            FROM read_models.expenses e
            LEFT JOIN read_models.documents d ON e.document_id = d.id
            WHERE e.id = :invoice_id OR e.invoice_number = :invoice_id
            LIMIT 1
        """
        
        result = await db.execute(text(query), {"invoice_id": invoice_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Faktura nie znaleziona: {invoice_id}")
        
        row_dict = dict(zip(result.keys(), row))
        value = row_dict.get(variable_name)
        
        return InvoiceVariableResponse(
            invoice_id=invoice_id,
            variable=VariableResponse(
                name=variable_name,
                value=value,
                source="invoice",
                path=variable_name,
            ),
            ocr_source=row_dict.get("ocr_text", "")[:500] if format == "ocr" else None,
            document_id=row_dict.get("document_id"),
        )
    
    @router.get("/invoice/{invoice_id}")
    async def get_invoice_data(
        invoice_id: str,
        format: str = Query("json", description="Output format: json, plain_text, ocr"),
        auth_ctx: AuthContext = Depends(auth_dep),
        db: AsyncSession = Depends(get_db),
    ) -> InvoiceDataResponse:
        """
        Get full invoice data.
        
        URL: /api/invoice/{invoice_id}?format=json|plain_text|ocr
        
        Formats:
        - json: Structured invoice data
        - plain_text: Invoice as plain text
        - ocr: Raw OCR text
        """
        if not auth_ctx.has_scope("read"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do odczytu")
        
        from sqlalchemy import text
        query = """
            SELECT e.*, d.ocr_text, d.ocr_confidence, d.extracted_data, d.id as document_id
            FROM read_models.expenses e
            LEFT JOIN read_models.documents d ON e.document_id = d.id
            WHERE e.id = :invoice_id OR e.invoice_number = :invoice_id
            LIMIT 1
        """
        
        result = await db.execute(text(query), {"invoice_id": invoice_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Faktura nie znaleziona: {invoice_id}")
        
        row_dict = dict(zip(result.keys(), row))
        
        if format == "ocr":
            data = row_dict.get("ocr_text", "")
        elif format == "plain_text":
            data = _format_invoice_plain_text(row_dict)
        else:
            # JSON format - exclude large OCR text
            data = {k: v for k, v in row_dict.items() if k != "ocr_text"}
        
        return InvoiceDataResponse(
            invoice_id=invoice_id,
            format=format,
            data=data,
            document_id=row_dict.get("document_id"),
            ocr_confidence=row_dict.get("ocr_confidence"),
        )
    
    @router.get("/project/{project_id}/nexus")
    async def get_nexus_calculation(
        project_id: str,
        year: Optional[int] = None,
        request: Request = None,
        auth_ctx: AuthContext = Depends(auth_dep),
        db: AsyncSession = Depends(get_db),
    ) -> NexusCalculationResponse:
        """
        Get Nexus indicator calculation for IP Box.
        
        URL: /api/project/{project_id}/nexus?year=2025
        
        Returns all components and verification URLs.
        """
        if not auth_ctx.has_scope("read"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do odczytu")
        
        result = await data_registry.fetch(
            "nexus_calculation",
            {"project_id": project_id},
            db=db
        )
        
        if result.error:
            raise HTTPException(status_code=500, detail=result.error)
        
        if not result.data or len(result.data) == 0:
            # Return default values
            return NexusCalculationResponse(
                project_id=project_id,
                year=year or 2025,
                a_direct=0,
                b_unrelated=0,
                c_related=0,
                d_ip=0,
                nexus=1.0,
            )
        
        data = result.data[0]
        base_url = str(request.base_url).rstrip("/") if request else "http://localhost:81"
        
        return NexusCalculationResponse(
            project_id=project_id,
            year=year or 2025,
            a_direct=float(data.get("a_direct", 0)),
            b_unrelated=float(data.get("b_unrelated", 0)),
            c_related=float(data.get("c_related", 0)),
            d_ip=float(data.get("d_ip", 0)),
            nexus=float(data.get("nexus", 1)),
            verification_urls={
                "a_direct": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/a_direct",
                "b_unrelated": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/b_unrelated",
                "c_related": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/c_related",
                "d_ip": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/d_ip",
                "nexus": f"{base_url}/api/project/{project_id}/variable/nexus_calculation/nexus",
            }
        )
    
    @router.get("/variables")
    async def list_available_variables(
        request: Request = None,
        auth_ctx: AuthContext = Depends(auth_dep),
    ) -> VariableListResponse:
        """
        List all available variable sources.
        
        URL: /api/variables
        """
        sources = data_registry.list_sources()
        base_url = str(request.base_url).rstrip("/") if request else "http://localhost:81"
        
        return VariableListResponse(
            variables=sources,
            total=len(sources),
            base_url=base_url,
        )
    
    return router


def _format_invoice_plain_text(data: dict) -> str:
    """Format invoice data as plain text"""
    lines = [
        f"FAKTURA: {data.get('invoice_number', 'N/A')}",
        f"Data: {data.get('invoice_date', 'N/A')}",
        f"Sprzedawca: {data.get('vendor_name', 'N/A')}",
        f"NIP: {data.get('vendor_nip', 'N/A')}",
        f"Kwota brutto: {data.get('gross_amount', 0)} PLN",
        f"Kwota netto: {data.get('net_amount', 0)} PLN",
        f"Kategoria B+R: {data.get('br_category', 'N/A')}",
        f"Kwalifikowany: {'Tak' if data.get('br_qualified') else 'Nie'}",
    ]
    return "\n".join(lines)
