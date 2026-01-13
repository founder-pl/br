"""
Documents Router - Upload and OCR processing
"""
import json
import uuid
from datetime import datetime
from typing import Optional, List
from pathlib import Path

import httpx
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
import structlog

from ..database import get_db
from ..config import settings
from ..document_classifier import classify_and_extract

logger = structlog.get_logger()
router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentResponse(BaseModel):
    """Document response model"""
    id: str
    filename: str
    document_type: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    extracted_data: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Upload response"""
    document_id: str
    filename: str
    status: str
    message: str


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(default="00000000-0000-0000-0000-000000000001"),
    document_type: str = Query(default="invoice"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for OCR processing.
    
    Supported formats:
    - Images: PNG, JPG, JPEG, TIFF
    - PDFs: Single and multi-page
    
    The document will be processed with OCR and data extraction in the background.
    """
    # Validate file type
    allowed_types = {
        "image/png", "image/jpeg", "image/jpg", "image/tiff",
        "application/pdf"
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    # Generate document ID
    doc_id = str(uuid.uuid4())
    
    # Save file
    file_ext = Path(file.filename).suffix.lower()
    file_path = UPLOAD_DIR / f"{doc_id}{file_ext}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Insert document record
    await db.execute(
        text("""
        INSERT INTO read_models.documents 
        (id, project_id, document_type, filename, original_path, file_size, mime_type, ocr_status)
        VALUES (:id, :project_id, :doc_type, :filename, :path, :size, :mime, 'pending')
        """),
        {
            "id": doc_id,
            "project_id": project_id,
            "doc_type": document_type,
            "filename": file.filename,
            "path": str(file_path),
            "size": len(content),
            "mime": file.content_type
        }
    )
    
    # Queue OCR processing
    background_tasks.add_task(process_document_ocr, doc_id, str(file_path), document_type)
    
    logger.info("Document uploaded", doc_id=doc_id, filename=file.filename)
    
    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status="pending",
        message="Document uploaded and queued for OCR processing"
    )


async def create_expense_from_document(doc_id: str, extracted_data: dict, doc_type: str):
    """Create expense record from OCR-extracted document data"""
    from ..database import get_db_context
    from decimal import Decimal
    
    try:
        # Handle nested extracted_data structure
        if 'extracted_data' in extracted_data and isinstance(extracted_data['extracted_data'], dict):
            extracted_data = {**extracted_data, **extracted_data['extracted_data']}
        
        # Extract financial data from OCR results
        gross_amount = extracted_data.get('gross_amount') or extracted_data.get('total') or extracted_data.get('kwota_brutto') or 0
        net_amount = extracted_data.get('net_amount') or extracted_data.get('netto') or extracted_data.get('kwota_netto') or gross_amount
        vat_amount = extracted_data.get('vat_amount') or extracted_data.get('vat') or extracted_data.get('kwota_vat') or 0
        
        # Try to parse amounts if they're strings
        def parse_amount(val):
            if val is None:
                return Decimal('0')
            if isinstance(val, (int, float)):
                return Decimal(str(val))
            if isinstance(val, str):
                # Remove currency symbols and whitespace, replace comma with dot
                cleaned = val.replace('PLN', '').replace('zł', '').replace(' ', '').replace(',', '.').strip()
                try:
                    return Decimal(cleaned) if cleaned else Decimal('0')
                except:
                    return Decimal('0')
            return Decimal('0')
        
        gross = parse_amount(gross_amount)
        net = parse_amount(net_amount)
        vat = parse_amount(vat_amount)
        
        # If we have no amounts, skip expense creation
        if gross == 0 and net == 0:
            logger.warning("No amounts found in document, skipping expense creation", doc_id=doc_id)
            return
        
        # Get document's project_id
        async with get_db_context() as db:
            result = await db.execute(
                text("SELECT project_id FROM read_models.documents WHERE id = :id"),
                {"id": doc_id}
            )
            row = result.fetchone()
            project_id = str(row[0]) if row else "00000000-0000-0000-0000-000000000001"
        
        expense_id = str(uuid.uuid4())
        
        # Helper to extract string value from field that may be dict or string
        def get_str_field(val):
            if val is None:
                return None
            if isinstance(val, dict):
                return val.get('raw') or val.get('cleaned') or val.get('value') or str(val)
            return str(val) if val else None
        
        # Extract other fields
        invoice_number = get_str_field(extracted_data.get('invoice_number') or extracted_data.get('numer_faktury') or extracted_data.get('number'))
        invoice_date_raw = extracted_data.get('invoice_date') or extracted_data.get('data_wystawienia') or extracted_data.get('date')
        vendor_name = get_str_field(extracted_data.get('vendor_name') or extracted_data.get('seller_name') or extracted_data.get('sprzedawca') or extracted_data.get('wystawca'))
        vendor_nip = get_str_field(extracted_data.get('vendor_nip') or extracted_data.get('seller_nip') or extracted_data.get('nip_sprzedawcy'))
        
        # Parse date
        invoice_date = None
        if invoice_date_raw:
            from datetime import datetime as dt
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y']:
                try:
                    invoice_date = dt.strptime(str(invoice_date_raw), fmt).date()
                    break
                except:
                    continue
        
        async with get_db_context() as db:
            await db.execute(
                text("""
                INSERT INTO read_models.expenses 
                (id, project_id, document_id, invoice_number, invoice_date, 
                 vendor_name, vendor_nip, net_amount, vat_amount, gross_amount, 
                 currency, expense_category, status, br_qualified, br_deduction_rate)
                VALUES (:id, :project_id, :document_id, :invoice_number, :invoice_date,
                        :vendor_name, :vendor_nip, :net_amount, :vat_amount, :gross_amount,
                        'PLN', :expense_category, 'draft', false, 1.0)
                """),
                {
                    "id": expense_id,
                    "project_id": project_id,
                    "document_id": doc_id,
                    "invoice_number": invoice_number,
                    "invoice_date": invoice_date,
                    "vendor_name": vendor_name,
                    "vendor_nip": vendor_nip,
                    "net_amount": float(net),
                    "vat_amount": float(vat),
                    "gross_amount": float(gross),
                    "expense_category": doc_type
                }
            )
        
        logger.info("Expense created from document", expense_id=expense_id, doc_id=doc_id, gross=float(gross))
        
        # Queue LLM classification for the new expense
        from .expenses import classify_expense_with_llm
        import asyncio
        asyncio.create_task(classify_expense_with_llm(expense_id))
        
    except Exception as e:
        logger.error("Failed to create expense from document", doc_id=doc_id, error=str(e))


async def process_document_ocr(doc_id: str, file_path: str, document_type: str):
    """Background task to process document with OCR service"""
    from ..database import get_db_context
    
    try:
        # Call OCR service
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, 'rb') as f:
                # Determine MIME type from file extension
                ext = Path(file_path).suffix.lower()
                mime_types = {
                    '.pdf': 'application/pdf',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.tiff': 'image/tiff',
                    '.tif': 'image/tiff',
                    '.bmp': 'image/bmp'
                }
                mime_type = mime_types.get(ext, 'application/octet-stream')
                files = {'file': (Path(file_path).name, f, mime_type)}
                params = {
                    'engine': 'paddleocr',
                    'language': 'pol',
                    'dpi': 300,
                    'extract_data': True,
                    'document_type': document_type
                }
                
                response = await client.post(
                    f"{settings.OCR_SERVICE_URL}/ocr/upload",
                    files=files,
                    params=params
                )
        
        if response.status_code == 200:
            result = response.json()
            ocr_text = result.get('text', '')
            
            # Auto-detect document type and extract structured data
            classification = classify_and_extract(ocr_text, document_type)
            detected_type = classification['document_type']
            detection_confidence = classification['detection_confidence']
            extracted_fields = classification['extracted_fields']
            
            # Merge OCR extracted data with classifier extracted data
            final_extracted_data = {
                **result.get('extracted_data', {}),
                **extracted_fields,
                '_detected_type': detected_type,
                '_detection_confidence': detection_confidence
            }
            
            # Update document with OCR results and detected type
            async with get_db_context() as db:
                await db.execute(
                    text("""
                    UPDATE read_models.documents 
                    SET ocr_status = 'completed',
                        ocr_confidence = :confidence,
                        ocr_text = :text,
                        document_type = :doc_type,
                        extracted_data = CAST(:data AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                    """),
                    {
                        "id": doc_id,
                        "confidence": result.get('confidence'),
                        "text": ocr_text,
                        "doc_type": detected_type,
                        "data": json.dumps(final_extracted_data)
                    }
                )
            
            logger.info("OCR completed", doc_id=doc_id, detected_type=detected_type, 
                       confidence=result.get('confidence'), detection_confidence=detection_confidence)
            
            # Auto-create expense record for invoice documents
            if detected_type in ('invoice', 'faktura', 'receipt', 'paragon'):
                await create_expense_from_document(doc_id, final_extracted_data, detected_type)
        else:
            raise Exception(f"OCR service error: {response.status_code}")
            
    except Exception as e:
        logger.error("OCR processing failed", doc_id=doc_id, error=str(e))
        
        async with get_db_context() as db:
            await db.execute(
                text("""
                UPDATE read_models.documents 
                SET ocr_status = 'failed',
                    validation_errors = CAST(:errors AS jsonb),
                    updated_at = NOW()
                WHERE id = :id
                """),
                {
                    "id": doc_id,
                    "errors": json.dumps([str(e)])
                }
            )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get document details"""
    result = await db.execute(
        text("""
        SELECT id, filename, document_type, ocr_status, ocr_confidence, 
               extracted_data, created_at
        FROM read_models.documents 
        WHERE id = :id
        """),
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=str(row[0]),
        filename=row[1],
        document_type=row[2],
        ocr_status=row[3],
        ocr_confidence=row[4],
        extracted_data=row[5],
        created_at=row[6]
    )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    project_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db)
):
    """List documents with optional filtering"""
    query = """
        SELECT id, filename, document_type, ocr_status, ocr_confidence, 
               extracted_data, created_at
        FROM read_models.documents 
        WHERE 1=1
    """
    params = {}
    
    if project_id:
        query += " AND project_id = :project_id"
        params["project_id"] = project_id
    
    if status:
        query += " AND ocr_status = :status"
        params["status"] = status
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    return [
        DocumentResponse(
            id=str(row[0]),
            filename=row[1],
            document_type=row[2],
            ocr_status=row[3],
            ocr_confidence=row[4],
            extracted_data=row[5],
            created_at=row[6]
        )
        for row in rows
    ]


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Reprocess document with OCR"""
    result = await db.execute(
        text("SELECT original_path, document_type FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status
    await db.execute(
        text("UPDATE read_models.documents SET ocr_status = 'pending' WHERE id = :id"),
        {"id": document_id}
    )
    
    # Queue reprocessing
    background_tasks.add_task(process_document_ocr, document_id, row[0], 'auto')
    
    return {"status": "queued", "message": "Document queued for reprocessing"}


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document"""
    # Get file path first
    result = await db.execute(
        text("SELECT original_path FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from database
    await db.execute(
        text("DELETE FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    
    # Try to delete file
    try:
        file_path = Path(row[0])
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning("Could not delete file", path=row[0], error=str(e))
    
    logger.info("Document deleted", doc_id=document_id)
    return {"status": "deleted", "document_id": document_id}


@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    document_type: Optional[str] = None,
    ocr_status: Optional[str] = None,
    extracted_data: Optional[dict] = None
):
    """Update document fields"""
    updates = []
    params = {"id": document_id}
    
    if document_type:
        updates.append("document_type = :doc_type")
        params["doc_type"] = document_type
    
    if ocr_status:
        updates.append("ocr_status = :status")
        params["status"] = ocr_status
    
    if extracted_data is not None:
        updates.append("extracted_data = CAST(:data AS jsonb)")
        params["data"] = json.dumps(extracted_data)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    await db.execute(
        text(f"UPDATE read_models.documents SET {', '.join(updates)} WHERE id = :id"),
        params
    )
    
    return {"status": "updated", "document_id": document_id}


class DocumentDetailResponse(BaseModel):
    """Extended document response with OCR text"""
    id: str
    filename: str
    document_type: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    ocr_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    validation_errors: Optional[list] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


@router.get("/{document_id}/detail", response_model=DocumentDetailResponse)
async def get_document_detail(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get full document details including OCR text"""
    result = await db.execute(
        text("""
        SELECT id, filename, document_type, ocr_status, ocr_confidence, 
               ocr_text, extracted_data, validation_errors, created_at, updated_at
        FROM read_models.documents 
        WHERE id = :id
        """),
        {"id": document_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentDetailResponse(
        id=str(row[0]),
        filename=row[1],
        document_type=row[2],
        ocr_status=row[3],
        ocr_confidence=row[4],
        ocr_text=row[5],
        extracted_data=row[6],
        validation_errors=row[7],
        created_at=row[8],
        updated_at=row[9]
    )


@router.post("/sync-expenses")
async def sync_expenses_from_documents(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create expense records for all completed invoice documents that don't have expenses yet.
    This is useful for retroactively processing already-OCR'd documents.
    """
    # Find completed invoice documents without expenses
    result = await db.execute(
        text("""
        SELECT d.id, d.extracted_data, d.document_type
        FROM read_models.documents d
        LEFT JOIN read_models.expenses e ON e.document_id = d.id
        WHERE d.ocr_status = 'completed'
          AND d.document_type IN ('invoice', 'faktura', 'receipt', 'paragon')
          AND e.id IS NULL
        """)
    )
    rows = result.fetchall()
    
    created = 0
    for row in rows:
        doc_id = str(row[0])
        extracted_data = row[1] or {}
        doc_type = row[2]
        
        background_tasks.add_task(create_expense_from_document, doc_id, extracted_data, doc_type)
        created += 1
    
    logger.info("Sync expenses triggered", documents_count=created)
    
    return {
        "status": "queued",
        "message": f"Queued expense creation for {created} documents",
        "documents_processed": created
    }
