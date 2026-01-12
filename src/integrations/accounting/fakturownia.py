"""
Fakturownia API Client
https://app.fakturownia.pl/api
"""
from typing import List, Dict, Any, Optional
from datetime import date

import httpx
import structlog

from .base import (
    BaseAccountingClient, Invoice, InvoiceItem, InvoiceType, 
    InvoiceStatus, AccountingDocument
)

logger = structlog.get_logger()


class FakturowniaClient(BaseAccountingClient):
    """
    Fakturownia.pl API client.
    
    Required credentials:
        - api_token: API token from Fakturownia settings
        - subdomain: Your Fakturownia subdomain (e.g., 'mycompany')
    """
    
    @property
    def provider_name(self) -> str:
        return "fakturownia"
    
    @property
    def base_url(self) -> str:
        subdomain = self.credentials.get("subdomain", "app")
        return f"https://{subdomain}.fakturownia.pl"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _get_params(self, **kwargs) -> Dict[str, Any]:
        """Add API token to params"""
        params = {"api_token": self.credentials.get("api_token", "")}
        params.update(kwargs)
        return params
    
    async def verify_connection(self) -> bool:
        """Verify Fakturownia connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/account.json",
                    params=self._get_params(),
                    headers=self._get_headers(),
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.error("Connection verification failed", error=str(e))
            return False
    
    async def get_invoices(
        self,
        invoice_type: InvoiceType = None,
        date_from: date = None,
        date_to: date = None,
        status: InvoiceStatus = None,
        page: int = 1,
        per_page: int = 50
    ) -> List[Invoice]:
        """Fetch invoices from Fakturownia"""
        invoices = []
        
        params = self._get_params(
            page=page,
            per_page=per_page
        )
        
        # Invoice type filter
        if invoice_type == InvoiceType.PURCHASE:
            params["kind"] = "expense"
        elif invoice_type == InvoiceType.SALES:
            params["kind"] = "vat"
        
        # Date filters
        if date_from:
            params["date_from"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["date_to"] = date_to.strftime("%Y-%m-%d")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/invoices.json",
                    params=params,
                    headers=self._get_headers(),
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data:
                        invoice = self._parse_invoice(item)
                        invoices.append(invoice)
        
        except Exception as e:
            self.logger.error("Failed to fetch invoices", error=str(e))
        
        return invoices
    
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get single invoice"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/invoices/{invoice_id}.json",
                    params=self._get_params(),
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_invoice(data)
        
        except Exception as e:
            self.logger.error("Failed to get invoice", invoice_id=invoice_id, error=str(e))
        
        return None
    
    async def get_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """Download invoice PDF"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/invoices/{invoice_id}.pdf",
                    params=self._get_params(),
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Failed to download PDF", invoice_id=invoice_id, error=str(e))
        
        return None
    
    async def get_expense_invoices(
        self,
        date_from: date = None,
        date_to: date = None,
        page: int = 1,
        per_page: int = 50
    ) -> List[Invoice]:
        """Get expense documents from Fakturownia"""
        expenses = []
        
        params = self._get_params(
            page=page,
            per_page=per_page
        )
        
        if date_from:
            params["date_from"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["date_to"] = date_to.strftime("%Y-%m-%d")
        
        try:
            async with httpx.AsyncClient() as client:
                # Get expenses (wydatki)
                response = await client.get(
                    f"{self.base_url}/expenses.json",
                    params=params,
                    headers=self._get_headers(),
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data:
                        expense = self._parse_expense(item)
                        expenses.append(expense)
        
        except Exception as e:
            self.logger.error("Failed to fetch expenses", error=str(e))
        
        return expenses
    
    def _parse_invoice(self, data: Dict) -> Invoice:
        """Parse Fakturownia invoice response"""
        items = []
        for pos in data.get("positions", []):
            items.append(InvoiceItem(
                name=pos.get("name", ""),
                quantity=float(pos.get("quantity", 1)),
                unit=pos.get("quantity_unit", "szt"),
                unit_price_net=float(pos.get("total_price_net", 0)) / float(pos.get("quantity", 1) or 1),
                vat_rate=float(pos.get("tax", 23)),
            ))
        
        # Determine invoice type from 'kind'
        kind = data.get("kind", "")
        if kind in ["expense", "kw", "receipt"]:
            inv_type = InvoiceType.PURCHASE
        elif kind in ["correction", "correction_note"]:
            inv_type = InvoiceType.CORRECTION
        elif kind == "proforma":
            inv_type = InvoiceType.PROFORMA
        else:
            inv_type = InvoiceType.SALES
        
        return Invoice(
            id=str(data.get("id", "")),
            number=data.get("number", ""),
            invoice_type=inv_type,
            status=self._map_status(data.get("status", "")),
            issue_date=self._parse_date(data.get("issue_date")),
            sale_date=self._parse_date(data.get("sell_date")),
            due_date=self._parse_date(data.get("payment_to")),
            seller_name=data.get("seller_name", ""),
            seller_nip=data.get("seller_tax_no", ""),
            buyer_name=data.get("buyer_name", ""),
            buyer_nip=data.get("buyer_tax_no", ""),
            items=items,
            net_amount=float(data.get("price_net", 0)),
            vat_amount=float(data.get("price_tax", 0)),
            gross_amount=float(data.get("price_gross", 0)),
            currency=data.get("currency", "PLN"),
            payment_method=data.get("payment_type", ""),
            bank_account=data.get("seller_bank_account", ""),
            is_paid=data.get("status") == "paid",
            pdf_url=data.get("view_url"),
            raw_data=data
        )
    
    def _parse_expense(self, data: Dict) -> Invoice:
        """Parse Fakturownia expense response"""
        return Invoice(
            id=str(data.get("id", "")),
            number=data.get("number", ""),
            invoice_type=InvoiceType.PURCHASE,
            status=InvoiceStatus.ISSUED,
            issue_date=self._parse_date(data.get("issue_date")),
            seller_name=data.get("name", ""),
            seller_nip=data.get("seller_tax_no", ""),
            net_amount=float(data.get("price_net", 0)),
            vat_amount=float(data.get("price_tax", 0)),
            gross_amount=float(data.get("price_gross", 0)),
            currency=data.get("currency", "PLN"),
            notes=data.get("description", ""),
            raw_data=data
        )
    
    def _map_status(self, status: str) -> InvoiceStatus:
        """Map Fakturownia status"""
        mapping = {
            "issued": InvoiceStatus.ISSUED,
            "sent": InvoiceStatus.SENT,
            "paid": InvoiceStatus.PAID,
            "partial": InvoiceStatus.ISSUED,
            "rejected": InvoiceStatus.CANCELLED,
        }
        return mapping.get(status, InvoiceStatus.DRAFT)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            return None
