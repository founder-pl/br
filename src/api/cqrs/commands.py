"""
Command Handlers for CQRS pattern.

Commands represent intentions to change system state.
Each command has a dedicated handler that validates and executes the change.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .events import (
    EventStore, 
    InvoiceClassifiedEvent, 
    InvoiceReclassifiedEvent,
    get_event_store
)


@dataclass
class Command(ABC):
    """Base class for commands."""
    pass


@dataclass
class ClassifyExpenseCommand(Command):
    """Command to classify an expense for B+R deduction."""
    expense_id: str
    br_qualified: bool
    br_category: Optional[str] = None
    br_deduction_rate: float = 1.0
    reason: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class ClassifyRevenueCommand(Command):
    """Command to classify a revenue for IP Box."""
    revenue_id: str
    ip_qualified: bool
    ip_type: Optional[str] = None
    ip_description: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class ReclassifyInvoiceCommand(Command):
    """Command to reclassify an invoice (expense <-> revenue)."""
    invoice_id: str
    from_type: str  # 'expense' or 'revenue'
    to_type: str    # 'expense' or 'revenue'
    reason: Optional[str] = None
    user_id: Optional[str] = None


class CommandHandler(ABC):
    """Base class for command handlers."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._event_store: Optional[EventStore] = None
    
    async def get_event_store(self) -> EventStore:
        if self._event_store is None:
            self._event_store = await get_event_store(self.db)
        return self._event_store
    
    @abstractmethod
    async def handle(self, command: Command) -> Dict[str, Any]:
        """Execute the command and return result."""
        pass


class ExpenseCommandHandler(CommandHandler):
    """Handler for expense-related commands."""
    
    async def handle(self, command: ClassifyExpenseCommand) -> Dict[str, Any]:
        """Classify an expense for B+R deduction."""
        # Validate expense exists
        result = await self.db.execute(
            text("SELECT id, gross_amount FROM read_models.expenses WHERE id = :id"),
            {"id": command.expense_id}
        )
        expense = result.fetchone()
        if not expense:
            return {"success": False, "error": "Expense not found"}
        
        # Update expense
        await self.db.execute(
            text("""
                UPDATE read_models.expenses SET
                    br_qualified = :br_qualified,
                    br_category = COALESCE(:br_category, br_category),
                    br_deduction_rate = :br_deduction_rate,
                    br_qualification_reason = COALESCE(:reason, br_qualification_reason),
                    manual_override = true,
                    status = 'classified',
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": command.expense_id,
                "br_qualified": command.br_qualified,
                "br_category": command.br_category,
                "br_deduction_rate": command.br_deduction_rate,
                "reason": command.reason,
            }
        )
        
        # Store event
        event_store = await self.get_event_store()
        event = InvoiceClassifiedEvent.create_expense(
            expense_id=command.expense_id,
            br_category=command.br_category or "other",
            br_qualified=command.br_qualified,
            deduction_rate=command.br_deduction_rate,
            reason=command.reason,
        )
        event.metadata = {"user_id": command.user_id} if command.user_id else {}
        await event_store.append(event)
        
        return {
            "success": True,
            "expense_id": command.expense_id,
            "br_qualified": command.br_qualified,
            "event_id": event.event_id,
        }


class RevenueCommandHandler(CommandHandler):
    """Handler for revenue-related commands."""
    
    async def handle(self, command: ClassifyRevenueCommand) -> Dict[str, Any]:
        """Classify a revenue for IP Box."""
        # Validate revenue exists
        result = await self.db.execute(
            text("SELECT id, gross_amount FROM read_models.revenues WHERE id = :id"),
            {"id": command.revenue_id}
        )
        revenue = result.fetchone()
        if not revenue:
            return {"success": False, "error": "Revenue not found"}
        
        # Update revenue
        await self.db.execute(
            text("""
                UPDATE read_models.revenues SET
                    ip_qualified = :ip_qualified,
                    ip_type = COALESCE(:ip_type, ip_type),
                    ip_description = COALESCE(:ip_description, ip_description),
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "id": command.revenue_id,
                "ip_qualified": command.ip_qualified,
                "ip_type": command.ip_type,
                "ip_description": command.ip_description,
            }
        )
        
        # Store event
        event_store = await self.get_event_store()
        event = InvoiceClassifiedEvent.create_revenue(
            revenue_id=command.revenue_id,
            ip_type=command.ip_type or "software",
            ip_qualified=command.ip_qualified,
            description=command.ip_description,
        )
        event.metadata = {"user_id": command.user_id} if command.user_id else {}
        await event_store.append(event)
        
        return {
            "success": True,
            "revenue_id": command.revenue_id,
            "ip_qualified": command.ip_qualified,
            "event_id": event.event_id,
        }


class ReclassifyInvoiceHandler(CommandHandler):
    """Handler for invoice reclassification (expense <-> revenue)."""
    
    async def handle(self, command: ReclassifyInvoiceCommand) -> Dict[str, Any]:
        """Reclassify an invoice from expense to revenue or vice versa."""
        company_nip = "5881918662"  # TODO: Get from config
        
        if command.from_type == "expense" and command.to_type == "revenue":
            # Move expense to revenue
            result = await self.db.execute(
                text("""
                    SELECT id, project_id, document_id, invoice_number, invoice_date,
                           vendor_name, vendor_nip, net_amount, vat_amount, gross_amount, currency
                    FROM read_models.expenses WHERE id = :id
                """),
                {"id": command.invoice_id}
            )
            expense = result.fetchone()
            if not expense:
                return {"success": False, "error": "Expense not found"}
            
            # Insert as revenue
            new_revenue_id = await self.db.execute(
                text("""
                    INSERT INTO read_models.revenues 
                    (project_id, document_id, invoice_number, invoice_date,
                     client_name, client_nip, net_amount, vat_amount, gross_amount, currency)
                    VALUES (:project_id, :document_id, :invoice_number, :invoice_date,
                            :client_name, :client_nip, :net_amount, :vat_amount, :gross_amount, :currency)
                    RETURNING id
                """),
                {
                    "project_id": expense[1],
                    "document_id": expense[2],
                    "invoice_number": expense[3],
                    "invoice_date": expense[4],
                    "client_name": expense[5],  # vendor becomes client for revenue
                    "client_nip": expense[6],
                    "net_amount": expense[7],
                    "vat_amount": expense[8],
                    "gross_amount": expense[9],
                    "currency": expense[10],
                }
            )
            new_id = str(new_revenue_id.fetchone()[0])
            
            # Delete expense
            await self.db.execute(
                text("DELETE FROM read_models.expenses WHERE id = :id"),
                {"id": command.invoice_id}
            )
            
            # Store event
            event_store = await self.get_event_store()
            event = InvoiceReclassifiedEvent.create(
                invoice_id=command.invoice_id,
                from_type="expense",
                to_type="revenue",
                reason=command.reason,
            )
            event.metadata = {"user_id": command.user_id, "new_id": new_id}
            await event_store.append(event)
            
            return {
                "success": True,
                "old_id": command.invoice_id,
                "new_id": new_id,
                "from_type": "expense",
                "to_type": "revenue",
                "event_id": event.event_id,
            }
        
        elif command.from_type == "revenue" and command.to_type == "expense":
            # Move revenue to expense
            result = await self.db.execute(
                text("""
                    SELECT id, project_id, document_id, invoice_number, invoice_date,
                           client_name, client_nip, net_amount, vat_amount, gross_amount, currency
                    FROM read_models.revenues WHERE id = :id
                """),
                {"id": command.invoice_id}
            )
            revenue = result.fetchone()
            if not revenue:
                return {"success": False, "error": "Revenue not found"}
            
            # Insert as expense
            new_expense_id = await self.db.execute(
                text("""
                    INSERT INTO read_models.expenses 
                    (project_id, document_id, invoice_number, invoice_date,
                     vendor_name, vendor_nip, net_amount, vat_amount, gross_amount, currency)
                    VALUES (:project_id, :document_id, :invoice_number, :invoice_date,
                            :vendor_name, :vendor_nip, :net_amount, :vat_amount, :gross_amount, :currency)
                    RETURNING id
                """),
                {
                    "project_id": revenue[1],
                    "document_id": revenue[2],
                    "invoice_number": revenue[3],
                    "invoice_date": revenue[4],
                    "vendor_name": revenue[5],  # client becomes vendor for expense
                    "vendor_nip": revenue[6],
                    "net_amount": revenue[7],
                    "vat_amount": revenue[8],
                    "gross_amount": revenue[9],
                    "currency": revenue[10],
                }
            )
            new_id = str(new_expense_id.fetchone()[0])
            
            # Delete revenue
            await self.db.execute(
                text("DELETE FROM read_models.revenues WHERE id = :id"),
                {"id": command.invoice_id}
            )
            
            # Store event
            event_store = await self.get_event_store()
            event = InvoiceReclassifiedEvent.create(
                invoice_id=command.invoice_id,
                from_type="revenue",
                to_type="expense",
                reason=command.reason,
            )
            event.metadata = {"user_id": command.user_id, "new_id": new_id}
            await event_store.append(event)
            
            return {
                "success": True,
                "old_id": command.invoice_id,
                "new_id": new_id,
                "from_type": "revenue",
                "to_type": "expense",
                "event_id": event.event_id,
            }
        
        return {"success": False, "error": f"Invalid reclassification: {command.from_type} -> {command.to_type}"}


async def get_command_handler(command_type: str, db: AsyncSession) -> CommandHandler:
    """Factory function to get appropriate command handler."""
    handlers = {
        "classify_expense": ExpenseCommandHandler,
        "classify_revenue": RevenueCommandHandler,
        "reclassify_invoice": ReclassifyInvoiceHandler,
    }
    handler_class = handlers.get(command_type)
    if not handler_class:
        raise ValueError(f"Unknown command type: {command_type}")
    return handler_class(db)
