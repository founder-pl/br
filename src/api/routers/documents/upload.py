"""
Documents Upload - Upload and OCR processing
"""
import json
import uuid
from pathlib import Path
from typing import Optional

import httpx
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db, get_db_context
from ...config import settings
from ...document_classifier import classify_and_extract
from .models import DocumentUploadResponse

logger = structlog.get_logger()
router = APIRouter()

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(default="00000000-0000-0000-0000-000000000001"),
    document_type: str = Query(default="invoice"),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document for OCR processing."""
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "application/pdf"}
    
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
    
    doc_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix.lower()
    file_path = UPLOAD_DIR / f"{doc_id}{file_ext}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    await db.execute(
        text("""
        INSERT INTO read_models.documents 
        (id, project_id, document_type, filename, original_path, file_size, mime_type, ocr_status)
        VALUES (:id, :project_id, :doc_type, :filename, :path, :size, :mime, 'pending')
        """),
        {
            "id": doc_id, "project_id": project_id, "doc_type": document_type,
            "filename": file.filename, "path": str(file_path),
            "size": len(content), "mime": file.content_type
        }
    )
    
    background_tasks.add_task(process_document_ocr, doc_id, str(file_path), document_type)
    logger.info("Document uploaded", doc_id=doc_id, filename=file.filename)
    
    return DocumentUploadResponse(
        document_id=doc_id, filename=file.filename,
        status="pending", message="Document uploaded and queued for OCR processing"
    )


def detect_invoice_type(extracted_data: dict, our_nip: str = "5881918662") -> str:
    """Detect if invoice is a cost (expense) or revenue invoice."""
    seller_nip = (extracted_data.get('vendor_nip') or extracted_data.get('seller_nip') or 
                  extracted_data.get('nip_sprzedawcy') or extracted_data.get('nip_wystawcy') or '')
    buyer_nip = (extracted_data.get('buyer_nip') or extracted_data.get('client_nip') or 
                 extracted_data.get('nip_nabywcy') or extracted_data.get('nip_kupujacego') or '')
    
    def clean_nip(nip):
        return ''.join(c for c in str(nip) if c.isdigit()) if nip else ''
    
    seller_clean, buyer_clean, our_clean = clean_nip(seller_nip), clean_nip(buyer_nip), clean_nip(our_nip)
    
    if seller_clean == our_clean:
        return 'revenue'
    if buyer_clean == our_clean:
        return 'expense'
    return 'expense'


async def create_expense_from_document(doc_id: str, extracted_data: dict, doc_type: str):
    """Create expense or revenue record from OCR-extracted document data"""
    from decimal import Decimal
    
    try:
        if 'extracted_data' in extracted_data and isinstance(extracted_data['extracted_data'], dict):
            extracted_data = {**extracted_data, **extracted_data['extracted_data']}
        
        invoice_type = detect_invoice_type(extracted_data)
        
        def parse_amount(val):
            if val is None:
                return Decimal('0')
            if isinstance(val, (int, float)):
                return Decimal(str(val))
            if isinstance(val, str):
                cleaned = val.replace('PLN', '').replace('zł', '').replace(' ', '').replace(',', '.').strip()
                try:
                    return Decimal(cleaned) if cleaned else Decimal('0')
                except:
                    return Decimal('0')
            return Decimal('0')
        
        gross = parse_amount(extracted_data.get('gross_amount') or extracted_data.get('total') or 0)
        net = parse_amount(extracted_data.get('net_amount') or extracted_data.get('netto') or gross)
        vat = parse_amount(extracted_data.get('vat_amount') or extracted_data.get('vat') or 0)
        
        if gross == 0 and net == 0:
            logger.warning("No amounts found in document", doc_id=doc_id)
            return
        
        async with get_db_context() as db:
            result = await db.execute(text("SELECT project_id FROM read_models.documents WHERE id = :id"), {"id": doc_id})
            row = result.fetchone()
            project_id = str(row[0]) if row else "00000000-0000-0000-0000-000000000001"
        
        expense_id = str(uuid.uuid4())
        
        def get_str_field(val):
            if val is None:
                return None
            if isinstance(val, dict):
                return val.get('raw') or val.get('cleaned') or val.get('value') or str(val)
            return str(val) if val else None
        
        invoice_number = get_str_field(extracted_data.get('invoice_number') or extracted_data.get('numer_faktury'))
        invoice_date_raw = extracted_data.get('invoice_date') or extracted_data.get('data_wystawienia')
        vendor_name = get_str_field(extracted_data.get('vendor_name') or extracted_data.get('seller_name'))
        vendor_nip = get_str_field(extracted_data.get('vendor_nip') or extracted_data.get('seller_nip'))
        
        invoice_date = None
        if invoice_date_raw:
            from datetime import datetime as dt
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y']:
                try:
                    invoice_date = dt.strptime(str(invoice_date_raw), fmt).date()
                    break
                except:
                    continue
        
        currency = 'PLN'
        raw_currency = extracted_data.get('currency') or extracted_data.get('waluta') or 'PLN'
        if isinstance(raw_currency, str):
            currency_map = {'zł': 'PLN', 'złotych': 'PLN', '$': 'USD', '€': 'EUR'}
            currency = currency_map.get(raw_currency.lower(), raw_currency.upper())
            if currency not in ('PLN', 'USD', 'EUR', 'GBP', 'CHF'):
                currency = 'PLN'
        
        async with get_db_context() as db:
            if invoice_type == 'revenue':
                client_name = get_str_field(extracted_data.get('buyer_name') or extracted_data.get('nabywca'))
                client_nip = get_str_field(extracted_data.get('buyer_nip') or extracted_data.get('nip_nabywcy'))
                
                await db.execute(
                    text("""
                    INSERT INTO read_models.revenues 
                    (id, project_id, document_id, invoice_number, invoice_date, 
                     client_name, client_nip, net_amount, vat_amount, gross_amount, currency, ip_description)
                    VALUES (:id, :project_id, :document_id, :invoice_number, :invoice_date,
                            :client_name, :client_nip, :net_amount, :vat_amount, :gross_amount, :currency, :ip_description)
                    """),
                    {"id": expense_id, "project_id": project_id, "document_id": doc_id,
                     "invoice_number": invoice_number, "invoice_date": invoice_date,
                     "client_name": client_name, "client_nip": client_nip,
                     "net_amount": float(net), "vat_amount": float(vat), "gross_amount": float(gross),
                     "currency": currency, "ip_description": "Przychód z projektu B+R"}
                )
                logger.info("Revenue created from document", revenue_id=expense_id, doc_id=doc_id)
            else:
                await db.execute(
                    text("""
                    INSERT INTO read_models.expenses 
                    (id, project_id, document_id, invoice_number, invoice_date, 
                     vendor_name, vendor_nip, net_amount, vat_amount, gross_amount, 
                     currency, expense_category, status, br_qualified, br_deduction_rate)
                    VALUES (:id, :project_id, :document_id, :invoice_number, :invoice_date,
                            :vendor_name, :vendor_nip, :net_amount, :vat_amount, :gross_amount,
                            :currency, :expense_category, 'draft', false, 1.0)
                    """),
                    {"id": expense_id, "project_id": project_id, "document_id": doc_id,
                     "invoice_number": invoice_number, "invoice_date": invoice_date,
                     "vendor_name": vendor_name, "vendor_nip": vendor_nip,
                     "net_amount": float(net), "vat_amount": float(vat), "gross_amount": float(gross),
                     "currency": currency, "expense_category": doc_type}
                )
                logger.info("Expense created from document", expense_id=expense_id, doc_id=doc_id)
                
                from ..expenses.classification import classify_expense_with_llm
                import asyncio
                asyncio.create_task(classify_expense_with_llm(expense_id))
        
    except Exception as e:
        logger.error("Failed to create expense from document", doc_id=doc_id, error=str(e))


async def process_document_ocr(doc_id: str, file_path: str, document_type: str):
    """Background task to process document with OCR service"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, 'rb') as f:
                ext = Path(file_path).suffix.lower()
                mime_types = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
                mime_type = mime_types.get(ext, 'application/octet-stream')
                files = {'file': (Path(file_path).name, f, mime_type)}
                params = {'engine': 'paddleocr', 'language': 'pol', 'dpi': 300, 'extract_data': True, 'document_type': document_type}
                response = await client.post(f"{settings.OCR_SERVICE_URL}/ocr/upload", files=files, params=params)
        
        if response.status_code == 200:
            result = response.json()
            ocr_text = result.get('text', '')
            
            classification = classify_and_extract(ocr_text, document_type)
            final_extracted_data = {
                **result.get('extracted_data', {}),
                **classification['extracted_fields'],
                '_detected_type': classification['document_type'],
                '_detection_confidence': classification['detection_confidence']
            }
            
            async with get_db_context() as db:
                await db.execute(
                    text("""
                    UPDATE read_models.documents 
                    SET ocr_status = 'completed', ocr_confidence = :confidence, ocr_text = :text,
                        document_type = :doc_type, extracted_data = CAST(:data AS jsonb), updated_at = NOW()
                    WHERE id = :id
                    """),
                    {"id": doc_id, "confidence": result.get('confidence'), "text": ocr_text,
                     "doc_type": classification['document_type'], "data": json.dumps(final_extracted_data)}
                )
            
            logger.info("OCR completed", doc_id=doc_id, detected_type=classification['document_type'])
            
            if classification['document_type'] in ('invoice', 'faktura', 'receipt', 'paragon'):
                await create_expense_from_document(doc_id, final_extracted_data, classification['document_type'])
        else:
            raise Exception(f"OCR service error: {response.status_code}")
            
    except Exception as e:
        logger.error("OCR processing failed", doc_id=doc_id, error=str(e))
        async with get_db_context() as db:
            await db.execute(
                text("UPDATE read_models.documents SET ocr_status = 'failed', validation_errors = CAST(:errors AS jsonb), updated_at = NOW() WHERE id = :id"),
                {"id": doc_id, "errors": json.dumps([str(e)])}
            )
