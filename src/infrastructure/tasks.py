"""
Celery Tasks - Background Processing
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
import structlog

logger = structlog.get_logger()

# Directories
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "/app/processed"))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr(self, document_id: str, file_path: str, document_type: str = "invoice"):
    """
    Process document with OCR.
    
    Args:
        document_id: UUID of the document
        file_path: Path to the uploaded file
        document_type: Type of document (invoice, receipt, etc.)
    """
    import httpx
    
    logger.info("Starting OCR processing", document_id=document_id, file_path=file_path)
    
    try:
        ocr_service_url = os.getenv("OCR_SERVICE_URL", "http://ocr-service:8001")
        
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f, 'application/octet-stream')}
            params = {
                'engine': 'paddleocr',
                'language': 'pol',
                'dpi': 300,
                'extract_data': True,
                'document_type': document_type
            }
            
            response = httpx.post(
                f"{ocr_service_url}/ocr/upload",
                files=files,
                params=params,
                timeout=300.0
            )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("OCR completed", document_id=document_id, confidence=result.get('confidence'))
            
            # Update document in database
            update_document_ocr_result.delay(document_id, result)
            
            return result
        else:
            raise Exception(f"OCR service error: {response.status_code}")
            
    except Exception as e:
        logger.error("OCR processing failed", document_id=document_id, error=str(e))
        self.retry(exc=e)


@shared_task
def update_document_ocr_result(document_id: str, ocr_result: dict):
    """Update document with OCR results in database"""
    from src.api.database import get_db_context
    import asyncio
    
    async def update():
        async with get_db_context() as db:
            await db.execute(
                """
                UPDATE read_models.documents SET
                    ocr_status = 'completed',
                    ocr_confidence = :confidence,
                    ocr_text = :text,
                    extracted_data = :data::jsonb,
                    updated_at = NOW()
                WHERE id = :id
                """,
                {
                    "id": document_id,
                    "confidence": ocr_result.get('confidence'),
                    "text": ocr_result.get('text'),
                    "data": str(ocr_result.get('extracted_data', {}))
                }
            )
    
    asyncio.run(update())
    logger.info("Document OCR result updated", document_id=document_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def classify_expense(self, expense_id: str):
    """
    Classify expense using LLM.
    
    Args:
        expense_id: UUID of the expense to classify
    """
    import httpx
    
    logger.info("Starting expense classification", expense_id=expense_id)
    
    try:
        llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm-service:4000")
        secret_key = os.getenv("SECRET_KEY", "")
        
        # Build classification prompt
        prompt = f"Classify expense {expense_id} for B+R qualification"
        
        response = httpx.post(
            f"{llm_service_url}/v1/chat/completions",
            json={
                "model": "br-classifier",
                "messages": [
                    {"role": "system", "content": "You are a B+R expense classifier."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0,
                "max_tokens": 2000
            },
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=120.0
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("Classification completed", expense_id=expense_id)
            return result
        else:
            raise Exception(f"LLM service error: {response.status_code}")
            
    except Exception as e:
        logger.error("Classification failed", expense_id=expense_id, error=str(e))
        self.retry(exc=e)


@shared_task
def generate_daily_reports():
    """Generate daily reports for all active projects"""
    from src.api.database import get_db_context
    import asyncio
    
    async def generate():
        async with get_db_context() as db:
            result = await db.execute(
                "SELECT id FROM read_models.projects WHERE status = 'active'"
            )
            projects = result.fetchall()
            
            for project in projects:
                generate_monthly_report.delay(
                    str(project[0]),
                    datetime.now().year,
                    datetime.now().month
                )
    
    asyncio.run(generate())
    logger.info("Daily report generation triggered")


@shared_task
def generate_monthly_report(project_id: str, year: int, month: int):
    """Generate monthly report for a project"""
    logger.info("Generating monthly report", project_id=project_id, year=year, month=month)
    # Implementation would call the reports API or directly calculate


@shared_task
def cleanup_old_files():
    """Clean up old uploaded and processed files"""
    cutoff_date = datetime.now() - timedelta(days=90)
    
    cleaned_count = 0
    
    for directory in [UPLOAD_DIR, PROCESSED_DIR]:
        if directory.exists():
            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        file_path.unlink()
                        cleaned_count += 1
    
    logger.info("Cleanup completed", files_removed=cleaned_count)
    return cleaned_count


@shared_task
def recalculate_all_projects():
    """Recalculate totals for all active projects"""
    from src.api.database import get_db_context
    import asyncio
    
    async def recalculate():
        async with get_db_context() as db:
            result = await db.execute(
                "SELECT id FROM read_models.projects WHERE status = 'active'"
            )
            projects = result.fetchall()
            
            for project in projects:
                project_id = str(project[0])
                
                # Calculate totals from expenses
                totals = await db.execute(
                    """
                    SELECT 
                        COALESCE(SUM(gross_amount), 0),
                        COALESCE(SUM(CASE WHEN br_qualified THEN gross_amount ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN ip_qualified THEN gross_amount ELSE 0 END), 0)
                    FROM read_models.expenses WHERE project_id = :project_id
                    """,
                    {"project_id": project_id}
                )
                row = totals.fetchone()
                
                # Update project
                await db.execute(
                    """
                    UPDATE read_models.projects SET
                        total_expenses = :total,
                        br_qualified_expenses = :br_total,
                        ip_qualified_expenses = :ip_total,
                        updated_at = NOW()
                    WHERE id = :id
                    """,
                    {
                        "id": project_id,
                        "total": float(row[0]),
                        "br_total": float(row[1]),
                        "ip_total": float(row[2])
                    }
                )
                
            logger.info("Project totals recalculated", count=len(projects))
    
    asyncio.run(recalculate())
