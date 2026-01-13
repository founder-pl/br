"""
Audit Trail Service - Event Sourcing for compliance tracking.

P2 Task: Event sourcing dla audit trail
Based on: todo/05-br-priority-roadmap.md

Tracks all changes to expenses for tax authority audits.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import json
import uuid
import structlog

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Types of audit events."""
    EXPENSE_CREATED = "expense.created"
    EXPENSE_UPDATED = "expense.updated"
    EXPENSE_DELETED = "expense.deleted"
    EXPENSE_CLASSIFIED = "expense.classified"
    EXPENSE_VALIDATED = "expense.validated"
    BR_QUALIFIED = "expense.br_qualified"
    BR_DISQUALIFIED = "expense.br_disqualified"
    JUSTIFICATION_GENERATED = "expense.justification_generated"
    DOCUMENT_ATTACHED = "expense.document_attached"
    VENDOR_UPDATED = "expense.vendor_updated"


@dataclass
class AuditEvent:
    """Single audit event."""
    event_id: str
    event_type: AuditEventType
    aggregate_id: str  # expense_id
    aggregate_type: str  # "expense"
    timestamp: datetime
    actor: str  # user or system
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "data": self.data,
            "metadata": self.metadata
        }


class AuditTrailService:
    """
    Service for recording and querying audit events.
    
    Provides complete audit trail for tax compliance.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._events_buffer: List[AuditEvent] = []
    
    async def record(
        self,
        event_type: AuditEventType,
        aggregate_id: str,
        data: Dict[str, Any],
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Record an audit event.
        
        Args:
            event_type: Type of event
            aggregate_id: ID of the entity (e.g., expense_id)
            data: Event data (changes, values, etc.)
            actor: Who performed the action
            metadata: Additional context
            
        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type="expense",
            timestamp=datetime.utcnow(),
            actor=actor,
            data=data,
            metadata=metadata or {}
        )
        
        # Buffer event
        self._events_buffer.append(event)
        
        # Log for immediate visibility
        logger.info(
            "Audit event recorded",
            event_type=event_type.value,
            aggregate_id=aggregate_id,
            actor=actor
        )
        
        # Persist if db available
        if self.db:
            await self._persist_event(event)
        
        return event
    
    async def _persist_event(self, event: AuditEvent):
        """Persist event to database."""
        from sqlalchemy import text
        
        try:
            await self.db.execute(
                text("""
                    INSERT INTO event_store.events 
                    (id, aggregate_id, aggregate_type, event_type, event_data, metadata, created_at)
                    VALUES (:id, :aggregate_id, :aggregate_type, :event_type, :event_data, :metadata, :created_at)
                """),
                {
                    "id": event.event_id,
                    "aggregate_id": event.aggregate_id,
                    "aggregate_type": event.aggregate_type,
                    "event_type": event.event_type.value,
                    "event_data": json.dumps(event.data),
                    "metadata": json.dumps(event.metadata),
                    "created_at": event.timestamp
                }
            )
        except Exception as e:
            logger.warning("Failed to persist audit event", error=str(e))
    
    async def get_history(
        self,
        aggregate_id: str,
        event_types: Optional[List[AuditEventType]] = None
    ) -> List[AuditEvent]:
        """
        Get audit history for an entity.
        
        Args:
            aggregate_id: Entity ID
            event_types: Filter by event types (optional)
            
        Returns:
            List of audit events in chronological order
        """
        if not self.db:
            # Return buffered events for this aggregate
            events = [e for e in self._events_buffer if e.aggregate_id == aggregate_id]
            if event_types:
                events = [e for e in events if e.event_type in event_types]
            return sorted(events, key=lambda e: e.timestamp)
        
        from sqlalchemy import text
        
        query = """
            SELECT id, aggregate_id, aggregate_type, event_type, 
                   event_data, metadata, created_at
            FROM event_store.events
            WHERE aggregate_id = :aggregate_id
        """
        params = {"aggregate_id": aggregate_id}
        
        if event_types:
            types_list = [et.value for et in event_types]
            query += " AND event_type = ANY(:types)"
            params["types"] = types_list
        
        query += " ORDER BY created_at ASC"
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        return [
            AuditEvent(
                event_id=row[0],
                event_type=AuditEventType(row[3]),
                aggregate_id=row[1],
                aggregate_type=row[2],
                timestamp=row[6],
                actor=json.loads(row[5]).get("actor", "unknown"),
                data=json.loads(row[4]),
                metadata=json.loads(row[5])
            )
            for row in rows
        ]
    
    async def get_changes_report(
        self,
        aggregate_id: str
    ) -> Dict[str, Any]:
        """
        Generate a changes report for audit purposes.
        
        Returns a summary of all changes to an entity.
        """
        events = await self.get_history(aggregate_id)
        
        if not events:
            return {"aggregate_id": aggregate_id, "events": [], "summary": "Brak historii zmian"}
        
        return {
            "aggregate_id": aggregate_id,
            "first_event": events[0].timestamp.isoformat(),
            "last_event": events[-1].timestamp.isoformat(),
            "total_events": len(events),
            "event_types": list(set(e.event_type.value for e in events)),
            "events": [e.to_dict() for e in events[-10:]],  # Last 10 events
            "summary": f"Zarejestrowano {len(events)} zdarzeń od {events[0].timestamp.date()}"
        }


# Convenience functions for common audit events

async def audit_expense_created(
    service: AuditTrailService,
    expense_id: str,
    expense_data: Dict[str, Any],
    actor: str = "system"
) -> AuditEvent:
    """Record expense creation."""
    return await service.record(
        AuditEventType.EXPENSE_CREATED,
        expense_id,
        {"expense": expense_data},
        actor
    )


async def audit_expense_classified(
    service: AuditTrailService,
    expense_id: str,
    category: str,
    reason: str,
    confidence: float,
    actor: str = "system"
) -> AuditEvent:
    """Record expense classification."""
    return await service.record(
        AuditEventType.EXPENSE_CLASSIFIED,
        expense_id,
        {
            "category": category,
            "reason": reason,
            "confidence": confidence
        },
        actor
    )


async def audit_br_qualification(
    service: AuditTrailService,
    expense_id: str,
    qualified: bool,
    category: str,
    reason: str,
    deduction_rate: float,
    actor: str = "system"
) -> AuditEvent:
    """Record B+R qualification decision."""
    event_type = AuditEventType.BR_QUALIFIED if qualified else AuditEventType.BR_DISQUALIFIED
    return await service.record(
        event_type,
        expense_id,
        {
            "qualified": qualified,
            "category": category,
            "reason": reason,
            "deduction_rate": deduction_rate
        },
        actor
    )


# Singleton
_audit_service: Optional[AuditTrailService] = None


def get_audit_service(db_session=None) -> AuditTrailService:
    """Get or create audit trail service."""
    global _audit_service
    if _audit_service is None or db_session:
        _audit_service = AuditTrailService(db_session)
    return _audit_service
