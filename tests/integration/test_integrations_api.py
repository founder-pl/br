"""
Integration Tests - Integrations API
"""
import pytest
from httpx import AsyncClient


class TestIntegrationsAPI:
    """Tests for integrations API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_providers(self, client: AsyncClient):
        """Test listing available providers"""
        response = await client.get("/integrations/providers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "accounting" in data
        assert "cloud_storage" in data
        
        # Check accounting providers
        accounting_ids = [p["id"] for p in data["accounting"]]
        assert "ifirma" in accounting_ids
        assert "fakturownia" in accounting_ids
        
        # Check cloud providers
        cloud_ids = [p["id"] for p in data["cloud_storage"]]
        assert "nextcloud" in cloud_ids
        assert "google_drive" in cloud_ids
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_integration(self, client: AsyncClient):
        """Test creating a new integration"""
        integration_data = {
            "id": "test-ifirma-integration",
            "provider": "ifirma",
            "integration_type": "accounting",
            "credentials": {
                "api_key": "test-api-key",
                "username": "test@example.com",
                "company_name": "Test Company"
            },
            "settings": {
                "sync_invoices": True
            }
        }
        
        response = await client.post("/integrations/", json=integration_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "test-ifirma-integration"
        assert data["provider"] == "ifirma"
        assert data["is_active"] is True
        # Credentials should NOT be in response
        assert "credentials" not in data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_cloud_integration(self, client: AsyncClient):
        """Test creating cloud storage integration"""
        integration_data = {
            "id": "test-nextcloud",
            "provider": "nextcloud",
            "integration_type": "cloud_storage",
            "credentials": {
                "username": "admin",
                "password": "secret123"
            },
            "base_url": "https://cloud.example.com"
        }
        
        response = await client.post("/integrations/", json=integration_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "test-nextcloud"
        assert data["provider"] == "nextcloud"
        assert data["integration_type"] == "cloud_storage"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_integrations(self, client: AsyncClient):
        """Test listing integrations"""
        response = await client.get("/integrations/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_integrations_by_type(self, client: AsyncClient):
        """Test listing integrations filtered by type"""
        # First create integrations of different types
        await client.post("/integrations/", json={
            "id": "filter-test-acc",
            "provider": "fakturownia",
            "integration_type": "accounting",
            "credentials": {"api_token": "test"}
        })
        
        await client.post("/integrations/", json={
            "id": "filter-test-cloud",
            "provider": "google_drive",
            "integration_type": "cloud_storage",
            "credentials": {"access_token": "test"}
        })
        
        # Filter by accounting
        response = await client.get("/integrations/?integration_type=accounting")
        assert response.status_code == 200
        data = response.json()
        
        for integration in data:
            assert integration["integration_type"] == "accounting"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_integration(self, client: AsyncClient):
        """Test getting single integration"""
        # Create first
        await client.post("/integrations/", json={
            "id": "get-test",
            "provider": "wfirma",
            "integration_type": "accounting",
            "credentials": {"access_key": "test"}
        })
        
        # Get
        response = await client.get("/integrations/get-test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "get-test"
        assert data["provider"] == "wfirma"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_nonexistent_integration(self, client: AsyncClient):
        """Test getting non-existent integration"""
        response = await client.get("/integrations/nonexistent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_integration(self, client: AsyncClient):
        """Test updating integration"""
        # Create first
        await client.post("/integrations/", json={
            "id": "update-test",
            "provider": "infakt",
            "integration_type": "accounting",
            "credentials": {"api_key": "old-key"},
            "settings": {"old": "setting"}
        })
        
        # Update
        response = await client.put("/integrations/update-test", json={
            "settings": {"new": "setting"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["settings"]["new"] == "setting"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_integration(self, client: AsyncClient):
        """Test deleting integration"""
        # Create first
        await client.post("/integrations/", json={
            "id": "delete-test",
            "provider": "dropbox",
            "integration_type": "cloud_storage",
            "credentials": {"access_token": "test"}
        })
        
        # Delete
        response = await client.delete("/integrations/delete-test")
        
        assert response.status_code == 200
        
        # Verify deleted
        get_response = await client.get("/integrations/delete-test")
        assert get_response.status_code == 404
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_duplicate_integration_id(self, client: AsyncClient):
        """Test creating integration with duplicate ID"""
        integration_data = {
            "id": "duplicate-test",
            "provider": "ifirma",
            "integration_type": "accounting",
            "credentials": {"api_key": "test"}
        }
        
        # First creation should succeed
        response1 = await client.post("/integrations/", json=integration_data)
        assert response1.status_code == 200
        
        # Second creation should fail
        response2 = await client.post("/integrations/", json=integration_data)
        assert response2.status_code == 409
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_provider(self, client: AsyncClient):
        """Test creating integration with invalid provider"""
        response = await client.post("/integrations/", json={
            "id": "invalid-provider-test",
            "provider": "nonexistent_provider",
            "integration_type": "accounting",
            "credentials": {}
        })
        
        assert response.status_code == 400
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_sync_logs(self, client: AsyncClient):
        """Test getting sync logs"""
        # Create integration first
        await client.post("/integrations/", json={
            "id": "logs-test",
            "provider": "fakturownia",
            "integration_type": "accounting",
            "credentials": {"api_token": "test"}
        })
        
        response = await client.get("/integrations/logs-test/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestIntegrationSyncAPI:
    """Tests for integration sync operations"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sync_invoices_invalid_type(self, client: AsyncClient):
        """Test syncing invoices with non-accounting integration"""
        # Create cloud integration
        await client.post("/integrations/", json={
            "id": "sync-cloud-test",
            "provider": "nextcloud",
            "integration_type": "cloud_storage",
            "credentials": {"url": "https://example.com"}
        })
        
        # Try to sync invoices
        response = await client.post(
            "/integrations/sync-cloud-test/sync/invoices",
            json={"date_from": "2025-01-01", "date_to": "2025-01-31"}
        )
        
        assert response.status_code == 400
        assert "Not an accounting integration" in response.json()["detail"]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_report_invalid_type(self, client: AsyncClient):
        """Test uploading report to non-cloud integration"""
        # Create accounting integration
        await client.post("/integrations/", json={
            "id": "upload-acc-test",
            "provider": "ifirma",
            "integration_type": "accounting",
            "credentials": {"api_key": "test"}
        })
        
        # Try to upload report
        response = await client.post(
            "/integrations/upload-acc-test/upload/report",
            json={"report_name": "test.pdf", "year": 2025, "month": 1}
        )
        
        assert response.status_code == 400
        assert "Not a cloud storage integration" in response.json()["detail"]
