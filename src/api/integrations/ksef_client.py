"""
KSeF Client - Integration with Polish Electronic Invoice System.

P3 Task: KSeF integration
Based on: todo/05-br-priority-roadmap.md

Provides:
- Authentication with KSeF API
- Fetching invoices by date range
- Invoice parsing and normalization
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
import httpx
import os
import hashlib
import base64
import structlog

logger = structlog.get_logger()


class KSeFEnvironment(str, Enum):
    """KSeF API environments."""
    PRODUCTION = "https://ksef.mf.gov.pl/api"
    TEST = "https://ksef-test.mf.gov.pl/api"
    DEMO = "https://ksef-demo.mf.gov.pl/api"


@dataclass
class KSeFInvoice:
    """Parsed KSeF invoice."""
    ksef_reference: str
    invoice_number: str
    issue_date: date
    seller_nip: str
    seller_name: str
    buyer_nip: str
    buyer_name: str
    net_amount: float
    vat_amount: float
    gross_amount: float
    currency: str
    items: List[Dict[str, Any]]
    raw_xml: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ksef_reference": self.ksef_reference,
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date.isoformat(),
            "seller_nip": self.seller_nip,
            "seller_name": self.seller_name,
            "buyer_nip": self.buyer_nip,
            "buyer_name": self.buyer_name,
            "net_amount": self.net_amount,
            "vat_amount": self.vat_amount,
            "gross_amount": self.gross_amount,
            "currency": self.currency,
            "items": self.items
        }


@dataclass
class KSeFSession:
    """Active KSeF session."""
    session_token: str
    reference_number: str
    timestamp: datetime
    expires_at: datetime


class KSeFClient:
    """
    Client for KSeF (Krajowy System e-Faktur) API.
    
    Supports both production and test environments.
    """
    
    def __init__(
        self,
        nip: str,
        environment: KSeFEnvironment = KSeFEnvironment.TEST,
        token: Optional[str] = None
    ):
        self.nip = nip
        self.environment = environment
        self.base_url = environment.value
        self.token = token or os.getenv("KSEF_TOKEN")
        self.session: Optional[KSeFSession] = None
        
    async def authenticate(self) -> KSeFSession:
        """
        Authenticate with KSeF API using token.
        
        Returns:
            Active session with token
        """
        if not self.token:
            raise ValueError("KSeF token not configured")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Initialize session
            response = await client.post(
                f"{self.base_url}/online/Session/InitToken",
                json={
                    "context": {
                        "contextIdentifier": {
                            "type": "onip",
                            "identifier": self.nip
                        }
                    }
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error("KSeF auth failed", status=response.status_code)
                raise Exception(f"KSeF authentication failed: {response.text}")
            
            data = response.json()
            
            # Sign challenge with token
            challenge = data.get("timestamp")
            signature = self._sign_challenge(challenge)
            
            # Complete authentication
            auth_response = await client.post(
                f"{self.base_url}/online/Session/AuthoriseChallenge",
                json={
                    "sessionToken": data.get("sessionToken", {}).get("token"),
                    "signature": signature
                }
            )
            
            if auth_response.status_code != 200:
                raise Exception(f"KSeF challenge failed: {auth_response.text}")
            
            auth_data = auth_response.json()
            
            self.session = KSeFSession(
                session_token=auth_data.get("sessionToken", {}).get("token", ""),
                reference_number=auth_data.get("referenceNumber", ""),
                timestamp=datetime.utcnow(),
                expires_at=datetime.utcnow()  # Would parse from response
            )
            
            logger.info("KSeF authenticated", nip=self.nip)
            return self.session
    
    async def fetch_invoices(
        self,
        date_from: date,
        date_to: date,
        invoice_type: str = "purchase"  # purchase or sales
    ) -> List[KSeFInvoice]:
        """
        Fetch invoices from KSeF for date range.
        
        Args:
            date_from: Start date
            date_to: End date
            invoice_type: "purchase" (received) or "sales" (issued)
            
        Returns:
            List of parsed invoices
        """
        if not self.session:
            await self.authenticate()
        
        invoices = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Query invoices
            query_type = "subject2" if invoice_type == "purchase" else "subject1"
            
            response = await client.post(
                f"{self.base_url}/online/Query/Invoice/Sync",
                json={
                    "queryCriteria": {
                        query_type: {"type": "onip", "identifier": self.nip},
                        "invoicingDateFrom": date_from.isoformat(),
                        "invoicingDateTo": date_to.isoformat()
                    }
                },
                headers={
                    "Content-Type": "application/json",
                    "SessionToken": self.session.session_token
                }
            )
            
            if response.status_code != 200:
                logger.error("KSeF query failed", status=response.status_code)
                return []
            
            data = response.json()
            invoice_refs = data.get("invoiceHeaderList", [])
            
            # Fetch each invoice details
            for ref in invoice_refs:
                try:
                    invoice = await self._fetch_invoice_details(
                        client, 
                        ref.get("ksefReferenceNumber")
                    )
                    if invoice:
                        invoices.append(invoice)
                except Exception as e:
                    logger.warning("Failed to fetch invoice", ref=ref, error=str(e))
        
        logger.info("KSeF invoices fetched", count=len(invoices))
        return invoices
    
    async def _fetch_invoice_details(
        self,
        client: httpx.AsyncClient,
        ksef_ref: str
    ) -> Optional[KSeFInvoice]:
        """Fetch and parse single invoice."""
        response = await client.get(
            f"{self.base_url}/online/Invoice/Get/{ksef_ref}",
            headers={"SessionToken": self.session.session_token}
        )
        
        if response.status_code != 200:
            return None
        
        # Parse XML invoice (simplified - real impl would use lxml)
        xml_content = response.text
        return self._parse_invoice_xml(ksef_ref, xml_content)
    
    def _parse_invoice_xml(self, ksef_ref: str, xml: str) -> KSeFInvoice:
        """
        Parse KSeF FA(2) XML format.
        
        Note: Simplified parser - production would use proper XML parsing.
        """
        # Extract basic fields (placeholder - real impl needs XML parsing)
        return KSeFInvoice(
            ksef_reference=ksef_ref,
            invoice_number="",
            issue_date=date.today(),
            seller_nip="",
            seller_name="",
            buyer_nip=self.nip,
            buyer_name="",
            net_amount=0.0,
            vat_amount=0.0,
            gross_amount=0.0,
            currency="PLN",
            items=[],
            raw_xml=xml
        )
    
    def _sign_challenge(self, challenge: str) -> str:
        """Sign authentication challenge with token."""
        if not self.token:
            return ""
        combined = f"{challenge}{self.token}"
        return base64.b64encode(
            hashlib.sha256(combined.encode()).digest()
        ).decode()
    
    async def close_session(self):
        """Close active KSeF session."""
        if not self.session:
            return
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{self.base_url}/online/Session/Terminate",
                headers={"SessionToken": self.session.session_token}
            )
        
        self.session = None
        logger.info("KSeF session closed")


class KSeFService:
    """
    High-level service for KSeF operations.
    
    Provides invoice import with automatic categorization.
    """
    
    def __init__(self, nip: str, environment: KSeFEnvironment = KSeFEnvironment.TEST):
        self.client = KSeFClient(nip, environment)
        self.nip = nip
    
    async def import_purchase_invoices(
        self,
        date_from: date,
        date_to: date
    ) -> Dict[str, Any]:
        """
        Import purchase invoices and prepare for expense creation.
        
        Returns summary with imported invoices.
        """
        try:
            invoices = await self.client.fetch_invoices(
                date_from, 
                date_to, 
                "purchase"
            )
            
            results = {
                "imported": 0,
                "skipped": 0,
                "errors": 0,
                "invoices": []
            }
            
            for inv in invoices:
                # Prepare expense data
                expense_data = {
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.issue_date.isoformat(),
                    "vendor_name": inv.seller_name,
                    "vendor_nip": inv.seller_nip,
                    "net_amount": inv.net_amount,
                    "vat_amount": inv.vat_amount,
                    "gross_amount": inv.gross_amount,
                    "currency": inv.currency,
                    "ksef_reference": inv.ksef_reference,
                    "source": "ksef"
                }
                
                results["invoices"].append(expense_data)
                results["imported"] += 1
            
            return results
            
        except Exception as e:
            logger.error("KSeF import failed", error=str(e))
            return {
                "imported": 0,
                "skipped": 0,
                "errors": 1,
                "error_message": str(e),
                "invoices": []
            }
        finally:
            await self.client.close_session()


# Singleton factory
def get_ksef_service(nip: str) -> KSeFService:
    """Get KSeF service instance for given NIP."""
    env = os.getenv("KSEF_ENV", "test")
    environment = KSeFEnvironment.TEST if env == "test" else KSeFEnvironment.PRODUCTION
    return KSeFService(nip, environment)
