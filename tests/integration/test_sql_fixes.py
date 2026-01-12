"""
Integration Tests - SQL Fixes Verification
Tests to verify that text() wrapper is correctly applied to all SQL queries
"""
import pytest
from httpx import AsyncClient


class TestProjectsSQL:
    """Verify SQL fixes in projects router"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_project_sql(self, client: AsyncClient):
        """Test that project creation uses text() correctly"""
        project_data = {
            "name": "SQL Test Project",
            "description": "Testing SQL text() wrapper",
            "fiscal_year": 2025
        }
        response = await client.post("/projects/", json=project_data)
        
        # Should not get 500 error from SQL issues
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == project_data["name"]
        
        # Store project_id for cleanup
        project_id = data["id"]
        
        # Test get project
        get_response = await client.get(f"/projects/{project_id}")
        assert get_response.status_code == 200
        
        # Test update project
        update_response = await client.put(
            f"/projects/{project_id}", 
            json={"name": "Updated SQL Test Project"}
        )
        assert update_response.status_code == 200
        
        # Test project summary
        summary_response = await client.get(f"/projects/{project_id}/summary")
        assert summary_response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_projects_with_filters_sql(self, client: AsyncClient):
        """Test that list projects with filters uses text() correctly"""
        response = await client.get("/projects/?fiscal_year=2025")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        response = await client.get("/projects/?status=active")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDocumentsSQL:
    """Verify SQL fixes in documents router"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_documents_sql(self, client: AsyncClient):
        """Test that list documents uses text() correctly"""
        response = await client.get("/documents/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_documents_with_filters_sql(self, client: AsyncClient):
        """Test that list documents with filters uses text() correctly"""
        response = await client.get("/documents/?status=pending")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestExpensesSQL:
    """Verify SQL fixes in expenses router"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_expenses_sql(self, client: AsyncClient):
        """Test that list expenses uses text() correctly"""
        response = await client.get("/expenses/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_expenses_categories_sql(self, client: AsyncClient):
        """Test that expenses categories endpoint works"""
        response = await client.get("/expenses/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestReportsSQL:
    """Verify SQL fixes in reports router"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_monthly_reports_sql(self, client: AsyncClient):
        """Test that monthly reports uses text() correctly"""
        response = await client.get("/reports/monthly?fiscal_year=2025")
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_annual_br_summary_sql(self, client: AsyncClient):
        """Test that annual B+R summary uses text() correctly"""
        response = await client.get(
            "/reports/annual/br-summary?fiscal_year=2025&project_id=00000000-0000-0000-0000-000000000001"
        )
        # May be 200 or 404 depending on data, but not 500
        assert response.status_code in [200, 404]


class TestClarificationsSQL:
    """Verify SQL fixes in clarifications router"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_clarifications_sql(self, client: AsyncClient):
        """Test that list clarifications uses text() correctly"""
        response = await client.get("/clarifications/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pending_count_sql(self, client: AsyncClient):
        """Test that pending count uses text() correctly"""
        response = await client.get("/clarifications/pending/count")
        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data


class TestAuthSQL:
    """Verify SQL fixes in auth router"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_register_user_sql(self, client: AsyncClient):
        """Test that user registration uses text() correctly"""
        import uuid
        user_data = {
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "testpassword123",
            "full_name": "SQL Test User"
        }
        response = await client.post("/auth/register", json=user_data)
        # Should be 200 (created) or 400 (exists), not 500
        assert response.status_code in [200, 400]
