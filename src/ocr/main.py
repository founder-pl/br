"""
OCR Service - Main Application
System B+R dla Tomasz Sapletta (NIP: 5881918662)
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiofiles
import redis.asyncio as redis

from .engines import TesseractEngine, PaddleOCREngine, get_ocr_engine
from .preprocessing import preprocess_image, preprocess_pdf
from .extractors import InvoiceExtractor, validate_nip
from .models import OCRResult, DocumentType, ProcessingStatus

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "/app/processed"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", "/app/cache"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Ensure directories exist
for dir_path in [UPLOAD_DIR, PROCESSED_DIR, CACHE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Pydantic Models
# =============================================================================

class OCRRequest(BaseModel):
    """Request model for OCR processing"""
    engine: str = Field(default="paddleocr", description="OCR engine: paddleocr, tesseract, easyocr")
    language: str = Field(default="pol", description="Language code")
    dpi: int = Field(default=300, ge=150, le=600, description="DPI for image processing")
    extract_data: bool = Field(default=True, description="Extract structured data from invoices")
    document_type: Optional[str] = Field(default=None, description="Document type hint")


class OCRResponse(BaseModel):
    """Response model for OCR results"""
    task_id: str
    status: str
    filename: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    text: Optional[str] = None
    confidence: Optional[float] = None
    extracted_data: Optional[Dict[str, Any]] = None
    pages: Optional[int] = None
    processing_time_ms: Optional[int] = None
    errors: Optional[List[str]] = None


class TaskStatus(BaseModel):
    """Task status model"""
    task_id: str
    status: str
    progress: int = 0
    message: Optional[str] = None


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting OCR Service", 
                engine=os.getenv("OCR_ENGINE", "paddleocr"),
                language=os.getenv("OCR_LANG", "pol"))
    
    # Initialize Redis connection
    app.state.redis = await redis.from_url(REDIS_URL, decode_responses=True)
    
    # Initialize OCR engines
    app.state.ocr_engine = await get_ocr_engine(
        engine_name=os.getenv("OCR_ENGINE", "paddleocr"),
        language=os.getenv("OCR_LANG", "pol"),
        use_gpu=True
    )
    
    # Initialize extractors
    app.state.invoice_extractor = InvoiceExtractor()
    
    logger.info("OCR Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OCR Service")
    await app.state.redis.close()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="System B+R - OCR Service",
    description="OCR Service dla automatycznej ekstrakcji danych z dokumentów finansowych",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ocr",
        "timestamp": datetime.utcnow().isoformat(),
        "engine": os.getenv("OCR_ENGINE", "paddleocr")
    }


@app.get("/engines")
async def list_engines():
    """List available OCR engines"""
    return {
        "available": ["paddleocr", "tesseract", "easyocr"],
        "default": os.getenv("OCR_ENGINE", "paddleocr"),
        "languages": {
            "paddleocr": ["pol", "eng", "deu", "latin"],
            "tesseract": ["pol", "eng", "deu"],
            "easyocr": ["pl", "en", "de"]
        }
    }


@app.post("/ocr/upload", response_model=OCRResponse)
async def upload_and_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    engine: str = Query(default="paddleocr"),
    language: str = Query(default="pol"),
    dpi: int = Query(default=300, ge=150, le=600),
    extract_data: bool = Query(default=True),
    document_type: Optional[str] = Query(default=None)
):
    """
    Upload and process a document with OCR.
    
    Supports:
    - Images: PNG, JPG, JPEG, TIFF, BMP
    - PDFs: Single and multi-page
    
    Returns extracted text and structured data (if extract_data=True)
    """
    # Validate file type
    allowed_types = {
        "image/png", "image/jpeg", "image/jpg", "image/tiff", "image/bmp",
        "application/pdf"
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {allowed_types}"
        )
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    timestamp = datetime.utcnow()
    
    # Save uploaded file
    file_ext = Path(file.filename).suffix.lower()
    upload_path = UPLOAD_DIR / f"{task_id}{file_ext}"
    
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    logger.info("File uploaded", task_id=task_id, filename=file.filename, size=len(content))
    
    # Store initial status in Redis
    await app.state.redis.hset(f"ocr:task:{task_id}", mapping={
        "status": "processing",
        "filename": file.filename,
        "created_at": timestamp.isoformat(),
        "engine": engine,
        "language": language
    })
    
    # Process synchronously for now (can be moved to background for large files)
    try:
        start_time = datetime.utcnow()
        
        # Preprocess and OCR
        if file.content_type == "application/pdf":
            images = await preprocess_pdf(upload_path, dpi=dpi)
            all_text = []
            all_confidence = []
            
            for i, img in enumerate(images):
                result = await app.state.ocr_engine.process(img)
                all_text.append(result.text)
                all_confidence.append(result.confidence)
                
                # Update progress
                await app.state.redis.hset(f"ocr:task:{task_id}", "progress", 
                                          int((i + 1) / len(images) * 100))
            
            text = "\n\n--- Page Break ---\n\n".join(all_text)
            confidence = sum(all_confidence) / len(all_confidence) if all_confidence else 0
            pages = len(images)
        else:
            img = await preprocess_image(upload_path, dpi=dpi)
            result = await app.state.ocr_engine.process(img)
            text = result.text
            confidence = result.confidence
            pages = 1
        
        # Extract structured data
        extracted_data = None
        if extract_data and text:
            extracted_data = await app.state.invoice_extractor.extract(text, document_type)
        
        end_time = datetime.utcnow()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        # Save processed result
        processed_path = PROCESSED_DIR / f"{task_id}.json"
        result_data = {
            "task_id": task_id,
            "text": text,
            "confidence": confidence,
            "extracted_data": extracted_data,
            "pages": pages,
            "processing_time_ms": processing_time
        }
        
        async with aiofiles.open(processed_path, 'w') as f:
            import json
            await f.write(json.dumps(result_data, ensure_ascii=False, indent=2, default=str))
        
        # Update Redis status
        await app.state.redis.hset(f"ocr:task:{task_id}", mapping={
            "status": "completed",
            "completed_at": end_time.isoformat(),
            "confidence": str(confidence),
            "pages": str(pages),
            "processing_time_ms": str(processing_time)
        })
        
        logger.info("OCR completed", task_id=task_id, pages=pages, 
                   confidence=confidence, processing_time_ms=processing_time)
        
        return OCRResponse(
            task_id=task_id,
            status="completed",
            filename=file.filename,
            created_at=timestamp,
            completed_at=end_time,
            text=text,
            confidence=confidence,
            extracted_data=extracted_data,
            pages=pages,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error("OCR failed", task_id=task_id, error=str(e))
        await app.state.redis.hset(f"ocr:task:{task_id}", mapping={
            "status": "failed",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.get("/ocr/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of an OCR task"""
    task_data = await app.state.redis.hgetall(f"ocr:task:{task_id}")
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(
        task_id=task_id,
        status=task_data.get("status", "unknown"),
        progress=int(task_data.get("progress", 0)),
        message=task_data.get("error")
    )


@app.get("/ocr/result/{task_id}", response_model=OCRResponse)
async def get_task_result(task_id: str):
    """Get the result of a completed OCR task"""
    task_data = await app.state.redis.hgetall(f"ocr:task:{task_id}")
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_data.get("status") != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Task not completed. Status: {task_data.get('status')}"
        )
    
    # Load result from file
    processed_path = PROCESSED_DIR / f"{task_id}.json"
    if not processed_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    async with aiofiles.open(processed_path, 'r') as f:
        import json
        result_data = json.loads(await f.read())
    
    return OCRResponse(
        task_id=task_id,
        status="completed",
        filename=task_data.get("filename", ""),
        created_at=datetime.fromisoformat(task_data.get("created_at")),
        completed_at=datetime.fromisoformat(task_data.get("completed_at")) if task_data.get("completed_at") else None,
        text=result_data.get("text"),
        confidence=result_data.get("confidence"),
        extracted_data=result_data.get("extracted_data"),
        pages=result_data.get("pages"),
        processing_time_ms=result_data.get("processing_time_ms")
    )


@app.post("/ocr/validate-nip")
async def validate_nip_endpoint(nip: str):
    """Validate Polish NIP number"""
    is_valid = validate_nip(nip)
    return {
        "nip": nip,
        "valid": is_valid,
        "formatted": f"{nip[:3]}-{nip[3:6]}-{nip[6:8]}-{nip[8:]}" if is_valid and len(nip) == 10 else None
    }


# =============================================================================
# Run with: python -m uvicorn src.ocr.main:app --host 0.0.0.0 --port 8001
# =============================================================================
