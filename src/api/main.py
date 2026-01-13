"""
API Backend - Main Application
System B+R dla Tomasz Sapletta (NIP: 5881918662)
FastAPI z CQRS i Event Sourcing
"""
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import documents, expenses, projects, reports, auth, clarifications, integrations, logs, config, timesheet, git_timesheet
from src.doc_generator.router import router as doc_generator_router
from .database import init_database, close_database
from .config import settings

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting API Backend",
               environment=settings.ENVIRONMENT,
               company=settings.COMPANY_NAME,
               project=settings.PROJECT_NAME)
    
    # Initialize database
    await init_database()
    
    logger.info("API Backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Backend")
    await close_database()


# OpenAPI Tags
openapi_tags = [
    {"name": "Autoryzacja", "description": "Autentykacja i zarządzanie użytkownikami"},
    {"name": "Dokumenty", "description": "Upload, OCR i przetwarzanie dokumentów finansowych"},
    {"name": "Wydatki B+R", "description": "Ewidencja i klasyfikacja kosztów B+R oraz IP Box"},
    {"name": "Projekty", "description": "Zarządzanie projektami badawczo-rozwojowymi"},
    {"name": "Raporty", "description": "Generowanie raportów miesięcznych i rocznych dla US"},
    {"name": "Wyjaśnienia", "description": "System pytań i odpowiedzi dla niejasnych wydatków"},
    {"name": "Integracje", "description": "KSeF, JPK_V7M, systemy księgowe i cloud storage"},
    {"name": "Logi", "description": "Streaming logów z kontenerów Docker"},
    {"name": "Konfiguracja", "description": "Ustawienia systemowe i parametry"},
    {"name": "Harmonogram", "description": "Rejestr czasu pracy pracowników B+R"},
    {"name": "Harmonogram Git", "description": "Generowanie ewidencji z commitów Git"},
    {"name": "Generator dokumentów", "description": "Generowanie dokumentów B+R i IP Box"},
]

# Create FastAPI app
app = FastAPI(
    title="System B+R - API",
    description=f"""
## System zarządzania dokumentacją B+R

**Firma:** {settings.COMPANY_NAME} (NIP: {settings.COMPANY_NIP})  
**Projekt:** {settings.PROJECT_NAME}  
**Rok podatkowy:** {settings.FISCAL_YEAR}

### Główne funkcjonalności

| Moduł | Opis |
|-------|------|
| **Dokumenty** | Upload i OCR dokumentów finansowych (faktury, rachunki) |
| **Wydatki** | Klasyfikacja kosztów B+R i IP Box z walidacją |
| **Przychody** | Ewidencja przychodów z kwalifikowanych praw IP |
| **Raporty** | Generowanie raportów miesięcznych/rocznych dla US |
| **Harmonogram** | Dzienny rejestr czasu pracy z integracją Git |
| **Integracje** | KSeF, JPK_V7M, systemy księgowe |

### Endpoints walidacji (P0-P2)

- `POST /expenses/validate-pipeline` - Kompleksowa walidacja wydatku
- `POST /expenses/categorize` - Automatyczna kategoryzacja B+R
- `POST /expenses/validate-invoice` - Walidacja numeru faktury
- `POST /expenses/convert-currency` - Konwersja walut (NBP)

### Endpoints integracji (P3)

- `POST /integrations/ksef/import` - Import faktur z KSeF
- `POST /integrations/jpk/generate` - Generowanie JPK_V7M
- `GET /integrations/jpk/download` - Pobieranie pliku JPK

### Architektura

System wykorzystuje **CQRS** (Command Query Responsibility Segregation) 
z **Event Sourcing** dla pełnego audit trail.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=openapi_tags,
    contact={
        "name": "System B+R Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://example.com/license"
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", 
                 path=request.url.path,
                 method=request.method,
                 error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": str(datetime.utcnow().timestamp())}
    )


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Autoryzacja"])
app.include_router(documents.router, prefix="/documents", tags=["Dokumenty"])
app.include_router(expenses.router, prefix="/expenses", tags=["Wydatki B+R"])
app.include_router(projects.router, prefix="/projects", tags=["Projekty"])
app.include_router(reports.router, prefix="/reports", tags=["Raporty"])
app.include_router(clarifications.router, prefix="/clarifications", tags=["Wyjaśnienia"])
app.include_router(integrations.router, prefix="/integrations", tags=["Integracje"])
app.include_router(logs.router, prefix="/logs", tags=["Logi"])
app.include_router(config.router, prefix="/config", tags=["Konfiguracja"])
app.include_router(timesheet.router, prefix="/timesheet", tags=["Harmonogram"])
app.include_router(git_timesheet.router, prefix="/git-timesheet", tags=["Harmonogram Git"])
app.include_router(doc_generator_router, tags=["Generator dokumentów"])


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "company_nip": settings.COMPANY_NIP,
        "project": settings.PROJECT_NAME
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "System B+R API",
        "version": "1.0.0",
        "company": settings.COMPANY_NAME,
        "nip": settings.COMPANY_NIP,
        "project": settings.PROJECT_NAME,
        "docs": "/docs",
        "health": "/health"
    }


# Metrics endpoint (basic)
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    return {
        "uptime": "running",
        "timestamp": datetime.utcnow().isoformat()
    }
