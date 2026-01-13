"""
Query Handlers for CQRS pattern.

Queries represent read operations that don't change system state.
Optimized for specific read use cases.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .events import EventStore, get_event_store


@dataclass
class Query(ABC):
    """Base class for queries."""
    pass


@dataclass
class GetExpensesQuery(Query):
    """Query to get expenses with filters."""
    project_id: Optional[str] = None
    year: Optional[int] = None
    br_qualified: Optional[bool] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass
class GetRevenuesQuery(Query):
    """Query to get revenues with filters."""
    project_id: Optional[str] = None
    year: Optional[int] = None
    ip_qualified: Optional[bool] = None
    limit: int = 100
    offset: int = 0


@dataclass
class GetInvoiceHistoryQuery(Query):
    """Query to get event history for an invoice."""
    invoice_id: str
    include_related: bool = False


@dataclass 
class GetAllInvoicesQuery(Query):
    """Query to get all invoices (expenses + revenues) for unified view."""
    project_id: Optional[str] = None
    year: Optional[int] = None
    invoice_type: Optional[str] = None  # 'expense', 'revenue', 'all'
    limit: int = 100
    offset: int = 0


class QueryHandler(ABC):
    """Base class for query handlers."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @abstractmethod
    async def execute(self, query: Query) -> Dict[str, Any]:
        """Execute the query and return results."""
        pass


class ExpenseQueryHandler(QueryHandler):
    """Handler for expense queries."""
    
    async def execute(self, query: GetExpensesQuery) -> Dict[str, Any]:
        """Get expenses with optional filters."""
        sql = """
            SELECT e.id, e.project_id, e.document_id, e.invoice_number, e.invoice_date,
                   e.vendor_name, e.vendor_nip, e.net_amount, e.vat_amount, e.gross_amount,
                   e.currency, e.br_qualified, e.br_category, e.br_deduction_rate,
                   e.status, e.created_at, p.name as project_name
            FROM read_models.expenses e
            LEFT JOIN read_models.projects p ON e.project_id = p.id
            WHERE 1=1
        """
        params = {}
        
        if query.project_id:
            sql += " AND e.project_id = :project_id"
            params["project_id"] = query.project_id
        
        if query.year:
            sql += " AND EXTRACT(YEAR FROM e.invoice_date) = :year"
            params["year"] = query.year
        
        if query.br_qualified is not None:
            sql += " AND e.br_qualified = :br_qualified"
            params["br_qualified"] = query.br_qualified
        
        if query.status:
            sql += " AND e.status = :status"
            params["status"] = query.status
        
        sql += " ORDER BY e.invoice_date DESC LIMIT :limit OFFSET :offset"
        params["limit"] = query.limit
        params["offset"] = query.offset
        
        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()
        
        return {
            "items": [
                {
                    "id": str(r[0]),
                    "project_id": str(r[1]) if r[1] else None,
                    "document_id": str(r[2]) if r[2] else None,
                    "invoice_number": r[3],
                    "invoice_date": str(r[4]) if r[4] else None,
                    "vendor_name": r[5],
                    "vendor_nip": r[6],
                    "net_amount": float(r[7] or 0),
                    "vat_amount": float(r[8] or 0),
                    "gross_amount": float(r[9] or 0),
                    "currency": r[10] or "PLN",
                    "br_qualified": r[11] or False,
                    "br_category": r[12],
                    "br_deduction_rate": float(r[13] or 1.0),
                    "status": r[14],
                    "created_at": r[15].isoformat() if r[15] else None,
                    "project_name": r[16],
                    "type": "expense",
                }
                for r in rows
            ],
            "count": len(rows),
            "limit": query.limit,
            "offset": query.offset,
        }


class RevenueQueryHandler(QueryHandler):
    """Handler for revenue queries."""
    
    async def execute(self, query: GetRevenuesQuery) -> Dict[str, Any]:
        """Get revenues with optional filters."""
        sql = """
            SELECT r.id, r.project_id, r.document_id, r.invoice_number, r.invoice_date,
                   r.client_name, r.client_nip, r.net_amount, r.vat_amount, r.gross_amount,
                   r.currency, r.ip_qualified, r.ip_type, r.ip_description,
                   r.created_at, p.name as project_name
            FROM read_models.revenues r
            LEFT JOIN read_models.projects p ON r.project_id = p.id
            WHERE 1=1
        """
        params = {}
        
        if query.project_id:
            sql += " AND r.project_id = :project_id"
            params["project_id"] = query.project_id
        
        if query.year:
            sql += " AND EXTRACT(YEAR FROM r.invoice_date) = :year"
            params["year"] = query.year
        
        if query.ip_qualified is not None:
            sql += " AND r.ip_qualified = :ip_qualified"
            params["ip_qualified"] = query.ip_qualified
        
        sql += " ORDER BY r.invoice_date DESC LIMIT :limit OFFSET :offset"
        params["limit"] = query.limit
        params["offset"] = query.offset
        
        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()
        
        return {
            "items": [
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
                    "ip_type": r[12],
                    "ip_description": r[13],
                    "created_at": r[14].isoformat() if r[14] else None,
                    "project_name": r[15],
                    "type": "revenue",
                }
                for r in rows
            ],
            "count": len(rows),
            "limit": query.limit,
            "offset": query.offset,
        }


class InvoiceHistoryQueryHandler(QueryHandler):
    """Handler for invoice history queries using event store."""
    
    async def execute(self, query: GetInvoiceHistoryQuery) -> Dict[str, Any]:
        """Get event history for an invoice."""
        event_store = await get_event_store(self.db)
        events = await event_store.get_events_for_aggregate(query.invoice_id)
        
        return {
            "invoice_id": query.invoice_id,
            "events": events,
            "event_count": len(events),
        }


class UnifiedInvoiceQueryHandler(QueryHandler):
    """Handler for unified invoice queries (expenses + revenues)."""
    
    async def execute(self, query: GetAllInvoicesQuery) -> Dict[str, Any]:
        """Get all invoices from both expenses and revenues tables."""
        items = []
        
        # Get expenses if requested
        if query.invoice_type in (None, 'all', 'expense'):
            expense_handler = ExpenseQueryHandler(self.db)
            expense_query = GetExpensesQuery(
                project_id=query.project_id,
                year=query.year,
                limit=query.limit,
                offset=query.offset,
            )
            expense_result = await expense_handler.execute(expense_query)
            items.extend(expense_result["items"])
        
        # Get revenues if requested
        if query.invoice_type in (None, 'all', 'revenue'):
            revenue_handler = RevenueQueryHandler(self.db)
            revenue_query = GetRevenuesQuery(
                project_id=query.project_id,
                year=query.year,
                limit=query.limit,
                offset=query.offset,
            )
            revenue_result = await revenue_handler.execute(revenue_query)
            items.extend(revenue_result["items"])
        
        # Sort by date descending
        items.sort(key=lambda x: x.get("invoice_date") or "", reverse=True)
        
        return {
            "items": items[:query.limit],
            "count": len(items),
            "limit": query.limit,
            "offset": query.offset,
        }


async def get_query_handler(query_type: str, db: AsyncSession) -> QueryHandler:
    """Factory function to get appropriate query handler."""
    handlers = {
        "expenses": ExpenseQueryHandler,
        "revenues": RevenueQueryHandler,
        "invoice_history": InvoiceHistoryQueryHandler,
        "all_invoices": UnifiedInvoiceQueryHandler,
    }
    handler_class = handlers.get(query_type)
    if not handler_class:
        raise ValueError(f"Unknown query type: {query_type}")
    return handler_class(db)
