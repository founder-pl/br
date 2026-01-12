"""
Pytest Fixtures for System B+R Tests
"""
import os
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime, date
from decimal import Decimal
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://br_admin:br_secret_2025@postgres:5432/br_system"
)
os.environ.setdefault(
    "REDIS_URL",
    "redis://redis:6379/15"
)
os.environ.setdefault(
    "OCR_SERVICE_URL",
    "http://ocr-service:8001"
)
os.environ.setdefault(
    "LLM_SERVICE_URL",
    "http://llm-service:4000"
)
os.environ["SECRET_KEY"] = "test-secret-key"

# Isolate integrations config DB for tests (avoid leaking state between runs)
os.environ.setdefault("CONFIG_DB_TYPE", "sqlite")
os.environ.setdefault("CONFIG_DB_URL", "sqlite:////tmp/br_config_test.db")
os.environ.setdefault("CONFIG_ENCRYPTION_KEY", "7o2OQ4p0s6lK0f5rV2uWcWlG2Q1mWnq0wQ0z5m7J8mM=")

_config_db_path = Path("/tmp/br_config_test.db")
if _config_db_path.exists():
    try:
        _config_db_path.unlink()
    except Exception:
        pass

from src.api.main import app
from src.api.database import Base, get_db
from src.api.config import settings


# =============================================================================
# Database Fixtures
# =============================================================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql+asyncpg://br_admin:br_secret_2025@postgres:5432/br_system")
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with TestAsyncSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API tests"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_project_data():
    """Sample project data"""
    return {
        "name": "Test Project B+R",
        "description": "Projekt testowy dla systemu B+R",
        "fiscal_year": 2025,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31"
    }


@pytest.fixture
def sample_expense_data():
    """Sample expense data"""
    return {
        "project_id": "00000000-0000-0000-0000-000000000001",
        "invoice_number": "FV/2025/01/001",
        "invoice_date": "2025-01-15",
        "vendor_name": "Test Vendor Sp. z o.o.",
        "vendor_nip": "1234567890",
        "net_amount": 1000.00,
        "vat_amount": 230.00,
        "gross_amount": 1230.00,
        "currency": "PLN",
        "expense_category": "materials"
    }


@pytest.fixture
def sample_document_data():
    """Sample document metadata"""
    return {
        "filename": "test_invoice.pdf",
        "document_type": "invoice",
        "mime_type": "application/pdf",
        "file_size": 12345
    }


@pytest.fixture
def sample_invoice_text():
    """Sample OCR text from invoice"""
    return """
    FAKTURA VAT NR FV/2025/01/001
    Data wystawienia: 15.01.2025
    
    Sprzedawca:
    Test Vendor Sp. z o.o.
    ul. Testowa 123
    00-001 Warszawa
    NIP: 123-456-78-90
    
    Nabywca:
    Tomasz Sapletta
    NIP: 588-191-86-62
    
    Nazwa towaru/usługi          Ilość   Cena netto    Wartość netto
    Komponenty elektroniczne     10      100,00 zł     1000,00 zł
    
    Razem netto:                                       1000,00 zł
    VAT 23%:                                            230,00 zł
    Razem brutto:                                      1230,00 zł
    
    Termin płatności: 14 dni
    """


@pytest.fixture
def sample_nip_valid():
    """Valid Polish NIP numbers for testing"""
    return [
        "5881918662",  # Tomasz Sapletta
        "5252344078",  # Example valid NIP
    ]


@pytest.fixture
def sample_nip_invalid():
    """Invalid Polish NIP numbers for testing"""
    return [
        "1234567890",  # Invalid checksum
        "0000000000",  # All zeros
        "123456789",   # Too short
        "12345678901", # Too long
    ]


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_ocr_result():
    """Mock OCR processing result"""
    return {
        "task_id": str(uuid.uuid4()),
        "status": "completed",
        "text": "FAKTURA VAT NR FV/2025/01/001...",
        "confidence": 0.95,
        "pages": 1,
        "processing_time_ms": 1500,
        "extracted_data": {
            "invoice_number": "FV/2025/01/001",
            "invoice_date": "2025-01-15",
            "vendor_nip": {"cleaned": "1234567890", "valid": True},
            "gross_amount": 1230.00
        }
    }


@pytest.fixture
def mock_llm_classification():
    """Mock LLM classification result"""
    return {
        "br_qualified": True,
        "br_category": "materials",
        "br_reason": "Zakup komponentów elektronicznych do prototypu - kwalifikuje się jako materiały B+R",
        "br_rate": 1.0,
        "ip_qualified": True,
        "nexus_category": "a",
        "confidence": 0.85,
        "needs_clarification": False,
        "questions": []
    }


# =============================================================================
# Helper Functions
# =============================================================================

def create_test_pdf_content() -> bytes:
    """Create minimal valid PDF content for testing"""
    # Minimal PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
193
%%EOF"""


def create_test_image_content() -> bytes:
    """Create minimal valid PNG content for testing"""
    # 1x1 white pixel PNG
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])


# =============================================================================
# Integration Test Fixtures
# =============================================================================

@pytest.fixture
def sample_accounting_integration():
    """Sample accounting integration configuration"""
    return {
        "id": "test-ifirma-integration",
        "provider": "ifirma",
        "integration_type": "accounting",
        "credentials": {
            "api_key": "test-api-key-12345",
            "username": "test@example.com",
            "company_name": "Test Company Sp. z o.o.",
            "invoice_key": "invoice-key-abc",
            "expense_key": "expense-key-xyz"
        },
        "settings": {
            "auto_sync": False,
            "sync_interval_hours": 24
        },
        "base_url": "https://api.ifirma.pl"
    }


@pytest.fixture
def sample_cloud_integration():
    """Sample cloud storage integration configuration"""
    return {
        "id": "test-nextcloud-integration",
        "provider": "nextcloud",
        "integration_type": "cloud_storage",
        "credentials": {
            "username": "admin",
            "password": "secretpassword123"
        },
        "settings": {
            "default_folder": "/BR-Reports",
            "auto_upload": False
        },
        "base_url": "https://cloud.example.com"
    }


@pytest.fixture
def sample_invoice_from_api():
    """Sample invoice data as returned from accounting API"""
    return {
        "id": "inv-12345",
        "number": "FV/2025/01/001",
        "invoice_type": "purchase",
        "status": "issued",
        "issue_date": "2025-01-15",
        "sale_date": "2025-01-15",
        "due_date": "2025-01-29",
        "seller_name": "Dostawca Sp. z o.o.",
        "seller_nip": "1234567890",
        "seller_address": "ul. Testowa 1, 00-001 Warszawa",
        "buyer_name": "Tomasz Sapletta",
        "buyer_nip": "5881918662",
        "items": [
            {
                "name": "Komponenty elektroniczne",
                "quantity": 10,
                "unit": "szt",
                "unit_price_net": 100.00,
                "vat_rate": 23,
                "net_amount": 1000.00,
                "vat_amount": 230.00,
                "gross_amount": 1230.00
            }
        ],
        "net_amount": 1000.00,
        "vat_amount": 230.00,
        "gross_amount": 1230.00,
        "currency": "PLN",
        "payment_method": "przelew",
        "is_paid": False
    }


@pytest.fixture
def sample_cloud_file():
    """Sample cloud file metadata"""
    return {
        "id": "file-12345",
        "name": "raport-br-2025-01.pdf",
        "path": "/BR-Reports/2025/01/raport-br-2025-01.pdf",
        "size": 125000,
        "mime_type": "application/pdf",
        "is_folder": False,
        "created_at": "2025-01-31T12:00:00Z",
        "modified_at": "2025-01-31T12:00:00Z"
    }


@pytest.fixture
def all_accounting_providers():
    """All supported accounting providers with sample credentials"""
    return [
        {
            "provider": "ifirma",
            "credentials": {
                "api_key": "test-key",
                "username": "user@test.com",
                "company_name": "Test Firma"
            }
        },
        {
            "provider": "fakturownia",
            "credentials": {
                "api_token": "test-token-123",
                "subdomain": "testfirma"
            }
        },
        {
            "provider": "wfirma",
            "credentials": {
                "access_key": "ak-123",
                "secret_key": "sk-456",
                "company_id": "comp-789"
            }
        },
        {
            "provider": "infakt",
            "credentials": {
                "api_key": "infakt-api-key"
            }
        }
    ]


@pytest.fixture
def all_cloud_providers():
    """All supported cloud storage providers with sample credentials"""
    return [
        {
            "provider": "nextcloud",
            "credentials": {
                "username": "admin",
                "password": "secret"
            },
            "base_url": "https://cloud.example.com"
        },
        {
            "provider": "google_drive",
            "credentials": {
                "client_id": "client-id",
                "client_secret": "client-secret",
                "access_token": "ya29.token",
                "refresh_token": "refresh-token"
            }
        },
        {
            "provider": "dropbox",
            "credentials": {
                "access_token": "sl.dropbox-token"
            }
        },
        {
            "provider": "onedrive",
            "credentials": {
                "client_id": "azure-client-id",
                "client_secret": "azure-secret",
                "access_token": "eyJ0-token",
                "refresh_token": "refresh"
            }
        },
        {
            "provider": "aws_s3",
            "credentials": {
                "access_key_id": "AKIATEST",
                "secret_access_key": "secret-key",
                "bucket": "br-reports"
            },
            "settings": {"region": "eu-central-1"}
        },
        {
            "provider": "minio",
            "credentials": {
                "access_key_id": "minioadmin",
                "secret_access_key": "minioadmin",
                "bucket": "br-bucket"
            },
            "settings": {"endpoint_url": "http://minio:9000"}
        }
    ]


# =============================================================================
# Config Database Fixture for Unit Tests
# =============================================================================

@pytest.fixture
def temp_config_db(tmp_path):
    """Create temporary config database for testing"""
    from src.integrations.config.database import ConfigDatabase, DatabaseType
    
    db_path = tmp_path / "test_config.db"
    return ConfigDatabase(
        db_type=DatabaseType.SQLITE,
        db_url=f"sqlite:///{db_path}",
        encryption_key=None  # Will generate one
    )
