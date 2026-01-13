"""
Domain Events and Event Store for Event Sourcing.

Events represent facts that have happened in the system.
The event store provides append-only storage for events.
"""

import uuid
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EventType(str, Enum):
    """Invoice lifecycle events."""
    INVOICE_UPLOADED = "invoice.uploaded"
    INVOICE_OCR_COMPLETED = "invoice.ocr_completed"
    INVOICE_TYPE_DETECTED = "invoice.type_detected"
    INVOICE_CLASSIFIED_AS_EXPENSE = "invoice.classified_as_expense"
    INVOICE_CLASSIFIED_AS_REVENUE = "invoice.classified_as_revenue"
    EXPENSE_BR_QUALIFIED = "expense.br_qualified"
    EXPENSE_BR_DISQUALIFIED = "expense.br_disqualified"
    REVENUE_IP_QUALIFIED = "revenue.ip_qualified"
    REVENUE_IP_DISQUALIFIED = "revenue.ip_disqualified"
    INVOICE_RECLASSIFIED = "invoice.reclassified"
    INVOICE_DELETED = "invoice.deleted"


@dataclass
class DomainEvent:
    """Base class for domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    aggregate_id: str = ""  # Invoice/Document ID
    aggregate_type: str = "invoice"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InvoiceCreatedEvent(DomainEvent):
    """Event when an invoice is uploaded and processed."""
    event_type: str = EventType.INVOICE_UPLOADED
    
    @classmethod
    def create(cls, document_id: str, invoice_data: dict, detected_type: str = "unknown") -> "InvoiceCreatedEvent":
        return cls(
            aggregate_id=document_id,
            data={
                "invoice_number": invoice_data.get("invoice_number"),
                "invoice_date": invoice_data.get("invoice_date"),
                "vendor_nip": invoice_data.get("vendor_nip"),
                "gross_amount": invoice_data.get("gross_amount"),
                "detected_type": detected_type,
            }
        )


@dataclass
class InvoiceClassifiedEvent(DomainEvent):
    """Event when an invoice is classified (B+R expense or IP revenue)."""
    
    @classmethod
    def create_expense(cls, expense_id: str, br_category: str, br_qualified: bool, 
                       deduction_rate: float = 1.0, reason: str = None) -> "InvoiceClassifiedEvent":
        return cls(
            event_type=EventType.EXPENSE_BR_QUALIFIED if br_qualified else EventType.EXPENSE_BR_DISQUALIFIED,
            aggregate_id=expense_id,
            aggregate_type="expense",
            data={
                "br_category": br_category,
                "br_qualified": br_qualified,
                "br_deduction_rate": deduction_rate,
                "reason": reason,
            }
        )
    
    @classmethod
    def create_revenue(cls, revenue_id: str, ip_type: str, ip_qualified: bool,
                       description: str = None) -> "InvoiceClassifiedEvent":
        return cls(
            event_type=EventType.REVENUE_IP_QUALIFIED if ip_qualified else EventType.REVENUE_IP_DISQUALIFIED,
            aggregate_id=revenue_id,
            aggregate_type="revenue",
            data={
                "ip_type": ip_type,
                "ip_qualified": ip_qualified,
                "ip_description": description,
            }
        )


@dataclass
class InvoiceReclassifiedEvent(DomainEvent):
    """Event when an invoice type is changed (expense <-> revenue)."""
    event_type: str = EventType.INVOICE_RECLASSIFIED
    
    @classmethod
    def create(cls, invoice_id: str, from_type: str, to_type: str, reason: str = None) -> "InvoiceReclassifiedEvent":
        return cls(
            aggregate_id=invoice_id,
            data={
                "from_type": from_type,
                "to_type": to_type,
                "reason": reason,
            }
        )


class EventStore:
    """
    Append-only event store for event sourcing.
    
    Stores all domain events for audit trail and replay capability.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ensure_table_exists(self):
        """Create events table if not exists."""
        # Check if table exists first
        result = await self.db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'read_models' AND table_name = 'domain_events'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            await self.db.execute(text("""
                CREATE TABLE read_models.domain_events (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    event_id UUID NOT NULL UNIQUE,
                    event_type VARCHAR(100) NOT NULL,
                    aggregate_id UUID NOT NULL,
                    aggregate_type VARCHAR(50) NOT NULL DEFAULT 'invoice',
                    version INTEGER NOT NULL DEFAULT 1,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    data JSONB NOT NULL DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            await self.db.execute(text("""
                CREATE INDEX idx_events_aggregate ON read_models.domain_events(aggregate_id, version)
            """))
            await self.db.execute(text("""
                CREATE INDEX idx_events_type ON read_models.domain_events(event_type)
            """))
            await self.db.execute(text("""
                CREATE INDEX idx_events_timestamp ON read_models.domain_events(timestamp)
            """))
    
    async def append(self, event: DomainEvent) -> str:
        """Append event to the store. Returns event_id."""
        # Convert timestamp string to datetime if needed
        timestamp = event.timestamp
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Convert event_type enum to string if needed
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        
        await self.db.execute(
            text("""
                INSERT INTO read_models.domain_events 
                (event_id, event_type, aggregate_id, aggregate_type, version, timestamp, data, metadata)
                VALUES (:event_id, :event_type, :aggregate_id, :aggregate_type, :version, :timestamp, 
                        CAST(:data AS jsonb), CAST(:metadata AS jsonb))
            """),
            {
                "event_id": event.event_id,
                "event_type": event_type,
                "aggregate_id": event.aggregate_id,
                "aggregate_type": event.aggregate_type,
                "version": event.version,
                "timestamp": timestamp,
                "data": json.dumps(event.data),
                "metadata": json.dumps(event.metadata),
            }
        )
        return event.event_id
    
    async def get_events_for_aggregate(self, aggregate_id: str) -> List[dict]:
        """Get all events for an aggregate (invoice/expense/revenue)."""
        result = await self.db.execute(
            text("""
                SELECT event_id, event_type, aggregate_id, aggregate_type, 
                       version, timestamp, data, metadata
                FROM read_models.domain_events
                WHERE aggregate_id = :aggregate_id
                ORDER BY version ASC, timestamp ASC
            """),
            {"aggregate_id": aggregate_id}
        )
        return [
            {
                "event_id": str(r[0]),
                "event_type": r[1],
                "aggregate_id": str(r[2]),
                "aggregate_type": r[3],
                "version": r[4],
                "timestamp": r[5].isoformat() if r[5] else None,
                "data": r[6],
                "metadata": r[7],
            }
            for r in result.fetchall()
        ]
    
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[dict]:
        """Get recent events of a specific type."""
        result = await self.db.execute(
            text("""
                SELECT event_id, event_type, aggregate_id, aggregate_type,
                       version, timestamp, data, metadata
                FROM read_models.domain_events
                WHERE event_type = :event_type
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"event_type": event_type, "limit": limit}
        )
        return [
            {
                "event_id": str(r[0]),
                "event_type": r[1],
                "aggregate_id": str(r[2]),
                "aggregate_type": r[3],
                "version": r[4],
                "timestamp": r[5].isoformat() if r[5] else None,
                "data": r[6],
                "metadata": r[7],
            }
            for r in result.fetchall()
        ]


async def get_event_store(db: AsyncSession) -> EventStore:
    """Factory function to get event store instance."""
    store = EventStore(db)
    await store.ensure_table_exists()
    return store
