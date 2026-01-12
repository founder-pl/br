"""
Base Accounting Client - Abstract interface for accounting integrations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class InvoiceType(str, Enum):
    """Invoice types"""
    SALES = "sales"  # Faktura sprzedaży
    PURCHASE = "purchase"  # Faktura zakupu (koszt)
    PROFORMA = "proforma"
    CORRECTION = "correction"  # Korekta


class InvoiceStatus(str, Enum):
    """Invoice status"""
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


@dataclass
class InvoiceItem:
    """Single invoice line item"""
    name: str
    quantity: float
    unit: str  # szt, godz, usł, etc.
    unit_price_net: float
    vat_rate: float  # 0, 5, 8, 23
    
    # Calculated
    net_amount: float = 0
    vat_amount: float = 0
    gross_amount: float = 0
    
    # Optional
    pkwiu: Optional[str] = None  # Polish classification
    gtu: Optional[str] = None  # GTU code for JPK
    description: Optional[str] = None
    
    def __post_init__(self):
        self.net_amount = self.quantity * self.unit_price_net
        self.vat_amount = self.net_amount * (self.vat_rate / 100)
        self.gross_amount = self.net_amount + self.vat_amount


@dataclass
class Invoice:
    """Invoice data model"""
    # Identification
    id: str
    number: str
    invoice_type: InvoiceType
    status: InvoiceStatus
    
    # Dates
    issue_date: date
    sale_date: Optional[date] = None
    due_date: Optional[date] = None
    
    # Parties
    seller_name: str = ""
    seller_nip: str = ""
    seller_address: str = ""
    
    buyer_name: str = ""
    buyer_nip: str = ""
    buyer_address: str = ""
    
    # Items
    items: List[InvoiceItem] = None
    
    # Totals
    net_amount: float = 0
    vat_amount: float = 0
    gross_amount: float = 0
    currency: str = "PLN"
    
    # Payment
    payment_method: str = ""
    bank_account: str = ""
    is_paid: bool = False
    paid_date: Optional[date] = None
    
    # Additional
    notes: str = ""
    pdf_url: Optional[str] = None
    raw_data: Optional[Dict] = None  # Original API response
    
    def __post_init__(self):
        if self.items is None:
            self.items = []


@dataclass
class AccountingDocument:
    """Generic accounting document (not just invoices)"""
    id: str
    document_type: str  # invoice, receipt, contract, etc.
    number: str
    issue_date: date
    
    counterparty_name: str = ""
    counterparty_nip: str = ""
    
    net_amount: float = 0
    vat_amount: float = 0
    gross_amount: float = 0
    currency: str = "PLN"
    
    description: str = ""
    category: str = ""
    
    file_url: Optional[str] = None
    raw_data: Optional[Dict] = None


class BaseAccountingClient(ABC):
    """
    Abstract base class for accounting system integrations.
    Implement this for each accounting provider.
    """
    
    def __init__(self, credentials: Dict[str, Any], settings: Dict[str, Any] = None):
        """
        Initialize accounting client.
        
        Args:
            credentials: API keys, tokens, etc.
            settings: Additional settings (company_id, etc.)
        """
        self.credentials = credentials
        self.settings = settings or {}
        self.logger = structlog.get_logger().bind(provider=self.provider_name)
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name identifier"""
        pass
    
    @abstractmethod
    async def verify_connection(self) -> bool:
        """
        Verify that credentials work and connection is valid.
        Returns True if connection successful.
        """
        pass
    
    @abstractmethod
    async def get_invoices(
        self,
        invoice_type: InvoiceType = None,
        date_from: date = None,
        date_to: date = None,
        status: InvoiceStatus = None,
        page: int = 1,
        per_page: int = 50
    ) -> List[Invoice]:
        """
        Fetch invoices from accounting system.
        
        Args:
            invoice_type: Filter by type (sales/purchase)
            date_from: Start date filter
            date_to: End date filter
            status: Filter by status
            page: Page number
            per_page: Items per page
        
        Returns:
            List of Invoice objects
        """
        pass
    
    @abstractmethod
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """
        Get single invoice by ID.
        
        Args:
            invoice_id: Invoice ID
        
        Returns:
            Invoice object or None
        """
        pass
    
    @abstractmethod
    async def get_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """
        Download invoice PDF.
        
        Args:
            invoice_id: Invoice ID
        
        Returns:
            PDF content as bytes
        """
        pass
    
    async def get_expense_invoices(
        self,
        date_from: date = None,
        date_to: date = None,
        page: int = 1,
        per_page: int = 50
    ) -> List[Invoice]:
        """Get purchase/expense invoices (for B+R tracking)"""
        return await self.get_invoices(
            invoice_type=InvoiceType.PURCHASE,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page
        )
    
    async def get_documents(
        self,
        date_from: date = None,
        date_to: date = None,
        document_type: str = None
    ) -> List[AccountingDocument]:
        """
        Get all accounting documents (invoices, receipts, etc.)
        Override in subclass if supported.
        """
        # Default implementation: convert invoices to documents
        invoices = await self.get_invoices(date_from=date_from, date_to=date_to)
        return [
            AccountingDocument(
                id=inv.id,
                document_type="invoice",
                number=inv.number,
                issue_date=inv.issue_date,
                counterparty_name=inv.buyer_name if inv.invoice_type == InvoiceType.SALES else inv.seller_name,
                counterparty_nip=inv.buyer_nip if inv.invoice_type == InvoiceType.SALES else inv.seller_nip,
                net_amount=inv.net_amount,
                vat_amount=inv.vat_amount,
                gross_amount=inv.gross_amount,
                currency=inv.currency,
                file_url=inv.pdf_url,
                raw_data=inv.raw_data
            )
            for inv in invoices
        ]
    
    async def sync_invoices_to_br_system(
        self,
        date_from: date,
        date_to: date,
        project_id: str = None
    ) -> Dict[str, Any]:
        """
        Sync invoices from accounting system to B+R system.
        
        Returns:
            Dict with sync results
        """
        from src.api.database import get_db_context
        
        results = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": [],
        }
        
        try:
            invoices = await self.get_expense_invoices(
                date_from=date_from,
                date_to=date_to
            )
            
            results["total"] = len(invoices)
            
            async with get_db_context() as db:
                for invoice in invoices:
                    try:
                        # Check if exists
                        existing = await db.execute(
                            """SELECT id FROM read_models.expenses 
                               WHERE invoice_number = :num AND vendor_nip = :nip""",
                            {"num": invoice.number, "nip": invoice.seller_nip}
                        )
                        
                        if existing.fetchone():
                            results["updated"] += 1
                        else:
                            # Create new expense
                            import uuid
                            expense_id = str(uuid.uuid4())
                            
                            await db.execute(
                                """INSERT INTO read_models.expenses 
                                   (id, project_id, invoice_number, invoice_date, 
                                    vendor_name, vendor_nip, net_amount, vat_amount, 
                                    gross_amount, currency, status, integration_source)
                                   VALUES (:id, :project_id, :num, :date, :vendor, :nip,
                                           :net, :vat, :gross, :currency, 'imported', :source)""",
                                {
                                    "id": expense_id,
                                    "project_id": project_id or "00000000-0000-0000-0000-000000000001",
                                    "num": invoice.number,
                                    "date": invoice.issue_date,
                                    "vendor": invoice.seller_name,
                                    "nip": invoice.seller_nip,
                                    "net": invoice.net_amount,
                                    "vat": invoice.vat_amount,
                                    "gross": invoice.gross_amount,
                                    "currency": invoice.currency,
                                    "source": self.provider_name
                                }
                            )
                            results["created"] += 1
                    
                    except Exception as e:
                        results["errors"].append({
                            "invoice": invoice.number,
                            "error": str(e)
                        })
            
            self.logger.info("Invoice sync completed", **results)
            
        except Exception as e:
            self.logger.error("Invoice sync failed", error=str(e))
            results["errors"].append({"error": str(e)})
        
        return results
