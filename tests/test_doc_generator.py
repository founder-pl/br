"""
Tests for Document Generator Module
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestTemplateRegistry:
    """Tests for TemplateRegistry"""
    
    def test_list_templates(self):
        from src.doc_generator.templates import get_template_registry
        
        registry = get_template_registry()
        templates = registry.list_templates()
        
        assert len(templates) >= 7
        assert all('id' in t for t in templates)
        assert all('name' in t for t in templates)
        assert all('category' in t for t in templates)
    
    def test_get_template_by_id(self):
        from src.doc_generator.templates import get_template_registry
        
        registry = get_template_registry()
        template = registry.get('project_card')
        
        assert template is not None
        assert template.id == 'project_card'
        assert template.name == 'Karta Projektowa B+R'
        assert len(template.data_requirements) > 0
    
    def test_template_categories(self):
        from src.doc_generator.templates import get_template_registry, DocumentCategory
        
        registry = get_template_registry()
        
        for category in DocumentCategory:
            templates = registry.get_by_category(category)
            assert isinstance(templates, list)
    
    def test_template_required_params(self):
        from src.doc_generator.templates import get_template_registry
        
        registry = get_template_registry()
        template = registry.get('timesheet_monthly')
        
        required = template.get_required_params()
        assert 'project_id' in required
        assert 'year' in required
        assert 'month' in required


class TestDataSourceRegistry:
    """Tests for DataSourceRegistry"""
    
    def test_list_sources(self):
        from src.doc_generator.data_sources import get_data_registry
        
        registry = get_data_registry()
        sources = registry.list_sources()
        
        assert len(sources) >= 9
        assert all('name' in s for s in sources)
        assert all('type' in s for s in sources)
    
    def test_get_source_by_name(self):
        from src.doc_generator.data_sources import get_data_registry
        
        registry = get_data_registry()
        source = registry.get('project_info')
        
        assert source is not None
        assert source.name == 'project_info'
    
    def test_sql_source_schema(self):
        from src.doc_generator.data_sources import get_data_registry
        
        registry = get_data_registry()
        source = registry.get('expenses_summary')
        schema = source.get_schema()
        
        assert schema['type'] == 'sql'
        assert 'params' in schema
        assert 'project_id' in schema['params']


class TestTemplateRenderer:
    """Tests for TemplateRenderer"""
    
    def test_render_variables(self):
        from src.doc_generator.engine import TemplateRenderer
        
        renderer = TemplateRenderer()
        template = "Hello {{name}}!"
        context = {"name": "World"}
        
        result = renderer.render(template, context)
        assert result == "Hello World!"
    
    def test_render_nested_variables(self):
        from src.doc_generator.engine import TemplateRenderer
        
        renderer = TemplateRenderer()
        template = "Project: {{project.name}}"
        context = {"project": {"name": "Test Project"}}
        
        result = renderer.render(template, context)
        assert result == "Project: Test Project"
    
    def test_render_filter_format_currency(self):
        from src.doc_generator.engine import TemplateRenderer
        
        renderer = TemplateRenderer()
        template = "Amount: {{amount|format_currency}}"
        context = {"amount": 1234.56}
        
        result = renderer.render(template, context)
        assert "1 234,56" in result or "1234,56" in result
    
    def test_render_for_loop(self):
        from src.doc_generator.engine import TemplateRenderer
        
        renderer = TemplateRenderer()
        template = "{% for item in items %}{{item}},{% endfor %}"
        context = {"items": ["a", "b", "c"]}
        
        result = renderer.render(template, context)
        assert result == "a,b,c,"
    
    def test_render_if_condition(self):
        from src.doc_generator.engine import TemplateRenderer
        
        renderer = TemplateRenderer()
        template = "{% if show %}visible{% endif %}"
        
        result_true = renderer.render(template, {"show": True})
        result_false = renderer.render(template, {"show": False})
        
        assert result_true == "visible"
        assert result_false == ""
    
    def test_render_if_else(self):
        from src.doc_generator.engine import TemplateRenderer
        
        renderer = TemplateRenderer()
        template = "{% if active %}ON{% else %}OFF{% endif %}"
        
        result_on = renderer.render(template, {"active": True})
        result_off = renderer.render(template, {"active": False})
        
        assert result_on == "ON"
        assert result_off == "OFF"


class TestDocumentEngine:
    """Tests for DocumentEngine"""
    
    def test_list_templates(self):
        from src.doc_generator.engine import get_doc_engine
        
        engine = get_doc_engine()
        # Need to run async
        import asyncio
        templates = asyncio.get_event_loop().run_until_complete(engine.list_templates())
        
        assert len(templates) >= 7
    
    def test_get_template(self):
        from src.doc_generator.engine import get_doc_engine
        
        engine = get_doc_engine()
        import asyncio
        template = asyncio.get_event_loop().run_until_complete(
            engine.get_template('project_card')
        )
        
        assert template is not None
        assert template['id'] == 'project_card'
        assert 'template_content' in template
        assert 'data_requirements' in template
    
    def test_get_demo_document(self):
        from src.doc_generator.engine import get_doc_engine
        
        engine = get_doc_engine()
        import asyncio
        demo = asyncio.get_event_loop().run_until_complete(
            engine.get_demo_document('project_card')
        )
        
        assert demo is not None
        assert 'content' in demo
        assert demo['is_demo'] == True
    
    def test_build_context(self):
        from src.doc_generator.engine import DocumentEngine
        from src.doc_generator.templates import get_template_registry
        
        engine = DocumentEngine()
        template = get_template_registry().get('project_card')
        
        params = {"project_id": "test-123", "year": 2025}
        data = {
            "project_info": [{"name": "Test Project", "code": "TP-001"}],
            "expenses_by_category": [
                {"category": "materials", "count": 5, "total_gross": 1000}
            ]
        }
        
        context = engine._build_context(template, params, data)
        
        assert 'project' in context
        assert context['project']['name'] == "Test Project"
        assert 'expenses_by_category' in context
        assert 'generated_date' in context


class TestFormatHelpers:
    """Tests for format helper functions"""
    
    def test_format_currency(self):
        from src.doc_generator.engine import format_currency
        
        assert "zł" in format_currency(1000)
        assert format_currency(None) == "0,00 zł"
        assert format_currency(0) == "0,00 zł"
    
    def test_format_date(self):
        from src.doc_generator.engine import format_date
        
        assert format_date(None) == ""
        assert format_date("2025-01-15") == "2025-01-15"
        assert format_date(datetime(2025, 1, 15)) == "2025-01-15"


# Integration tests (require database)
@pytest.mark.asyncio
class TestDocGeneratorAPI:
    """Integration tests for doc-generator API endpoints"""
    
    async def test_list_templates_endpoint(self, test_client):
        """Test GET /doc-generator/templates"""
        response = await test_client.get("/doc-generator/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert "templates" in data
        assert "total" in data
        assert data["total"] >= 7
    
    async def test_get_template_detail(self, test_client):
        """Test GET /doc-generator/templates/{id}"""
        response = await test_client.get("/doc-generator/templates/project_card")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "project_card"
        assert "template_content" in data
    
    async def test_get_template_not_found(self, test_client):
        """Test GET /doc-generator/templates/{id} with invalid id"""
        response = await test_client.get("/doc-generator/templates/nonexistent")
        assert response.status_code == 404
    
    async def test_list_data_sources(self, test_client):
        """Test GET /doc-generator/data-sources"""
        response = await test_client.get("/doc-generator/data-sources")
        assert response.status_code == 200
        
        data = response.json()
        assert "sources" in data
        assert len(data["sources"]) >= 9
    
    async def test_get_demo_document(self, test_client):
        """Test GET /doc-generator/demo/{id}"""
        response = await test_client.get("/doc-generator/demo/project_card")
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data
        assert data["is_demo"] == True
    
    async def test_filter_options(self, test_client):
        """Test GET /doc-generator/filter-options"""
        response = await test_client.get("/doc-generator/filter-options")
        assert response.status_code == 200
        
        data = response.json()
        assert "years" in data
        assert "months" in data
        assert "projects" in data


# Fixture for test client (if using pytest-asyncio)
@pytest.fixture
def test_client():
    """Create test client - skip if dependencies not available"""
    pytest.skip("Integration tests require running API server")
