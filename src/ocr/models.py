"""
OCR Data Models
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """OCR processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document types"""
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    OTHER = "other"


class OCRResult(BaseModel):
    """OCR processing result"""
    text: str
    confidence: float = Field(ge=0, le=1)
    boxes: Optional[List[Dict[str, Any]]] = None
    raw_data: Optional[Any] = None


class ExtractedInvoiceData(BaseModel):
    """Structured invoice data"""
    document_type: DocumentType = DocumentType.INVOICE
    
    # Invoice identification
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    payment_due_date: Optional[str] = None
    
    # Parties
    vendor_name: Optional[str] = None
    vendor_nip: Optional[Dict[str, Any]] = None
    buyer_nip: Optional[Dict[str, Any]] = None
    
    # Amounts
    net_amount: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    currency: str = "PLN"
    
    # Additional data
    bank_account: Optional[str] = None
    dates: Optional[List[str]] = None
    nip_numbers: Optional[List[Dict[str, Any]]] = None
    
    # Extraction metadata
    extraction_confidence: float = 0.0
    fields_found: int = 0
    fields_validated: int = 0
    raw_text_length: int = 0
