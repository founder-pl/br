"""
Documents Extraction - LLM extraction and data sync
"""
import json
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db
from ...config import settings
from .upload import create_expense_from_document

logger = structlog.get_logger()
router = APIRouter()


@router.post("/{document_id}/llm-extract")
async def llm_extract_fields(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Use LLM to extract structured fields from OCR text"""
    result = await db.execute(
        text("SELECT ocr_text, document_type, extracted_data FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    ocr_text = row[0]
    if not ocr_text:
        raise HTTPException(status_code=400, detail="No OCR text available")
    
    prompt = f"""Wyodrębnij dane z faktury/dokumentu. Zwróć TYLKO JSON:
{{
  "invoice_number": "numer faktury",
  "invoice_date": "YYYY-MM-DD",
  "vendor_name": "nazwa sprzedawcy",
  "vendor_nip": "NIP sprzedawcy (10 cyfr)",
  "buyer_name": "nazwa nabywcy",
  "buyer_nip": "NIP nabywcy",
  "net_amount": 0.00,
  "vat_amount": 0.00,
  "gross_amount": 0.00,
  "currency": "PLN",
  "items": ["lista pozycji"]
}}

TEKST DOKUMENTU:
{ocr_text[:4000]}"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 1000
                },
                headers={"Authorization": f"Bearer {settings.SECRET_KEY}"}
            )
        
        if response.status_code == 200:
            llm_result = response.json()
            content = llm_result['choices'][0]['message']['content']
            
            # Parse JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                extracted = json.loads(content[start:end])
            else:
                extracted = {}
            
            # Merge with existing data
            existing = row[2] or {}
            merged = {**existing, **extracted, '_llm_extracted': True}
            
            await db.execute(
                text("UPDATE read_models.documents SET extracted_data = CAST(:data AS jsonb), updated_at = NOW() WHERE id = :id"),
                {"id": document_id, "data": json.dumps(merged)}
            )
            await db.commit()
            
            logger.info("LLM extraction completed", document_id=document_id)
            return {"status": "extracted", "data": extracted}
        else:
            raise HTTPException(status_code=500, detail="LLM service error")
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")
    except Exception as e:
        logger.error("LLM extraction failed", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/re-extract")
async def re_extract_document_data(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Re-extract data from document and update/create expense"""
    result = await db.execute(
        text("SELECT extracted_data, document_type FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    extracted_data = row[0] or {}
    doc_type = row[1] or 'invoice'
    
    await create_expense_from_document(document_id, extracted_data, doc_type)
    
    logger.info("Document data re-extracted", document_id=document_id)
    return {"status": "re-extracted", "document_id": document_id}


@router.post("/sync-expenses")
async def sync_expenses_from_documents(
    project_id: Optional[str] = Query(default="00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db)
):
    """Sync expenses from all processed documents that don't have expenses yet"""
    result = await db.execute(
        text("""
            SELECT d.id, d.extracted_data, d.document_type
            FROM read_models.documents d
            LEFT JOIN read_models.expenses e ON e.document_id = d.id
            LEFT JOIN read_models.revenues r ON r.document_id = d.id
            WHERE d.project_id = :project_id
              AND d.ocr_status = 'completed'
              AND e.id IS NULL
              AND r.id IS NULL
        """),
        {"project_id": project_id}
    )
    rows = result.fetchall()
    
    created = 0
    errors = 0
    for row in rows:
        try:
            await create_expense_from_document(str(row[0]), row[1] or {}, row[2] or 'invoice')
            created += 1
        except Exception as e:
            logger.error("Failed to create expense from document", doc_id=str(row[0]), error=str(e))
            errors += 1
    
    logger.info("Expenses synced from documents", created=created, errors=errors)
    return {"status": "synced", "created": created, "errors": errors}


@router.get("/{document_id}/check-duplicates")
async def check_document_duplicates(document_id: str, db: AsyncSession = Depends(get_db)):
    """Check for potential duplicate documents"""
    result = await db.execute(
        text("SELECT extracted_data, project_id FROM read_models.documents WHERE id = :id"),
        {"id": document_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    extracted = row[0] or {}
    project_id = row[1]
    
    invoice_number = extracted.get('invoice_number') or extracted.get('numer_faktury')
    vendor_nip = extracted.get('vendor_nip') or extracted.get('nip_sprzedawcy')
    
    if not invoice_number:
        return {"duplicates": [], "message": "No invoice number to check"}
    
    # Check for duplicates
    query = """
        SELECT d.id, d.filename, d.extracted_data, d.created_at
        FROM read_models.documents d
        WHERE d.project_id = :project_id
          AND d.id != :doc_id
          AND d.ocr_status = 'completed'
    """
    result = await db.execute(text(query), {"project_id": project_id, "doc_id": document_id})
    
    duplicates = []
    for r in result.fetchall():
        other_data = r[2] or {}
        other_invoice = other_data.get('invoice_number') or other_data.get('numer_faktury')
        other_nip = other_data.get('vendor_nip') or other_data.get('nip_sprzedawcy')
        
        if other_invoice and other_invoice == invoice_number:
            duplicates.append({
                "document_id": str(r[0]),
                "filename": r[1],
                "invoice_number": other_invoice,
                "vendor_nip": other_nip,
                "created_at": r[3].isoformat() if r[3] else None,
                "match_type": "invoice_number"
            })
    
    return {"duplicates": duplicates, "checked_invoice": invoice_number}
