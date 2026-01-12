"""
iFirma API Client
https://www.ifirma.pl/api
"""
import hashlib
from typing import List, Dict, Any, Optional
from datetime import date
from base64 import b64encode

import httpx
import structlog

from .base import (
    BaseAccountingClient, Invoice, InvoiceItem, InvoiceType, 
    InvoiceStatus, AccountingDocument
)

logger = structlog.get_logger()


class IFirmaClient(BaseAccountingClient):
    """
    iFirma API client for Polish accounting software.
    
    Required credentials:
        - api_key: API key from iFirma panel
        - username: iFirma login (email)
        - company_name: Company name for invoice key
        
    Optional settings:
        - invoice_key: Key for invoice operations
        - expense_key: Key for expense operations
    """
    
    BASE_URL = "https://www.ifirma.pl/iapi"
    
    @property
    def provider_name(self) -> str:
        return "ifirma"
    
    def _get_auth_header(self, key_type: str = "faktura") -> str:
        """
        Generate HMAC authentication header for iFirma API.
        
        Args:
            key_type: 'faktura' for invoices, 'wydatek' for expenses
        """
        username = self.credentials.get("username", "")
        
        if key_type == "faktura":
            key = self.credentials.get("invoice_key", self.credentials.get("api_key", ""))
        else:
            key = self.credentials.get("expense_key", self.credentials.get("api_key", ""))
        
        # iFirma uses HMAC-SHA1
        message = f"{username}:{self.credentials.get('company_name', '')}:{key_type}"
        hmac_hash = hashlib.sha1(f"{message}:{key}".encode()).hexdigest()
        
        auth = b64encode(f"{username}:{hmac_hash}".encode()).decode()
        return f"IAPIS {auth}"
    
    async def verify_connection(self) -> bool:
        """Verify iFirma connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/abonent/miesiacksiegowy.json",
                    headers={
                        "Authentication": self._get_auth_header("abonent"),
                        "Content-Type": "application/json"
                    },
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
        """Fetch invoices from iFirma"""
        invoices = []
        
        # Determine endpoint based on invoice type
        if invoice_type == InvoiceType.PURCHASE:
            endpoint = "/wydatki.json"
            key_type = "wydatek"
        else:
            endpoint = "/faktury.json"
            key_type = "faktura"
        
        params = {}
        if date_from:
            params["dataOd"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["dataDo"] = date_to.strftime("%Y-%m-%d")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}{endpoint}",
                    headers={
                        "Authentication": self._get_auth_header(key_type),
                        "Content-Type": "application/json"
                    },
                    params=params,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("response", {}).get("Rachunki", []):
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
                    f"{self.BASE_URL}/faktury/{invoice_id}.json",
                    headers={
                        "Authentication": self._get_auth_header("faktura"),
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_invoice(data.get("response", {}), InvoiceType.SALES)
        
        except Exception as e:
            self.logger.error("Failed to get invoice", invoice_id=invoice_id, error=str(e))
        
        return None
    
    async def get_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """Download invoice PDF"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/faktury/{invoice_id}.pdf",
                    headers={
                        "Authentication": self._get_auth_header("faktura")
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return response.content
        
        except Exception as e:
            self.logger.error("Failed to download PDF", invoice_id=invoice_id, error=str(e))
        
        return None
    
    def _parse_invoice(self, data: Dict, invoice_type: InvoiceType) -> Invoice:
        """Parse iFirma response to Invoice model"""
        items = []
        for pos in data.get("Pozycje", []):
            items.append(InvoiceItem(
                name=pos.get("Nazwa", ""),
                quantity=float(pos.get("Ilosc", 1)),
                unit=pos.get("Jednostka", "szt"),
                unit_price_net=float(pos.get("CenaNetto", 0)),
                vat_rate=float(pos.get("StawkaVat", 23)),
                pkwiu=pos.get("PKWiU"),
                gtu=pos.get("GTU")
            ))
        
        return Invoice(
            id=str(data.get("Id", "")),
            number=data.get("NumerPelny", data.get("Numer", "")),
            invoice_type=invoice_type,
            status=self._map_status(data.get("Status", "")),
            issue_date=self._parse_date(data.get("DataWystawienia")),
            sale_date=self._parse_date(data.get("DataSprzedazy")),
            due_date=self._parse_date(data.get("TerminPlatnosci")),
            seller_name=data.get("Sprzedawca", {}).get("Nazwa", ""),
            seller_nip=data.get("Sprzedawca", {}).get("NIP", ""),
            buyer_name=data.get("Kontrahent", {}).get("Nazwa", ""),
            buyer_nip=data.get("Kontrahent", {}).get("NIP", ""),
            items=items,
            net_amount=float(data.get("LacznaKwotaNetto", 0)),
            vat_amount=float(data.get("LacznaKwotaVAT", 0)),
            gross_amount=float(data.get("LacznaKwotaBrutto", 0)),
            currency=data.get("Waluta", "PLN"),
            payment_method=data.get("SposobZaplaty", ""),
            is_paid=data.get("CzyZaplacona", False),
            raw_data=data
        )
    
    def _map_status(self, status: str) -> InvoiceStatus:
        """Map iFirma status to InvoiceStatus"""
        mapping = {
            "WYSTAWIONA": InvoiceStatus.ISSUED,
            "WYSLANA": InvoiceStatus.SENT,
            "OPLACONA": InvoiceStatus.PAID,
            "NIEOPLACONA": InvoiceStatus.OVERDUE,
            "ANULOWANA": InvoiceStatus.CANCELLED,
        }
        return mapping.get(status.upper(), InvoiceStatus.DRAFT)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            return None
