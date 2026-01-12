"""
wFirma and InFakt API Clients
"""
from typing import List, Dict, Any, Optional
from datetime import date

import httpx
import structlog

from .base import (
    BaseAccountingClient, Invoice, InvoiceItem, InvoiceType, 
    InvoiceStatus
)

logger = structlog.get_logger()


class WFirmaClient(BaseAccountingClient):
    """
    wFirma.pl API client.
    
    Required credentials:
        - access_key: API access key
        - secret_key: API secret key
        - company_id: Company ID in wFirma
    """
    
    BASE_URL = "https://api2.wfirma.pl"
    
    @property
    def provider_name(self) -> str:
        return "wfirma"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "accessKey": self.credentials.get("access_key", ""),
            "secretKey": self.credentials.get("secret_key", ""),
            "appKey": self.credentials.get("app_key", "br-system"),
            "Content-Type": "application/json"
        }
    
    async def verify_connection(self) -> bool:
        """Verify wFirma connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/companies/get",
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
        """Fetch invoices from wFirma"""
        invoices = []
        
        # Build request body
        body = {
            "page": page,
            "limit": per_page,
        }
        
        conditions = []
        if date_from:
            conditions.append({
                "field": "date",
                "operator": ">=",
                "value": date_from.strftime("%Y-%m-%d")
            })
        if date_to:
            conditions.append({
                "field": "date",
                "operator": "<=",
                "value": date_to.strftime("%Y-%m-%d")
            })
        
        if conditions:
            body["conditions"] = {"and": conditions}
        
        # Choose endpoint based on invoice type
        if invoice_type == InvoiceType.PURCHASE:
            endpoint = "/expenses/find"
        else:
            endpoint = "/invoices/find"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self._get_headers(),
                    json=body,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("invoices", data.get("expenses", [])):
                        invoice = self._parse_invoice(item, invoice_type or InvoiceType.SALES)
                        invoices.append(invoice)
        
        except Exception as e:
            self.logger.error("Failed to fetch invoices", error=str(e))
        
        return invoices
    
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get single invoice"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/invoices/get/{invoice_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_invoice(data.get("invoice", {}), InvoiceType.SALES)
        
        except Exception as e:
            self.logger.error("Failed to get invoice", invoice_id=invoice_id, error=str(e))
        
        return None
    
    async def get_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """Download invoice PDF"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/invoices/download/{invoice_id}",
                    headers=self._get_headers(),
                    params={"format": "pdf"},
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Failed to download PDF", invoice_id=invoice_id, error=str(e))
        
        return None
    
    def _parse_invoice(self, data: Dict, invoice_type: InvoiceType) -> Invoice:
        """Parse wFirma response"""
        items = []
        for pos in data.get("invoicecontents", []):
            items.append(InvoiceItem(
                name=pos.get("name", ""),
                quantity=float(pos.get("count", 1)),
                unit=pos.get("unit", "szt"),
                unit_price_net=float(pos.get("price", 0)),
                vat_rate=float(pos.get("vat", "23").replace("%", "")),
            ))
        
        return Invoice(
            id=str(data.get("id", "")),
            number=data.get("fullnumber", data.get("number", "")),
            invoice_type=invoice_type,
            status=InvoiceStatus.ISSUED,
            issue_date=self._parse_date(data.get("date")),
            sale_date=self._parse_date(data.get("disposaldate")),
            due_date=self._parse_date(data.get("paymentdate")),
            seller_name=data.get("company", {}).get("name", ""),
            seller_nip=data.get("company", {}).get("nip", ""),
            buyer_name=data.get("contractor", {}).get("name", ""),
            buyer_nip=data.get("contractor", {}).get("nip", ""),
            items=items,
            net_amount=float(data.get("netto", 0)),
            vat_amount=float(data.get("tax", 0)),
            gross_amount=float(data.get("brutto", data.get("total", 0))),
            currency=data.get("currency", "PLN"),
            payment_method=data.get("paymentmethod", ""),
            is_paid=data.get("alreadypaid", 0) >= float(data.get("total", 0)),
            raw_data=data
        )
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            return None


class InFaktClient(BaseAccountingClient):
    """
    InFakt.pl API client.
    
    Required credentials:
        - api_key: API key from InFakt settings
    """
    
    BASE_URL = "https://api.infakt.pl/v3"
    
    @property
    def provider_name(self) -> str:
        return "infakt"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-inFakt-ApiKey": self.credentials.get("api_key", ""),
            "Content-Type": "application/json"
        }
    
    async def verify_connection(self) -> bool:
        """Verify InFakt connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/account.json",
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
        """Fetch invoices from InFakt"""
        invoices = []
        
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if date_from:
            params["q[invoice_date_gteq]"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["q[invoice_date_lteq]"] = date_to.strftime("%Y-%m-%d")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/invoices.json",
                    headers=self._get_headers(),
                    params=params,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("entities", []):
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
                    f"{self.BASE_URL}/invoices/{invoice_id}.json",
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
                    f"{self.BASE_URL}/invoices/{invoice_id}.pdf",
                    headers=self._get_headers(),
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Failed to download PDF", invoice_id=invoice_id, error=str(e))
        
        return None
    
    def _parse_invoice(self, data: Dict) -> Invoice:
        """Parse InFakt response"""
        items = []
        for pos in data.get("services", []):
            items.append(InvoiceItem(
                name=pos.get("name", ""),
                quantity=float(pos.get("quantity", 1)),
                unit=pos.get("unit", "szt"),
                unit_price_net=float(pos.get("unit_net_price", 0)),
                vat_rate=float(pos.get("tax_symbol", "23").replace("%", "")),
                pkwiu=pos.get("pkwiu"),
                gtu=pos.get("gtu_code")
            ))
        
        return Invoice(
            id=str(data.get("id", "")),
            number=data.get("number", ""),
            invoice_type=InvoiceType.SALES,
            status=self._map_status(data.get("status", "")),
            issue_date=self._parse_date(data.get("invoice_date")),
            sale_date=self._parse_date(data.get("sale_date")),
            due_date=self._parse_date(data.get("payment_date")),
            seller_name=data.get("seller", {}).get("name", ""),
            seller_nip=data.get("seller", {}).get("tax_id", ""),
            buyer_name=data.get("client", {}).get("name", ""),
            buyer_nip=data.get("client", {}).get("tax_id", ""),
            items=items,
            net_amount=float(data.get("net_price", 0)),
            vat_amount=float(data.get("tax_price", 0)),
            gross_amount=float(data.get("gross_price", 0)),
            currency=data.get("currency", "PLN"),
            payment_method=data.get("payment_method", ""),
            bank_account=data.get("bank_account", ""),
            is_paid=data.get("paid") == True,
            paid_date=self._parse_date(data.get("paid_date")),
            raw_data=data
        )
    
    def _map_status(self, status: str) -> InvoiceStatus:
        mapping = {
            "draft": InvoiceStatus.DRAFT,
            "sent": InvoiceStatus.SENT,
            "paid": InvoiceStatus.PAID,
            "printed": InvoiceStatus.ISSUED,
        }
        return mapping.get(status, InvoiceStatus.DRAFT)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            return None
