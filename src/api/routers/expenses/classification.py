"""
Expenses Classification - Classification and categorization endpoints
"""
import json
import httpx
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db, get_db_context
from ...config import settings
from .models import ExpenseClassifyRequest, ExpenseResponse
from .crud import get_expense

logger = structlog.get_logger()
router = APIRouter()


@router.put("/{expense_id}/classify", response_model=ExpenseResponse)
async def classify_expense_manually(
    expense_id: str,
    classification: ExpenseClassifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Manually classify expense for B+R or IP Box"""
    updates = []
    params = {"id": expense_id}
    
    if classification.br_qualified is not None:
        updates.append("br_qualified = :br_qualified")
        params["br_qualified"] = classification.br_qualified
    
    if classification.br_category:
        updates.append("br_category = :br_category")
        params["br_category"] = classification.br_category
    
    if classification.br_qualification_reason:
        updates.append("br_qualification_reason = :br_qualification_reason")
        params["br_qualification_reason"] = classification.br_qualification_reason
    
    if classification.br_deduction_rate:
        updates.append("br_deduction_rate = :br_deduction_rate")
        params["br_deduction_rate"] = classification.br_deduction_rate
    
    if classification.ip_qualified is not None:
        updates.append("ip_qualified = :ip_qualified")
        params["ip_qualified"] = classification.ip_qualified
    
    if classification.ip_category:
        updates.append("ip_category = :ip_category")
        params["ip_category"] = classification.ip_category
    
    if classification.nexus_category:
        updates.append("nexus_category = :nexus_category")
        params["nexus_category"] = classification.nexus_category
    
    if updates:
        updates.append("manual_override = true")
        updates.append("status = 'classified'")
        updates.append("updated_at = NOW()")
        
        await db.execute(
            text(f"UPDATE read_models.expenses SET {', '.join(updates)} WHERE id = :id"),
            params
        )
        
        # Record event in event store (CQRS)
        from ...cqrs.events import EventStore, EventType, DomainEvent
        event_store = EventStore(db)
        await event_store.ensure_table_exists()
        
        event_type = EventType.EXPENSE_BR_QUALIFIED if classification.br_qualified else EventType.EXPENSE_BR_DISQUALIFIED
        event = DomainEvent(
            event_type=event_type,
            aggregate_id=expense_id,
            aggregate_type="expense",
            data={
                "br_category": classification.br_category,
                "br_qualified": classification.br_qualified,
                "br_deduction_rate": classification.br_deduction_rate,
                "reason": classification.br_qualification_reason or "manual_classification"
            }
        )
        await event_store.append(event)
    
    logger.info("Expense classified manually", expense_id=expense_id)
    return await get_expense(expense_id, db)


@router.post("/{expense_id}/auto-classify")
async def trigger_auto_classification(
    expense_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger automatic LLM classification"""
    result = await db.execute(
        text("SELECT id FROM read_models.expenses WHERE id = :id"),
        {"id": expense_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    background_tasks.add_task(classify_expense_with_llm, expense_id)
    return {"status": "queued", "message": "Classification queued"}


@router.post("/{expense_id}/generate-justification")
async def generate_expense_justification(
    expense_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate individualized B+R justification for an expense using LLM."""
    from ...services.justification_generator import (
        get_justification_generator, ExpenseContext, ProjectContext
    )
    
    result = await db.execute(
        text("""
            SELECT e.invoice_number, e.invoice_date, e.gross_amount, e.currency,
                   e.vendor_name, e.vendor_nip, e.expense_category,
                   p.name as project_name, p.description as project_desc,
                   d.ocr_text, e.br_qualification_reason
            FROM read_models.expenses e
            JOIN read_models.projects p ON e.project_id = p.id
            LEFT JOIN read_models.documents d ON e.document_id = d.id
            WHERE e.id = :id
        """),
        {"id": expense_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    expense_ctx = ExpenseContext(
        invoice_number=row[0] or "brak",
        invoice_date=str(row[1]) if row[1] else None,
        amount=float(row[2] or 0),
        currency=row[3] or "PLN",
        vendor_name=row[4],
        vendor_nip=row[5],
        category=row[6],
        description=row[10],
        ocr_text=row[9]
    )
    
    project_ctx = ProjectContext(
        name=row[7] or "Projekt B+R",
        description=row[8]
    )
    
    generator = get_justification_generator()
    result = await generator.generate_justification(expense_ctx, project_ctx)
    
    await db.execute(
        text("""
            UPDATE read_models.expenses SET
                br_qualification_reason = :justification,
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": expense_id, "justification": result.justification}
    )
    await db.commit()
    
    logger.info("Justification generated", expense_id=expense_id, words=result.word_count)
    
    return {
        "expense_id": expense_id,
        "justification": result.justification,
        "confidence": result.confidence,
        "br_category_suggestion": result.br_category_suggestion,
        "keywords_used": result.keywords_used,
        "word_count": result.word_count
    }


async def classify_expense_with_llm(expense_id: str):
    """Background task to classify expense using LLM"""
    try:
        async with get_db_context() as db:
            result = await db.execute(
                text("""
                    SELECT e.*, d.ocr_text, d.extracted_data
                    FROM read_models.expenses e
                    LEFT JOIN read_models.documents d ON e.document_id = d.id
                    WHERE e.id = :id
                """),
                {"id": expense_id}
            )
            row = result.fetchone()
            
            if not row:
                return
        
        prompt = _build_classification_prompt(row)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/v1/chat/completions",
                json={
                    "model": "br-classifier",
                    "messages": [
                        {"role": "system", "content": _get_br_classifier_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0,
                    "max_tokens": 2000
                },
                headers={"Authorization": f"Bearer {settings.SECRET_KEY}"}
            )
        
        if response.status_code == 200:
            llm_result = response.json()
            classification = _parse_llm_classification(
                llm_result['choices'][0]['message']['content']
            )
            
            async with get_db_context() as db:
                await db.execute(
                    text("""
                        UPDATE read_models.expenses SET
                            br_qualified = :br_qualified,
                            br_category = :br_category,
                            br_qualification_reason = :br_reason,
                            br_deduction_rate = :br_rate,
                            ip_qualified = :ip_qualified,
                            nexus_category = :nexus,
                            llm_classification = CAST(:llm_data AS jsonb),
                            llm_confidence = :confidence,
                            needs_clarification = :needs_clarification,
                            clarification_questions = CAST(:questions AS jsonb),
                            status = 'classified',
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": expense_id,
                        "br_qualified": classification.get('br_qualified', False),
                        "br_category": classification.get('br_category'),
                        "br_reason": classification.get('br_reason'),
                        "br_rate": classification.get('br_rate', 1.0),
                        "ip_qualified": classification.get('ip_qualified', False),
                        "nexus": classification.get('nexus_category'),
                        "llm_data": json.dumps(classification),
                        "confidence": classification.get('confidence', 0.5),
                        "needs_clarification": classification.get('needs_clarification', False),
                        "questions": json.dumps(classification.get('questions', []))
                    }
                )
            
            logger.info("Expense classified by LLM", 
                       expense_id=expense_id,
                       br_qualified=classification.get('br_qualified'))
    
    except Exception as e:
        logger.error("LLM classification failed", expense_id=expense_id, error=str(e))


def _get_br_classifier_system_prompt() -> str:
    """System prompt for B+R expense classifier"""
    return """Jesteś ekspertem od polskiego prawa podatkowego, specjalizującym się w uldze B+R (art. 26e ustawy o PIT) oraz IP Box (art. 30ca-30cb).

Twoim zadaniem jest klasyfikacja wydatków pod kątem:
1. Kwalifikowalności do ulgi B+R
2. Kategorii kosztów kwalifikowanych
3. Stawki odliczenia (100% lub 200%)
4. Kwalifikowalności do IP Box (kategoria nexus: a, b, c, d)

KATEGORIE KOSZTÓW B+R (zgodnie z art. 26e PIT):
- personnel_employment (200%): wynagrodzenia pracowników B+R (umowa o pracę)
- personnel_civil (200%): umowy zlecenie/o dzieło za prace B+R
- materials (100%): materiały i surowce do B+R
- equipment (100%): sprzęt specjalistyczny niebędący ŚT
- depreciation (100%): odpisy amortyzacyjne ŚT używanych w B+R
- expertise (100%): ekspertyzy od jednostek naukowych
- external_services (100%): usługi zewnętrzne B+R

Odpowiadaj TYLKO w formacie JSON:
{
  "br_qualified": true/false,
  "br_category": "kategoria lub null",
  "br_reason": "uzasadnienie klasyfikacji",
  "br_rate": 1.0 lub 2.0,
  "ip_qualified": true/false,
  "nexus_category": "a/b/c/d lub null",
  "confidence": 0.0-1.0,
  "needs_clarification": true/false,
  "questions": ["pytanie1", "pytanie2"] lub []
}"""


def _build_classification_prompt(expense_row) -> str:
    """Build prompt for expense classification"""
    return f"""Sklasyfikuj następujący wydatek dla projektu B+R:

DANE WYDATKU:
- Numer faktury: {expense_row[3] or 'brak'}
- Data: {expense_row[4] or 'brak'}
- Dostawca: {expense_row[5] or 'brak'}
- NIP dostawcy: {expense_row[6] or 'brak'}
- Kwota netto: {expense_row[7]} PLN
- Kwota brutto: {expense_row[9]} PLN
- Kategoria: {expense_row[11] or 'brak'}

TREŚĆ DOKUMENTU (OCR):
{expense_row[-2] or 'brak treści'}

DANE WYEKSTRAHOWANE:
{expense_row[-1] or 'brak danych'}

Czy ten wydatek kwalifikuje się do ulgi B+R? Jeśli tak, do jakiej kategorii?"""


def _parse_llm_classification(response: str) -> dict:
    """Parse LLM response to classification dict"""
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    
    return {
        "br_qualified": False,
        "confidence": 0.3,
        "needs_clarification": True,
        "questions": ["Nie udało się automatycznie sklasyfikować wydatku."]
    }
