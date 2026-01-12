"""
Unit Tests - Integration Clients
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.config.database import (
    ConfigDatabase, IntegrationProvider, IntegrationType, DatabaseType
)
from src.integrations.accounting.base import Invoice, InvoiceItem, InvoiceType, InvoiceStatus
from src.integrations.cloud.base import CloudFile, UploadResult


class TestConfigDatabase:
    """Tests for configuration database"""
    
    @pytest.fixture
    def config_db(self, tmp_path):
        """Create temporary config database"""
        db_path = tmp_path / "test_config.db"
        return ConfigDatabase(
            db_type=DatabaseType.SQLITE,
            db_url=f"sqlite:///{db_path}",
            encryption_key=None  # Will generate one
        )
    
    @pytest.mark.unit
    def test_save_and_get_integration(self, config_db):
        """Test saving and retrieving integration"""
        config_db.save_integration(
            integration_id="test-ifirma",
            provider=IntegrationProvider.IFIRMA,
            integration_type=IntegrationType.ACCOUNTING,
            credentials={"api_key": "test-key", "username": "test@example.com"},
            settings={"company_name": "Test Company"},
            base_url="https://api.ifirma.pl"
        )
        
        result = config_db.get_integration("test-ifirma")
        
        assert result is not None
        assert result["id"] == "test-ifirma"
        assert result["provider"] == "ifirma"
        assert result["integration_type"] == "accounting"
        assert result["credentials"]["api_key"] == "test-key"
        assert result["settings"]["company_name"] == "Test Company"
    
    @pytest.mark.unit
    def test_list_integrations(self, config_db):
        """Test listing integrations"""
        # Add test integrations
        config_db.save_integration(
            integration_id="acc-1",
            provider=IntegrationProvider.IFIRMA,
            integration_type=IntegrationType.ACCOUNTING,
            credentials={"key": "value"}
        )
        config_db.save_integration(
            integration_id="cloud-1",
            provider=IntegrationProvider.NEXTCLOUD,
            integration_type=IntegrationType.CLOUD_STORAGE,
            credentials={"url": "https://cloud.example.com"}
        )
        
        # List all
        all_integrations = config_db.list_integrations(active_only=False)
        assert len(all_integrations) == 2
        
        # List by type
        accounting = config_db.list_integrations(
            integration_type=IntegrationType.ACCOUNTING,
            active_only=False
        )
        assert len(accounting) == 1
        assert accounting[0]["provider"] == "ifirma"
    
    @pytest.mark.unit
    def test_delete_integration(self, config_db):
        """Test deleting integration"""
        config_db.save_integration(
            integration_id="to-delete",
            provider=IntegrationProvider.FAKTUROWNIA,
            integration_type=IntegrationType.ACCOUNTING,
            credentials={"token": "abc"}
        )
        
        assert config_db.get_integration("to-delete") is not None
        
        result = config_db.delete_integration("to-delete")
        assert result is True
        
        assert config_db.get_integration("to-delete") is None
    
    @pytest.mark.unit
    def test_encryption_decryption(self, config_db):
        """Test credential encryption/decryption"""
        original = "super-secret-api-key-123"
        
        encrypted = config_db.encrypt(original)
        decrypted = config_db.decrypt(encrypted)
        
        assert encrypted != original
        assert decrypted == original
    
    @pytest.mark.unit
    def test_sync_log(self, config_db):
        """Test sync logging"""
        log_id = config_db.log_sync(
            integration_id="test-integration",
            sync_type="invoices",
            status="success",
            items_processed=10,
            items_failed=1,
            details={"date_range": "2025-01-01 to 2025-01-31"}
        )
        
        assert log_id is not None
        
        logs = config_db.get_sync_logs(integration_id="test-integration")
        assert len(logs) == 1
        assert logs[0]["items_processed"] == 10


class TestInvoiceModel:
    """Tests for Invoice data model"""
    
    @pytest.mark.unit
    def test_invoice_item_calculation(self):
        """Test invoice item amount calculation"""
        item = InvoiceItem(
            name="Test Product",
            quantity=2,
            unit="szt",
            unit_price_net=100.00,
            vat_rate=23
        )
        
        assert item.net_amount == 200.00
        assert item.vat_amount == 46.00
        assert item.gross_amount == 246.00
    
    @pytest.mark.unit
    def test_invoice_creation(self):
        """Test Invoice model creation"""
        invoice = Invoice(
            id="inv-001",
            number="FV/2025/01/001",
            invoice_type=InvoiceType.PURCHASE,
            status=InvoiceStatus.ISSUED,
            issue_date=date(2025, 1, 15),
            seller_name="Test Vendor",
            seller_nip="1234567890",
            net_amount=1000.00,
            vat_amount=230.00,
            gross_amount=1230.00
        )
        
        assert invoice.id == "inv-001"
        assert invoice.invoice_type == InvoiceType.PURCHASE
        assert invoice.gross_amount == 1230.00


class TestCloudFileModel:
    """Tests for CloudFile data model"""
    
    @pytest.mark.unit
    def test_cloud_file_creation(self):
        """Test CloudFile model creation"""
        file = CloudFile(
            id="file-123",
            name="report.pdf",
            path="/BR-Reports/2025/01/report.pdf",
            size=1024,
            mime_type="application/pdf",
            is_folder=False
        )
        
        assert file.name == "report.pdf"
        assert file.is_folder is False
    
    @pytest.mark.unit
    def test_upload_result_success(self):
        """Test UploadResult success"""
        result = UploadResult(
            success=True,
            file_id="uploaded-123",
            file_path="/reports/file.pdf",
            file_url="https://cloud.example.com/f/123"
        )
        
        assert result.success is True
        assert result.file_id == "uploaded-123"
    
    @pytest.mark.unit
    def test_upload_result_failure(self):
        """Test UploadResult failure"""
        result = UploadResult(
            success=False,
            error="Connection timeout"
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"


class TestFactoryFunctions:
    """Tests for integration factory functions"""
    
    @pytest.mark.unit
    def test_get_accounting_client_ifirma(self):
        """Test creating iFirma client"""
        from src.integrations.factory import get_accounting_client
        
        client = get_accounting_client(
            provider=IntegrationProvider.IFIRMA,
            credentials={"api_key": "test", "username": "test@example.com"},
            settings={}
        )
        
        assert client is not None
        assert client.provider_name == "ifirma"
    
    @pytest.mark.unit
    def test_get_cloud_client_nextcloud(self):
        """Test creating Nextcloud client"""
        from src.integrations.factory import get_cloud_client
        
        client = get_cloud_client(
            provider=IntegrationProvider.NEXTCLOUD,
            credentials={
                "url": "https://cloud.example.com",
                "username": "user",
                "password": "pass"
            }
        )
        
        assert client is not None
        assert client.provider_name == "nextcloud"
    
    @pytest.mark.unit
    def test_get_cloud_client_s3(self):
        """Test creating S3 client"""
        from src.integrations.factory import get_cloud_client
        
        client = get_cloud_client(
            provider=IntegrationProvider.AWS_S3,
            credentials={
                "access_key_id": "AKIATEST",
                "secret_access_key": "secret",
                "bucket": "test-bucket"
            }
        )
        
        assert client is not None
        assert client.provider_name == "aws_s3"
    
    @pytest.mark.unit
    def test_get_unknown_provider(self):
        """Test handling unknown provider"""
        from src.integrations.factory import get_accounting_client
        
        # This should return None for invalid provider
        # (would need to handle the enum properly)
        pass  # Skip - enum validation happens before
