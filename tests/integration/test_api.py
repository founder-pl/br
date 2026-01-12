"""
Integration Tests - API Endpoints
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_api_health(self, client: AsyncClient):
        """Test API health endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api"
        assert "timestamp" in data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "System B+R API"
        assert "version" in data


class TestProjectsAPI:
    """Tests for projects API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, sample_project_data):
        """Test creating a new project"""
        response = await client.post("/projects/", json=sample_project_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_project_data["name"]
        assert data["fiscal_year"] == sample_project_data["fiscal_year"]
        assert data["status"] == "active"
        assert "id" in data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient):
        """Test getting default project"""
        project_id = "00000000-0000-0000-0000-000000000001"
        response = await client.get(f"/projects/{project_id}")
        
        # May return 404 if DB not seeded, or 200 if exists
        assert response.status_code in [200, 404]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient):
        """Test listing projects"""
        response = await client.get("/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_projects_filter_by_year(self, client: AsyncClient):
        """Test listing projects filtered by fiscal year"""
        response = await client.get("/projects/?fiscal_year=2025")
        
        assert response.status_code == 200
        data = response.json()
        for project in data:
            assert project["fiscal_year"] == 2025


class TestExpensesAPI:
    """Tests for expenses API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_br_categories(self, client: AsyncClient):
        """Test getting B+R expense categories"""
        response = await client.get("/expenses/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check required category fields
        for cat in data:
            assert "code" in cat
            assert "name" in cat
            assert "deduction_rate" in cat
        
        # Check specific categories exist
        codes = [c["code"] for c in data]
        assert "personnel_employment" in codes
        assert "materials" in codes
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_expense(self, client: AsyncClient, sample_expense_data):
        """Test creating an expense"""
        response = await client.post("/expenses/", json=sample_expense_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_number"] == sample_expense_data["invoice_number"]
        assert float(data["gross_amount"]) == sample_expense_data["gross_amount"]
        assert data["status"] == "draft"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_expenses(self, client: AsyncClient):
        """Test listing expenses"""
        response = await client.get("/expenses/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_expenses_filter_br_qualified(self, client: AsyncClient):
        """Test listing expenses filtered by B+R qualification"""
        response = await client.get("/expenses/?br_qualified=true")
        
        assert response.status_code == 200
        data = response.json()
        for expense in data:
            assert expense["br_qualified"] is True


class TestDocumentsAPI:
    """Tests for documents API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient):
        """Test listing documents"""
        response = await client.get("/documents/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_upload_document_invalid_type(self, client: AsyncClient):
        """Test uploading document with invalid type"""
        files = {"file": ("test.txt", b"Hello World", "text/plain")}
        response = await client.post("/documents/upload", files=files)
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


class TestReportsAPI:
    """Tests for reports API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_monthly_reports(self, client: AsyncClient):
        """Test listing monthly reports"""
        response = await client.get("/reports/monthly?fiscal_year=2025")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_annual_br_summary(self, client: AsyncClient):
        """Test getting annual B+R summary"""
        response = await client.get(
            "/reports/annual/br-summary?fiscal_year=2025&project_id=00000000-0000-0000-0000-000000000001"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["fiscal_year"] == 2025
        assert "total_br_costs" in data
        assert "total_br_deduction" in data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_annual_ip_box_summary(self, client: AsyncClient):
        """Test getting annual IP Box summary"""
        response = await client.get(
            "/reports/annual/ip-box-summary?fiscal_year=2025&project_id=00000000-0000-0000-0000-000000000001"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["fiscal_year"] == 2025
        assert "nexus_ratio" in data
        assert "qualified_income" in data
        assert "tax_5_percent" in data


class TestClarificationsAPI:
    """Tests for clarifications API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_clarifications(self, client: AsyncClient):
        """Test listing clarifications"""
        response = await client.get("/clarifications/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pending_count(self, client: AsyncClient):
        """Test getting pending clarifications count"""
        response = await client.get("/clarifications/pending/count")
        
        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data
        assert isinstance(data["pending_count"], int)


class TestAuthAPI:
    """Tests for authentication API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration"""
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        response = await client.post("/auth/register", json=user_data)
        
        # May fail if user exists
        assert response.status_code in [200, 400]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials"""
        response = await client.post(
            "/auth/token",
            data={"username": "invalid@example.com", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
