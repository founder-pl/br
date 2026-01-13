"""
E2E Tests for Document Generator API

Run with: pytest tests/test_doc_generator_e2e.py -v
"""
import pytest
import httpx
import asyncio

API_BASE = "http://localhost:8020"
PROJECT_ID = "00000000-0000-0000-0000-000000000001"


class TestDocGeneratorE2E:
    """End-to-end tests for document generator API"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=API_BASE, timeout=30.0)
    
    def test_list_templates(self, client):
        """Test GET /doc-generator/templates"""
        response = client.get("/doc-generator/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert "templates" in data
        assert data["total"] >= 7
        
        template_ids = [t["id"] for t in data["templates"]]
        assert "project_card" in template_ids
        assert "expense_registry" in template_ids
    
    def test_get_filter_options(self, client):
        """Test GET /doc-generator/filter-options"""
        response = client.get("/doc-generator/filter-options")
        assert response.status_code == 200
        
        data = response.json()
        assert "years" in data
        assert "months" in data
        assert "projects" in data
        assert len(data["months"]) == 12
    
    def test_get_template_detail(self, client):
        """Test GET /doc-generator/templates/{id}"""
        response = client.get("/doc-generator/templates/project_card")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "project_card"
        assert "template_content" in data
        assert "data_requirements" in data
    
    def test_get_demo_document(self, client):
        """Test GET /doc-generator/demo/{id}"""
        response = client.get("/doc-generator/demo/project_card")
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data
        assert data["is_demo"] == True
        assert len(data["content"]) > 100
    
    def test_preview_data(self, client):
        """Test POST /doc-generator/preview-data"""
        response = client.post("/doc-generator/preview-data", json={
            "template_id": "project_card",
            "params": {"project_id": PROJECT_ID}
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "params" in data
    
    def test_generate_project_card(self, client):
        """Test POST /doc-generator/generate - project_card"""
        response = client.post("/doc-generator/generate", json={
            "template_id": "project_card",
            "params": {"project_id": PROJECT_ID},
            "use_llm": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_id"] == "project_card"
        assert "content" in data
        assert len(data["content"]) > 100
        assert "KARTA PROJEKTOWA" in data["content"]
    
    def test_generate_expense_registry(self, client):
        """Test POST /doc-generator/generate - expense_registry"""
        response = client.post("/doc-generator/generate", json={
            "template_id": "expense_registry",
            "params": {"project_id": PROJECT_ID},
            "use_llm": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_id"] == "expense_registry"
        assert "content" in data
        assert len(data["content"]) > 100
    
    def test_generate_nexus_calculation(self, client):
        """Test POST /doc-generator/generate - nexus_calculation"""
        response = client.post("/doc-generator/generate", json={
            "template_id": "nexus_calculation",
            "params": {"project_id": PROJECT_ID},
            "use_llm": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_id"] == "nexus_calculation"
        assert "content" in data
    
    def test_generate_br_annual_summary(self, client):
        """Test POST /doc-generator/generate - br_annual_summary"""
        response = client.post("/doc-generator/generate", json={
            "template_id": "br_annual_summary",
            "params": {"project_id": PROJECT_ID, "year": 2025},
            "use_llm": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_id"] == "br_annual_summary"
        assert "content" in data
    
    def test_generate_ip_box_procedure(self, client):
        """Test POST /doc-generator/generate - ip_box_procedure"""
        response = client.post("/doc-generator/generate", json={
            "template_id": "ip_box_procedure",
            "params": {"project_id": PROJECT_ID},
            "use_llm": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_id"] == "ip_box_procedure"
        assert "content" in data
        assert "IP Box" in data["content"] or "IP BOX" in data["content"]
    
    def test_generate_all_templates(self, client):
        """Test generating all available templates"""
        templates_response = client.get("/doc-generator/templates")
        templates = templates_response.json()["templates"]
        
        results = []
        for template in templates:
            response = client.post("/doc-generator/generate", json={
                "template_id": template["id"],
                "params": {"project_id": PROJECT_ID, "year": 2025, "month": 12},
                "use_llm": False
            })
            
            results.append({
                "id": template["id"],
                "status": response.status_code,
                "has_content": len(response.json().get("content", "")) > 50,
                "errors": response.json().get("errors")
            })
        
        # All should return 200
        for r in results:
            assert r["status"] == 200, f"Template {r['id']} failed: {r}"
            assert r["has_content"], f"Template {r['id']} has no content"
        
        print(f"Tested {len(results)} templates successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
