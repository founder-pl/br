"""
CQRS (Command Query Responsibility Segregation) and Event Sourcing module.

This module implements:
- Command handlers for write operations
- Query handlers for read operations  
- Event store for audit trail and event sourcing
- Domain events for invoice lifecycle
"""

from .commands import (
    ClassifyExpenseCommand,
    ClassifyRevenueCommand,
    ReclassifyInvoiceCommand,
    CommandHandler,
    ExpenseCommandHandler,
    RevenueCommandHandler,
)

from .events import (
    DomainEvent,
    InvoiceCreatedEvent,
    InvoiceClassifiedEvent,
    InvoiceReclassifiedEvent,
    EventStore,
)

from .queries import (
    GetExpensesQuery,
    GetRevenuesQuery,
    GetInvoiceHistoryQuery,
    QueryHandler,
)

__all__ = [
    # Commands
    "ClassifyExpenseCommand",
    "ClassifyRevenueCommand",
    "ReclassifyInvoiceCommand",
    "CommandHandler",
    "ExpenseCommandHandler",
    "RevenueCommandHandler",
    # Events
    "DomainEvent",
    "InvoiceCreatedEvent",
    "InvoiceClassifiedEvent",
    "InvoiceReclassifiedEvent",
    "EventStore",
    # Queries
    "GetExpensesQuery",
    "GetRevenuesQuery",
    "GetInvoiceHistoryQuery",
    "QueryHandler",
]
