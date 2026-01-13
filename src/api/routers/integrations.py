"""
Integrations API Router - Manage accounting and cloud storage integrations
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from src.integrations.config.database import (
    get_config_db, ConfigDatabase, IntegrationProvider, IntegrationType
)
from src.integrations.factory import (
    get_client_from_config, verify_integration, IntegrationManager
)

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class IntegrationCreate(BaseModel):
    """Create integration request"""
    id: str = Field(..., min_length=1, max_length=50, description="Unique integration ID")
    provider: str = Field(..., description="Provider name (ifirma, fakturownia, nextcloud, etc.)")
    integration_type: str = Field(..., description="Type: accounting or cloud_storage")
    
    credentials: Dict[str, Any] = Field(..., description="API credentials (will be encrypted)")
    settings: Optional[Dict[str, Any]] = Field(default={}, description="Additional settings")
    
    base_url: Optional[str] = Field(default=None, description="Base URL for API (if applicable)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "my-ifirma",
                "provider": "ifirma",
                "integration_type": "accounting",
                "credentials": {
                    "api_key": "your-api-key",
                    "username": "user@example.com",
                    "company_name": "My Company"
                },
                "settings": {}
            }
        }


class IntegrationUpdate(BaseModel):
    """Update integration request"""
    credentials: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None


class IntegrationResponse(BaseModel):
    """Integration response"""
    id: str
    provider: str
    integration_type: str
    is_active: bool
    is_verified: bool
    last_sync_at: Optional[datetime]
    settings: Dict[str, Any]
    base_url: Optional[str] = None
    # Note: credentials are never returned


class SyncRequest(BaseModel):
    """Invoice sync request"""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    project_id: Optional[str] = None


class UploadReportRequest(BaseModel):
    """Report upload request"""
    report_name: str
    year: Optional[int] = None
    month: Optional[int] = None


class SyncLogResponse(BaseModel):
    """Sync log response"""
    id: int
    integration_id: str
    sync_type: str
    status: str
    items_processed: int
    items_failed: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


# =============================================================================
# Dependencies
# =============================================================================

def get_db() -> ConfigDatabase:
    return get_config_db()


def get_manager(db: ConfigDatabase = Depends(get_db)) -> IntegrationManager:
    return IntegrationManager(db)


# =============================================================================
# Endpoints - Integration Management
# =============================================================================

@router.get("/providers")
async def list_providers():
    """List available integration providers"""
    return {
        "accounting": [
            {"id": "ifirma", "name": "iFirma", "description": "Polish accounting software"},
            {"id": "fakturownia", "name": "Fakturownia", "description": "Polish invoicing platform"},
            {"id": "wfirma", "name": "wFirma", "description": "Polish accounting software"},
            {"id": "infakt", "name": "InFakt", "description": "Polish invoicing & accounting"},
        ],
        "cloud_storage": [
            {"id": "nextcloud", "name": "Nextcloud", "description": "Self-hosted cloud storage"},
            {"id": "google_drive", "name": "Google Drive", "description": "Google cloud storage"},
            {"id": "aws_s3", "name": "AWS S3", "description": "Amazon S3 storage"},
            {"id": "minio", "name": "MinIO", "description": "S3-compatible object storage"},
        ]
    }


@router.post("/", response_model=IntegrationResponse)
async def create_integration(
    integration: IntegrationCreate,
    db: ConfigDatabase = Depends(get_db)
):
    """Create a new integration"""
    try:
        provider = IntegrationProvider(integration.provider)
        int_type = IntegrationType(integration.integration_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid provider or type: {e}")
    
    # Check if already exists
    existing = db.get_integration(integration.id)
    if existing:
        raise HTTPException(status_code=409, detail="Integration with this ID already exists")
    
    # Save integration
    db.save_integration(
        integration_id=integration.id,
        provider=provider,
        integration_type=int_type,
        credentials=integration.credentials,
        settings=integration.settings,
        base_url=integration.base_url
    )
    
    # Get and return (without credentials)
    config = db.get_integration(integration.id)
    
    return IntegrationResponse(
        id=config["id"],
        provider=config["provider"],
        integration_type=config["integration_type"],
        is_active=config["is_active"],
        is_verified=config["is_verified"],
        last_sync_at=config["last_sync_at"],
        settings=config["settings"],
        base_url=config.get("base_url")
    )


@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    integration_type: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    db: ConfigDatabase = Depends(get_db)
):
    """List all integrations"""
    int_type = IntegrationType(integration_type) if integration_type else None
    
    integrations = db.list_integrations(
        integration_type=int_type,
        active_only=active_only
    )
    
    return [
        IntegrationResponse(
            id=i["id"],
            provider=i["provider"],
            integration_type=i["integration_type"],
            is_active=i["is_active"],
            is_verified=i["is_verified"],
            last_sync_at=i["last_sync_at"],
            settings=i.get("settings", {})
        )
        for i in integrations
    ]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    db: ConfigDatabase = Depends(get_db)
):
    """Get integration details"""
    config = db.get_integration(integration_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return IntegrationResponse(
        id=config["id"],
        provider=config["provider"],
        integration_type=config["integration_type"],
        is_active=config["is_active"],
        is_verified=config["is_verified"],
        last_sync_at=config["last_sync_at"],
        settings=config["settings"],
        base_url=config.get("base_url")
    )


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: str,
    update: IntegrationUpdate,
    db: ConfigDatabase = Depends(get_db)
):
    """Update integration configuration"""
    existing = db.get_integration(integration_id)
    
    if not existing:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Update only provided fields
    db.save_integration(
        integration_id=integration_id,
        provider=IntegrationProvider(existing["provider"]),
        integration_type=IntegrationType(existing["integration_type"]),
        credentials=update.credentials if update.credentials else None,
        settings=update.settings if update.settings else None,
        base_url=update.base_url
    )
    
    return await get_integration(integration_id, db)


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    db: ConfigDatabase = Depends(get_db)
):
    """Delete integration"""
    if not db.delete_integration(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"status": "deleted", "id": integration_id}


@router.post("/{integration_id}/verify")
async def verify_integration_connection(
    integration_id: str,
    background_tasks: BackgroundTasks,
    db: ConfigDatabase = Depends(get_db)
):
    """Verify integration connection"""
    config = db.get_integration(integration_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Run verification
    is_valid = await verify_integration(integration_id)
    
    return {
        "integration_id": integration_id,
        "is_verified": is_valid,
        "message": "Connection successful" if is_valid else "Connection failed"
    }


# =============================================================================
# Endpoints - Sync Operations
# =============================================================================

@router.post("/{integration_id}/sync/invoices")
async def sync_invoices(
    integration_id: str,
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    manager: IntegrationManager = Depends(get_manager)
):
    """Sync invoices from accounting system to B+R database"""
    # Verify integration exists and is accounting type
    config = manager.config_db.get_integration(integration_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if config["integration_type"] != "accounting":
        raise HTTPException(status_code=400, detail="Not an accounting integration")
    
    # Run sync (could be background task for large syncs)
    result = await manager.sync_invoices_from_accounting(
        integration_id=integration_id,
        date_from=sync_request.date_from,
        date_to=sync_request.date_to,
        project_id=sync_request.project_id
    )
    
    return result


@router.post("/{integration_id}/upload/report")
async def upload_report_to_cloud(
    integration_id: str,
    upload_request: UploadReportRequest,
    manager: IntegrationManager = Depends(get_manager)
):
    """Upload generated report to cloud storage"""
    # Verify integration exists and is cloud storage type
    config = manager.config_db.get_integration(integration_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if config["integration_type"] != "cloud_storage":
        raise HTTPException(status_code=400, detail="Not a cloud storage integration")
    
    # Get report content from reports API
    # This would typically fetch the report from the database or generate it
    from datetime import datetime
    year = upload_request.year or datetime.now().year
    month = upload_request.month or datetime.now().month
    
    # Placeholder - in real implementation, generate or fetch report
    report_content = f"B+R Report {year}-{month:02d}".encode()
    
    result = await manager.upload_report_to_cloud(
        integration_id=integration_id,
        report_content=report_content,
        report_name=upload_request.report_name,
        year=year,
        month=month
    )
    
    return result


# =============================================================================
# Endpoints - Sync Logs
# =============================================================================

@router.get("/{integration_id}/logs", response_model=List[SyncLogResponse])
async def get_sync_logs(
    integration_id: str,
    limit: int = Query(default=50, le=100),
    db: ConfigDatabase = Depends(get_db)
):
    """Get sync logs for integration"""
    logs = db.get_sync_logs(integration_id=integration_id, limit=limit)
    
    return [
        SyncLogResponse(
            id=log["id"],
            integration_id=log["integration_id"],
            sync_type=log["sync_type"],
            status=log["status"],
            items_processed=log["items_processed"],
            items_failed=log["items_failed"],
            error_message=log["error_message"],
            started_at=log["started_at"],
            completed_at=log["completed_at"]
        )
        for log in logs
    ]


# =============================================================================
# Endpoints - Quick Actions
# =============================================================================

@router.post("/actions/sync-all-invoices")
async def sync_all_invoices(
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    manager: IntegrationManager = Depends(get_manager)
):
    """Sync invoices from all active accounting integrations"""
    integrations = manager.get_active_accounting_integrations()
    
    results = {}
    for integration in integrations:
        result = await manager.sync_invoices_from_accounting(
            integration_id=integration["id"],
            date_from=sync_request.date_from,
            date_to=sync_request.date_to,
            project_id=sync_request.project_id
        )
        results[integration["id"]] = result
    
    return {
        "integrations_synced": len(integrations),
        "results": results
    }


@router.post("/actions/upload-monthly-reports")
async def upload_monthly_reports(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    manager: IntegrationManager = Depends(get_manager)
):
    """Upload monthly reports to all active cloud storage integrations"""
    integrations = manager.get_active_cloud_integrations()
    
    if not integrations:
        raise HTTPException(status_code=404, detail="No active cloud storage integrations")
    
    # Generate report (placeholder - would call actual report generation)
    report_name = f"raport-br-{year}-{month:02d}.pdf"
    report_content = f"B+R Monthly Report for {year}-{month:02d}".encode()
    
    results = {}
    for integration in integrations:
        result = await manager.upload_report_to_cloud(
            integration_id=integration["id"],
            report_content=report_content,
            report_name=report_name,
            year=year,
            month=month
        )
        results[integration["id"]] = result
    
    return {
        "integrations_uploaded": len(integrations),
        "results": results
    }


# =============================================================================
# Endpoints - KSeF Integration (P3)
# =============================================================================

@router.post("/ksef/import")
async def import_ksef_invoices(
    nip: str = Query(..., description="NIP podatnika"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    invoice_type: str = Query(default="purchase", description="purchase or sales")
):
    """
    P3: Import invoices from KSeF (Polish Electronic Invoice System).
    
    Fetches invoices and returns them ready for expense creation.
    """
    from ..integrations.ksef_client import get_ksef_service
    
    service = get_ksef_service(nip)
    
    try:
        if invoice_type == "purchase":
            result = await service.import_purchase_invoices(date_from, date_to)
        else:
            # Sales invoices would go to revenues
            result = await service.client.fetch_invoices(date_from, date_to, "sales")
            result = {"invoices": [inv.to_dict() for inv in result], "imported": len(result)}
        
        logger.info("KSeF import completed", 
                   nip=nip, 
                   imported=result.get("imported", 0))
        
        return result
        
    except Exception as e:
        logger.error("KSeF import failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"KSeF import failed: {str(e)}")


# =============================================================================
# Endpoints - JPK Export (P3)
# =============================================================================

@router.post("/jpk/generate")
async def generate_jpk_v7m(
    nip: str = Query(..., description="NIP podatnika"),
    full_name: str = Query(..., description="Pełna nazwa podatnika"),
    email: str = Query(..., description="Email kontaktowy"),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    purpose: int = Query(default=0, description="0=oryginał, 1=korekta"),
    db = Depends(get_db)
):
    """
    P3: Generate JPK_V7M XML file for Polish tax authority.
    
    Exports all expenses for given month in JPK format.
    """
    from ..integrations.jpk_export import JPKExporter, JPKHeader, create_jpk_from_expenses
    from sqlalchemy import text
    from src.infra.database import get_db as get_main_db
    
    # Get expenses for the month
    async for session in get_main_db():
        result = await session.execute(
            text("""
                SELECT invoice_number, invoice_date, vendor_name, vendor_nip,
                       net_amount, vat_amount, gross_amount
                FROM read_models.expenses
                WHERE EXTRACT(YEAR FROM invoice_date) = :year
                  AND EXTRACT(MONTH FROM invoice_date) = :month
                ORDER BY invoice_date
            """),
            {"year": year, "month": month}
        )
        rows = result.fetchall()
        
        expenses = [
            {
                "invoice_number": row[0],
                "invoice_date": row[1],
                "vendor_name": row[2],
                "vendor_nip": row[3],
                "net_amount": float(row[4] or 0),
                "vat_amount": float(row[5] or 0),
                "gross_amount": float(row[6] or 0)
            }
            for row in rows
        ]
        break
    
    # Create JPK
    header = JPKHeader(
        nip=nip,
        full_name=full_name,
        email=email,
        year=year,
        month=month,
        purpose=purpose
    )
    
    exporter = create_jpk_from_expenses(expenses, header)
    
    # Validate
    errors = exporter.validate()
    if errors:
        return {
            "status": "validation_failed",
            "errors": errors,
            "expense_count": len(expenses)
        }
    
    # Generate XML
    xml_content = exporter.generate_xml()
    
    logger.info("JPK generated", 
               year=year, 
               month=month, 
               expenses=len(expenses))
    
    return {
        "status": "success",
        "filename": f"JPK_V7M_{nip}_{year}_{month:02d}.xml",
        "expense_count": len(expenses),
        "xml_preview": xml_content[:2000] if len(xml_content) > 2000 else xml_content,
        "xml_length": len(xml_content)
    }


@router.get("/jpk/download")
async def download_jpk_v7m(
    nip: str = Query(...),
    full_name: str = Query(...),
    email: str = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12)
):
    """
    Download JPK_V7M as XML file.
    """
    from fastapi.responses import Response
    
    # Generate (reuse logic from above)
    result = await generate_jpk_v7m(nip, full_name, email, year, month, 0, None)
    
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("errors", ["Unknown error"]))
    
    # Return as downloadable file
    from ..integrations.jpk_export import JPKExporter, JPKHeader, create_jpk_from_expenses
    
    header = JPKHeader(nip=nip, full_name=full_name, email=email, year=year, month=month)
    exporter = create_jpk_from_expenses([], header)  # Would need actual expenses
    xml_content = exporter.generate_xml()
    
    return Response(
        content=xml_content.encode("utf-8"),
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="JPK_V7M_{nip}_{year}_{month:02d}.xml"'
        }
    )
