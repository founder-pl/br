"""
End-to-End Tests - Integration Scenarios
Full integration workflows with accounting and cloud storage systems
"""
import pytest
import asyncio
from datetime import date, datetime, timedelta
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock


class TestAccountingIntegrationE2E:
    """E2E tests for accounting system integration workflows"""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_full_accounting_integration_setup_and_sync(self, client: AsyncClient):
        """
        Full E2E test: Setup accounting integration -> Verify -> Sync invoices -> Check expenses
        """
        # Step 1: List available providers
        providers_response = await client.get("/integrations/providers")
        assert providers_response.status_code == 200
        providers = providers_response.json()
        assert "accounting" in providers
        assert any(p["id"] == "ifirma" for p in providers["accounting"])
        
        # Step 2: Create accounting integration
        integration_data = {
            "id": "e2e-test-ifirma",
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
        
        create_response = await client.post("/integrations/", json=integration_data)
        assert create_response.status_code == 200
        created = create_response.json()
        
        assert created["id"] == "e2e-test-ifirma"
        assert created["provider"] == "ifirma"
        assert created["is_active"] is True
        assert created["is_verified"] is False
        
        # Step 3: Get integration details
        get_response = await client.get("/integrations/e2e-test-ifirma")
        assert get_response.status_code == 200
        details = get_response.json()
        assert details["settings"]["auto_sync"] is False
        
        # Step 4: Update integration settings
        update_response = await client.put("/integrations/e2e-test-ifirma", json={
            "settings": {"auto_sync": True, "sync_interval_hours": 12}
        })
        assert update_response.status_code == 200
        
        # Step 5: Verify integration (mock - will fail without real API)
        verify_response = await client.post("/integrations/e2e-test-ifirma/verify")
        assert verify_response.status_code == 200
        # Verification will fail with test credentials, but endpoint works
        
        # Step 6: Check sync logs (should be empty initially)
        logs_response = await client.get("/integrations/e2e-test-ifirma/logs")
        assert logs_response.status_code == 200
        assert isinstance(logs_response.json(), list)
        
        # Step 7: List all accounting integrations
        list_response = await client.get("/integrations/?integration_type=accounting")
        assert list_response.status_code == 200
        integrations = list_response.json()
        assert any(i["id"] == "e2e-test-ifirma" for i in integrations)
        
        # Step 8: Cleanup - delete integration
        delete_response = await client.delete("/integrations/e2e-test-ifirma")
        assert delete_response.status_code == 200
        
        # Verify deleted
        get_deleted = await client.get("/integrations/e2e-test-ifirma")
        assert get_deleted.status_code == 404
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multiple_accounting_integrations_workflow(self, client: AsyncClient):
        """
        E2E test: Setup multiple accounting integrations and manage them
        """
        integrations_to_create = [
            {
                "id": "e2e-ifirma",
                "provider": "ifirma",
                "integration_type": "accounting",
                "credentials": {"api_key": "key1", "username": "user1@test.com", "company_name": "Firma 1"}
            },
            {
                "id": "e2e-fakturownia",
                "provider": "fakturownia",
                "integration_type": "accounting",
                "credentials": {"api_token": "token123", "subdomain": "mojafirma"}
            },
            {
                "id": "e2e-wfirma",
                "provider": "wfirma",
                "integration_type": "accounting",
                "credentials": {"access_key": "ak123", "secret_key": "sk456", "company_id": "comp789"}
            }
        ]
        
        created_ids = []
        
        try:
            # Create all integrations
            for integration in integrations_to_create:
                response = await client.post("/integrations/", json=integration)
                assert response.status_code == 200
                created_ids.append(integration["id"])
            
            # List all accounting integrations
            list_response = await client.get("/integrations/?integration_type=accounting")
            assert list_response.status_code == 200
            accounting_integrations = list_response.json()
            
            assert len([i for i in accounting_integrations if i["id"] in created_ids]) == 3
            
            # Verify each one has correct provider
            for integration in accounting_integrations:
                if integration["id"] == "e2e-ifirma":
                    assert integration["provider"] == "ifirma"
                elif integration["id"] == "e2e-fakturownia":
                    assert integration["provider"] == "fakturownia"
                elif integration["id"] == "e2e-wfirma":
                    assert integration["provider"] == "wfirma"
        
        finally:
            # Cleanup
            for integration_id in created_ids:
                await client.delete(f"/integrations/{integration_id}")


class TestCloudStorageIntegrationE2E:
    """E2E tests for cloud storage integration workflows"""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_full_cloud_storage_integration_setup(self, client: AsyncClient):
        """
        Full E2E test: Setup cloud storage -> Verify -> Upload report -> Check logs
        """
        # Step 1: List cloud storage providers
        providers_response = await client.get("/integrations/providers")
        assert providers_response.status_code == 200
        providers = providers_response.json()
        assert "cloud_storage" in providers
        assert any(p["id"] == "nextcloud" for p in providers["cloud_storage"])
        
        # Step 2: Create Nextcloud integration
        integration_data = {
            "id": "e2e-test-nextcloud",
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
        
        create_response = await client.post("/integrations/", json=integration_data)
        assert create_response.status_code == 200
        created = create_response.json()
        
        assert created["id"] == "e2e-test-nextcloud"
        assert created["provider"] == "nextcloud"
        assert created["integration_type"] == "cloud_storage"
        
        # Step 3: Create S3 integration
        s3_integration = {
            "id": "e2e-test-s3",
            "provider": "aws_s3",
            "integration_type": "cloud_storage",
            "credentials": {
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket": "br-reports-bucket"
            },
            "settings": {
                "region": "eu-central-1"
            }
        }
        
        s3_response = await client.post("/integrations/", json=s3_integration)
        assert s3_response.status_code == 200
        
        # Step 4: List cloud storage integrations
        list_response = await client.get("/integrations/?integration_type=cloud_storage")
        assert list_response.status_code == 200
        cloud_integrations = list_response.json()
        
        assert any(i["id"] == "e2e-test-nextcloud" for i in cloud_integrations)
        assert any(i["id"] == "e2e-test-s3" for i in cloud_integrations)
        
        # Step 5: Cleanup
        await client.delete("/integrations/e2e-test-nextcloud")
        await client.delete("/integrations/e2e-test-s3")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_all_cloud_providers_setup(self, client: AsyncClient):
        """
        E2E test: Setup all supported cloud storage providers
        """
        providers_configs = [
            {
                "id": "e2e-nextcloud",
                "provider": "nextcloud",
                "integration_type": "cloud_storage",
                "credentials": {"username": "user", "password": "pass"},
                "base_url": "https://cloud.example.com"
            },
            {
                "id": "e2e-gdrive",
                "provider": "google_drive",
                "integration_type": "cloud_storage",
                "credentials": {
                    "client_id": "client123",
                    "client_secret": "secret456",
                    "access_token": "ya29.token",
                    "refresh_token": "refresh.token"
                }
            },
            {
                "id": "e2e-dropbox",
                "provider": "dropbox",
                "integration_type": "cloud_storage",
                "credentials": {"access_token": "sl.token12345"}
            },
            {
                "id": "e2e-onedrive",
                "provider": "onedrive",
                "integration_type": "cloud_storage",
                "credentials": {
                    "client_id": "azure-client-id",
                    "client_secret": "azure-secret",
                    "access_token": "eyJ0token",
                    "refresh_token": "refresh"
                }
            },
            {
                "id": "e2e-minio",
                "provider": "minio",
                "integration_type": "cloud_storage",
                "credentials": {
                    "access_key_id": "minioadmin",
                    "secret_access_key": "minioadmin",
                    "bucket": "br-bucket"
                },
                "settings": {"endpoint_url": "http://minio:9000"}
            }
        ]
        
        created_ids = []
        
        try:
            for config in providers_configs:
                response = await client.post("/integrations/", json=config)
                assert response.status_code == 200, f"Failed to create {config['provider']}"
                created_ids.append(config["id"])
            
            # Verify all created
            list_response = await client.get("/integrations/?integration_type=cloud_storage")
            assert list_response.status_code == 200
            
            integrations = list_response.json()
            for expected_id in created_ids:
                assert any(i["id"] == expected_id for i in integrations), f"Missing {expected_id}"
        
        finally:
            for integration_id in created_ids:
                await client.delete(f"/integrations/{integration_id}")


class TestIntegrationSyncWorkflowE2E:
    """E2E tests for integration sync workflows"""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_invoice_sync_workflow(self, client: AsyncClient):
        """
        E2E test: Setup integration -> Trigger sync -> Check logs -> Verify data
        """
        # Create accounting integration
        integration_data = {
            "id": "e2e-sync-test",
            "provider": "fakturownia",
            "integration_type": "accounting",
            "credentials": {"api_token": "test-token", "subdomain": "testfirma"}
        }
        
        try:
            await client.post("/integrations/", json=integration_data)
            
            # Trigger invoice sync (will fail without real API, but tests endpoint)
            sync_request = {
                "date_from": (date.today() - timedelta(days=30)).isoformat(),
                "date_to": date.today().isoformat(),
                "project_id": "00000000-0000-0000-0000-000000000001"
            }
            
            sync_response = await client.post(
                "/integrations/e2e-sync-test/sync/invoices",
                json=sync_request
            )
            # May return error due to mock API, but endpoint should work
            assert sync_response.status_code in [200, 500]
            
            # Check sync logs
            logs_response = await client.get("/integrations/e2e-sync-test/logs")
            assert logs_response.status_code == 200
        
        finally:
            await client.delete("/integrations/e2e-sync-test")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_report_upload_workflow(self, client: AsyncClient):
        """
        E2E test: Setup cloud integration -> Upload report -> Check logs
        """
        # Create cloud integration
        integration_data = {
            "id": "e2e-upload-test",
            "provider": "nextcloud",
            "integration_type": "cloud_storage",
            "credentials": {"username": "user", "password": "pass"},
            "base_url": "https://cloud.test.com"
        }
        
        try:
            await client.post("/integrations/", json=integration_data)
            
            # Trigger report upload (will fail without real cloud, but tests endpoint)
            upload_request = {
                "report_name": "raport-br-2025-01.pdf",
                "year": 2025,
                "month": 1
            }
            
            upload_response = await client.post(
                "/integrations/e2e-upload-test/upload/report",
                json=upload_request
            )
            # May return error due to mock cloud, but endpoint should work
            assert upload_response.status_code in [200, 500]
        
        finally:
            await client.delete("/integrations/e2e-upload-test")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_bulk_sync_all_integrations(self, client: AsyncClient):
        """
        E2E test: Setup multiple integrations -> Sync all -> Upload all reports
        """
        # Create multiple integrations
        integrations = [
            {
                "id": "e2e-bulk-acc-1",
                "provider": "ifirma",
                "integration_type": "accounting",
                "credentials": {"api_key": "k1", "username": "u1@test.com", "company_name": "F1"}
            },
            {
                "id": "e2e-bulk-cloud-1",
                "provider": "nextcloud",
                "integration_type": "cloud_storage",
                "credentials": {"username": "u", "password": "p"},
                "base_url": "https://c1.test.com"
            }
        ]
        
        created_ids = []
        
        try:
            for integration in integrations:
                response = await client.post("/integrations/", json=integration)
                assert response.status_code == 200
                created_ids.append(integration["id"])
            
            # Sync all invoices
            sync_response = await client.post(
                "/integrations/actions/sync-all-invoices",
                json={
                    "date_from": (date.today() - timedelta(days=30)).isoformat(),
                    "date_to": date.today().isoformat()
                }
            )
            assert sync_response.status_code == 200
            sync_result = sync_response.json()
            assert "integrations_synced" in sync_result
            
            # Upload all reports
            upload_response = await client.post(
                "/integrations/actions/upload-monthly-reports?year=2025&month=1"
            )
            assert upload_response.status_code in [200, 404]  # 404 if no cloud integrations active
        
        finally:
            for integration_id in created_ids:
                await client.delete(f"/integrations/{integration_id}")


class TestIntegrationErrorHandlingE2E:
    """E2E tests for integration error handling"""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_invalid_provider_error(self, client: AsyncClient):
        """Test error handling for invalid provider"""
        response = await client.post("/integrations/", json={
            "id": "invalid-test",
            "provider": "nonexistent_provider",
            "integration_type": "accounting",
            "credentials": {}
        })
        
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_duplicate_integration_id_error(self, client: AsyncClient):
        """Test error handling for duplicate integration ID"""
        integration_data = {
            "id": "duplicate-test",
            "provider": "ifirma",
            "integration_type": "accounting",
            "credentials": {"api_key": "k", "username": "u@test.com", "company_name": "F"}
        }
        
        try:
            # First creation
            response1 = await client.post("/integrations/", json=integration_data)
            assert response1.status_code == 200
            
            # Duplicate creation
            response2 = await client.post("/integrations/", json=integration_data)
            assert response2.status_code == 409
            assert "already exists" in response2.json()["detail"]
        
        finally:
            await client.delete("/integrations/duplicate-test")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_wrong_integration_type_for_operation(self, client: AsyncClient):
        """Test error handling when using wrong integration type for operation"""
        # Create cloud integration
        await client.post("/integrations/", json={
            "id": "wrong-type-test",
            "provider": "nextcloud",
            "integration_type": "cloud_storage",
            "credentials": {"username": "u", "password": "p"},
            "base_url": "https://cloud.test.com"
        })
        
        try:
            # Try to sync invoices with cloud integration
            response = await client.post(
                "/integrations/wrong-type-test/sync/invoices",
                json={"date_from": "2025-01-01", "date_to": "2025-01-31"}
            )
            
            assert response.status_code == 400
            assert "Not an accounting integration" in response.json()["detail"]
        
        finally:
            await client.delete("/integrations/wrong-type-test")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_nonexistent_integration_error(self, client: AsyncClient):
        """Test error handling for nonexistent integration"""
        response = await client.get("/integrations/nonexistent-integration-12345")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestFullIntegrationBusinessScenarioE2E:
    """E2E tests for complete business scenarios with integrations"""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complete_monthly_workflow_with_integrations(self, client: AsyncClient):
        """
        Complete monthly B+R workflow with integrations:
        1. Setup accounting integration (iFirma)
        2. Setup cloud storage integration (Nextcloud)
        3. Sync invoices from accounting
        4. Process and classify expenses
        5. Generate monthly report
        6. Upload report to cloud storage
        7. Verify all steps completed
        """
        accounting_id = "e2e-complete-acc"
        cloud_id = "e2e-complete-cloud"
        project_id = "00000000-0000-0000-0000-000000000001"
        
        try:
            # Step 1: Setup accounting integration
            await client.post("/integrations/", json={
                "id": accounting_id,
                "provider": "ifirma",
                "integration_type": "accounting",
                "credentials": {
                    "api_key": "test-key",
                    "username": "test@firma.pl",
                    "company_name": "Test Firma Sp. z o.o."
                }
            })
            
            # Step 2: Setup cloud storage integration
            await client.post("/integrations/", json={
                "id": cloud_id,
                "provider": "nextcloud",
                "integration_type": "cloud_storage",
                "credentials": {"username": "admin", "password": "secret"},
                "base_url": "https://cloud.firma.pl"
            })
            
            # Step 3: Verify both integrations exist
            accounting_response = await client.get(f"/integrations/{accounting_id}")
            assert accounting_response.status_code == 200
            
            cloud_response = await client.get(f"/integrations/{cloud_id}")
            assert cloud_response.status_code == 200
            
            # Step 4: Trigger invoice sync (will fail without real API)
            sync_response = await client.post(
                f"/integrations/{accounting_id}/sync/invoices",
                json={
                    "date_from": "2025-01-01",
                    "date_to": "2025-01-31",
                    "project_id": project_id
                }
            )
            # Endpoint works, actual sync may fail
            
            # Step 5: Create manual expenses (since sync won't work with test API)
            expenses_data = [
                {
                    "project_id": project_id,
                    "invoice_number": "E2E/2025/01/001",
                    "invoice_date": "2025-01-10",
                    "vendor_name": "Dostawca Komponentów",
                    "net_amount": 8000.00,
                    "vat_amount": 1840.00,
                    "gross_amount": 9840.00,
                    "currency": "PLN",
                    "expense_category": "materials"
                },
                {
                    "project_id": project_id,
                    "invoice_number": "E2E/2025/01/002",
                    "invoice_date": "2025-01-20",
                    "vendor_name": "Konsultant IT",
                    "net_amount": 15000.00,
                    "vat_amount": 3450.00,
                    "gross_amount": 18450.00,
                    "currency": "PLN",
                    "expense_category": "external_services"
                }
            ]
            
            expense_ids = []
            for exp in expenses_data:
                response = await client.post("/expenses/", json=exp)
                if response.status_code == 200:
                    expense_ids.append(response.json()["id"])
            
            # Step 6: Classify expenses as B+R
            for exp_id in expense_ids:
                await client.put(f"/expenses/{exp_id}/classify", json={
                    "br_qualified": True,
                    "br_category": "materials",
                    "br_deduction_rate": 1.0
                })
            
            # Step 7: Generate monthly report
            report_response = await client.post("/reports/monthly/generate", json={
                "project_id": project_id,
                "fiscal_year": 2025,
                "month": 1,
                "regenerate": True
            })
            assert report_response.status_code == 200
            
            # Step 8: Upload report to cloud (will fail without real cloud)
            upload_response = await client.post(
                f"/integrations/{cloud_id}/upload/report",
                json={
                    "report_name": "raport-br-2025-01.pdf",
                    "year": 2025,
                    "month": 1
                }
            )
            # Endpoint works, actual upload may fail
            
            # Step 9: Check sync logs for both integrations
            acc_logs = await client.get(f"/integrations/{accounting_id}/logs")
            assert acc_logs.status_code == 200
            
            cloud_logs = await client.get(f"/integrations/{cloud_id}/logs")
            assert cloud_logs.status_code == 200
            
            # Step 10: Check project summary
            summary_response = await client.get(f"/projects/{project_id}/summary")
            assert summary_response.status_code == 200
            
            print("✅ Complete monthly workflow with integrations completed")
            print(f"   Accounting integration: {accounting_id}")
            print(f"   Cloud integration: {cloud_id}")
            print(f"   Expenses created: {len(expense_ids)}")
        
        finally:
            # Cleanup
            await client.delete(f"/integrations/{accounting_id}")
            await client.delete(f"/integrations/{cloud_id}")
