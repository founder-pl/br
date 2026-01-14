"""
Expenses Revenues - Revenue (sales invoice) management
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db

logger = structlog.get_logger()
router = APIRouter()


@router.get("/revenues/")
async def list_revenues(
    project_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """List revenues (sales invoices) with optional project filter."""
    query = """
        SELECT r.id, r.project_id, r.document_id, r.invoice_number, r.invoice_date,
               r.client_name, r.client_nip, r.net_amount, r.vat_amount, r.gross_amount,
               r.currency, r.ip_qualified, r.ip_type, r.ip_description,
               r.created_at, p.name as project_name
        FROM read_models.revenues r
        LEFT JOIN read_models.projects p ON r.project_id = p.id
        WHERE 1=1
    """
    params = {}
    
    if project_id:
        query += " AND r.project_id = :project_id"
        params["project_id"] = project_id
    
    query += " ORDER BY r.invoice_date DESC"
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [
        {
            "id": str(r[0]),
            "project_id": str(r[1]) if r[1] else None,
            "document_id": str(r[2]) if r[2] else None,
            "invoice_number": r[3],
            "invoice_date": str(r[4]) if r[4] else None,
            "client_name": r[5],
            "client_nip": r[6],
            "net_amount": float(r[7] or 0),
            "vat_amount": float(r[8] or 0),
            "gross_amount": float(r[9] or 0),
            "currency": r[10] or "PLN",
            "ip_qualified": r[11] or False,
            "ip_category": r[12],
            "ip_description": r[13],
            "created_at": r[14].isoformat() if r[14] else None,
            "project_name": r[15],
            "type": "revenue"
        }
        for r in rows
    ]


@router.post("/revenues/")
async def create_revenue(
    revenue: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new revenue (sales invoice) from document."""
    revenue_id = str(uuid.uuid4())
    
    await db.execute(
        text("""
            INSERT INTO read_models.revenues (
                id, project_id, document_id, invoice_number, invoice_date,
                client_name, client_nip, net_amount, vat_amount, gross_amount,
                currency, ip_qualified, ip_type, ip_description
            ) VALUES (
                :id, :project_id, :document_id, :invoice_number, :invoice_date,
                :client_name, :client_nip, :net_amount, :vat_amount, :gross_amount,
                :currency, :ip_qualified, :ip_type, :ip_description
            )
        """),
        {
            "id": revenue_id,
            "project_id": revenue.get("project_id"),
            "document_id": revenue.get("document_id"),
            "invoice_number": revenue.get("invoice_number"),
            "invoice_date": revenue.get("invoice_date"),
            "client_name": revenue.get("client_name"),
            "client_nip": revenue.get("client_nip"),
            "net_amount": revenue.get("net_amount", 0),
            "vat_amount": revenue.get("vat_amount", 0),
            "gross_amount": revenue.get("gross_amount", 0),
            "currency": revenue.get("currency", "PLN"),
            "ip_qualified": revenue.get("ip_qualified", False),
            "ip_type": revenue.get("ip_type"),
            "ip_description": revenue.get("description")
        }
    )
    await db.commit()
    
    logger.info("Revenue created", revenue_id=revenue_id)
    return {"status": "created", "revenue_id": revenue_id}


@router.put("/revenues/{revenue_id}/classify")
async def classify_revenue(
    revenue_id: str,
    classification: dict,
    db: AsyncSession = Depends(get_db)
):
    """Classify a revenue for IP Box purposes."""
    result = await db.execute(
        text("SELECT * FROM read_models.revenues WHERE id = :id"),
        {"id": revenue_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Revenue not found")
    
    ip_qualified = classification.get("ip_qualified", False)
    ip_type = classification.get("ip_type") or classification.get("ip_category")
    ip_description = classification.get("ip_description")
    
    await db.execute(
        text("""
            UPDATE read_models.revenues SET
                ip_qualified = :ip_qualified,
                ip_type = :ip_type,
                ip_description = COALESCE(:ip_description, ip_description),
                updated_at = NOW()
            WHERE id = :id
        """),
        {
            "id": revenue_id,
            "ip_qualified": ip_qualified,
            "ip_type": ip_type,
            "ip_description": ip_description
        }
    )
    
    # Record event in event store (CQRS)
    from ...cqrs.events import EventStore, EventType, DomainEvent
    event_store = EventStore(db)
    await event_store.ensure_table_exists()
    
    event_type = EventType.REVENUE_IP_QUALIFIED if ip_qualified else EventType.REVENUE_IP_DISQUALIFIED
    event = DomainEvent(
        event_type=event_type,
        aggregate_id=revenue_id,
        aggregate_type="revenue",
        data={
            "ip_type": ip_type,
            "ip_qualified": ip_qualified,
            "ip_description": ip_description,
            "reason": "manual_classification"
        }
    )
    await event_store.append(event)
    
    result = await db.execute(
        text("""SELECT id, project_id, invoice_number, invoice_date, client_name, client_nip,
                       net_amount, vat_amount, gross_amount, currency, ip_qualified, ip_type,
                       ip_description, created_at
                FROM read_models.revenues WHERE id = :id"""),
        {"id": revenue_id}
    )
    r = result.fetchone()
    
    return {
        "id": str(r[0]),
        "project_id": str(r[1]) if r[1] else None,
        "invoice_number": r[2],
        "invoice_date": str(r[3]) if r[3] else None,
        "client_name": r[4],
        "client_nip": r[5],
        "net_amount": float(r[6] or 0),
        "vat_amount": float(r[7] or 0),
        "gross_amount": float(r[8] or 0),
        "currency": r[9] or "PLN",
        "ip_qualified": r[10] or False,
        "ip_category": r[11],
        "ip_description": r[12],
        "created_at": r[13].isoformat() if r[13] else None,
        "type": "revenue"
    }


@router.post("/invoices/{invoice_id}/reclassify")
async def reclassify_invoice(
    invoice_id: str,
    from_type: str = Query(..., description="Current type: expense or revenue"),
    to_type: str = Query(..., description="Target type: expense or revenue"),
    reason: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Reclassify an invoice from expense to revenue or vice versa."""
    from ...cqrs.commands import ReclassifyInvoiceCommand, ReclassifyInvoiceHandler
    
    command = ReclassifyInvoiceCommand(
        invoice_id=invoice_id,
        from_type=from_type,
        to_type=to_type,
        reason=reason,
    )
    
    handler = ReclassifyInvoiceHandler(db)
    result = await handler.handle(command)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Reclassification failed"))
    
    return result


@router.get("/invoices/{invoice_id}/history")
async def get_invoice_history(
    invoice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get event history for an invoice (expenses or revenues)."""
    from ...cqrs.queries import GetInvoiceHistoryQuery, InvoiceHistoryQueryHandler
    
    query = GetInvoiceHistoryQuery(invoice_id=invoice_id)
    handler = InvoiceHistoryQueryHandler(db)
    result = await handler.execute(query)
    
    return result
