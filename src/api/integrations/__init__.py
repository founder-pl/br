"""
Integrations module - External system integrations.

Contains:
- KSeF client for Polish electronic invoice system
- JPK export for tax authority reporting
"""

from .ksef_client import (
    KSeFClient,
    KSeFService,
    KSeFInvoice,
    KSeFEnvironment,
    get_ksef_service,
)
from .jpk_export import (
    JPKExporter,
    JPKHeader,
    JPKSalesRecord,
    JPKPurchaseRecord,
    JPKDeclaration,
    create_jpk_from_expenses,
)

__all__ = [
    "KSeFClient",
    "KSeFService",
    "KSeFInvoice",
    "KSeFEnvironment",
    "get_ksef_service",
    "JPKExporter",
    "JPKHeader",
    "JPKSalesRecord",
    "JPKPurchaseRecord",
    "JPKDeclaration",
    "create_jpk_from_expenses",
]
