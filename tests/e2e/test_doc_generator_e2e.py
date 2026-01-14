"""
E2E tests for Document Generator page.

Tests the full flow:
- Document generation
- HTML rendering
- Data correctness
- Variable verification

Target URL: http://localhost:81/?page=doc-generator&logs_tab=api&year=2025&month=12
"""
import asyncio
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import pytest
import httpx

# Test configuration
BASE_URL = "http://localhost:81"
API_BASE = f"{BASE_URL}/api"
DOC_GENERATOR_PAGE = f"{BASE_URL}/?page=doc-generator&logs_tab=api&year=2025&month=12"

# Expected document structure patterns
DOCUMENT_PATTERNS = {
    "project_card": {
        "required_sections": [
            r"#\s+Karta\s+Projekt",
            r"##\s+Identyfikacja",
            r"##\s+(Opis|Cel)",
            r"##\s+(Zespół|Pracownicy)",
            r"##\s+Koszty",
        ],
        "required_fields": [
            r"NIP[:\s]+\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            r"(Rok|Year)[:\s]+\d{4}",
        ],
    },
    "expense_registry": {
        "required_sections": [
            r"#\s+Ewidencja\s+Wydatków",
            r"##\s+Podsumowanie",
        ],
        "required_fields": [
            r"\d+[,.\s]\d{2}\s*(zł|PLN)",
        ],
    },
    "nexus_calculation": {
        "required_sections": [
            r"#\s+(Obliczenie\s+)?Nexus",
            r"##\s+Składniki",
            r"##\s+Obliczenie",
        ],
        "required_fields": [
            r"[Nn]exus[:\s]*\d+[.,]\d+",
            r"a[:\s]*\d+",
            r"b[:\s]*\d+",
        ],
    },
    "timesheet_monthly": {
        "required_sections": [
            r"#\s+(Ewidencja|Rejestr)\s+Czasu",
        ],
        "required_fields": [
            r"(godzin|hours)",
        ],
    },
}


class DocumentValidator:
    """Validates generated document content"""
    
    def __init__(self, content: str, doc_type: str):
        self.content = content
        self.doc_type = doc_type
        self.issues: List[Dict[str, Any]] = []
    
    def validate_structure(self) -> bool:
        """Validate document has required sections"""
        patterns = DOCUMENT_PATTERNS.get(self.doc_type, {})
        required_sections = patterns.get("required_sections", [])
        
        for pattern in required_sections:
            if not re.search(pattern, self.content, re.IGNORECASE):
                self.issues.append({
                    "type": "missing_section",
                    "pattern": pattern,
                    "message": f"Missing required section matching: {pattern}"
                })
        
        return len([i for i in self.issues if i["type"] == "missing_section"]) == 0
    
    def validate_fields(self) -> bool:
        """Validate document has required fields"""
        patterns = DOCUMENT_PATTERNS.get(self.doc_type, {})
        required_fields = patterns.get("required_fields", [])
        
        for pattern in required_fields:
            if not re.search(pattern, self.content, re.IGNORECASE):
                self.issues.append({
                    "type": "missing_field",
                    "pattern": pattern,
                    "message": f"Missing required field matching: {pattern}"
                })
        
        return len([i for i in self.issues if i["type"] == "missing_field"]) == 0
    
    def validate_calculations(self) -> bool:
        """Validate financial calculations are correct"""
        # Extract amounts from document
        amount_pattern = r'(\d{1,3}(?:[\s\xa0]?\d{3})*(?:[,\.]\d{2})?)\s*(?:zł|PLN)'
        amounts = []
        
        for match in re.finditer(amount_pattern, self.content):
            amount_str = match.group(1).replace(' ', '').replace('\xa0', '').replace(',', '.')
            try:
                amounts.append(float(amount_str))
            except ValueError:
                pass
        
        # Check for obvious errors (negative amounts, very large numbers)
        for amount in amounts:
            if amount < 0:
                self.issues.append({
                    "type": "invalid_amount",
                    "value": amount,
                    "message": "Negative amount found"
                })
            if amount > 100_000_000:  # 100M seems unreasonable
                self.issues.append({
                    "type": "suspicious_amount",
                    "value": amount,
                    "message": "Suspiciously large amount"
                })
        
        return len([i for i in self.issues if "amount" in i["type"]]) == 0
    
    def validate_nip(self) -> bool:
        """Validate NIP numbers in document"""
        nip_pattern = r'\b(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})\b|\b(\d{10})\b'
        
        for match in re.finditer(nip_pattern, self.content):
            nip = match.group(0).replace('-', '').replace(' ', '')
            if len(nip) == 10 and nip.isdigit():
                if not self._validate_nip_checksum(nip):
                    self.issues.append({
                        "type": "invalid_nip",
                        "value": nip,
                        "message": f"Invalid NIP checksum: {nip}"
                    })
        
        return len([i for i in self.issues if i["type"] == "invalid_nip"]) == 0
    
    def _validate_nip_checksum(self, nip: str) -> bool:
        """Validate NIP checksum"""
        weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
        checksum = sum(int(nip[i]) * weights[i] for i in range(9))
        control = checksum % 11
        return control != 10 and control == int(nip[9])
    
    def validate_nexus(self) -> bool:
        """Validate Nexus indicator value"""
        nexus_pattern = r'[Nn]exus[:\s]*(\d+[.,]\d+)'
        match = re.search(nexus_pattern, self.content)
        
        if match:
            nexus_value = float(match.group(1).replace(',', '.'))
            if nexus_value > 1.0:
                self.issues.append({
                    "type": "invalid_nexus",
                    "value": nexus_value,
                    "message": f"Nexus value exceeds 1.0: {nexus_value}"
                })
            if nexus_value < 0:
                self.issues.append({
                    "type": "invalid_nexus",
                    "value": nexus_value,
                    "message": f"Nexus value is negative: {nexus_value}"
                })
        
        return len([i for i in self.issues if i["type"] == "invalid_nexus"]) == 0
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all validations and return summary"""
        results = {
            "structure": self.validate_structure(),
            "fields": self.validate_fields(),
            "calculations": self.validate_calculations(),
            "nip": self.validate_nip(),
            "nexus": self.validate_nexus(),
        }
        
        return {
            "valid": all(results.values()),
            "results": results,
            "issues": self.issues,
            "doc_type": self.doc_type,
        }


class HTMLValidator:
    """Validates HTML rendering of documents"""
    
    def __init__(self, html_content: str):
        self.html = html_content
        self.issues: List[Dict[str, Any]] = []
    
    def validate_structure(self) -> bool:
        """Validate HTML structure"""
        # Check for basic HTML elements
        required_elements = [
            (r'<html', "Missing <html> tag"),
            (r'<head', "Missing <head> tag"),
            (r'<body', "Missing <body> tag"),
            (r'</html>', "Missing </html> closing tag"),
        ]
        
        for pattern, message in required_elements:
            if not re.search(pattern, self.html, re.IGNORECASE):
                self.issues.append({"type": "html_structure", "message": message})
        
        return len(self.issues) == 0
    
    def validate_tables(self) -> bool:
        """Validate table rendering"""
        # Check that tables are properly closed
        open_tables = len(re.findall(r'<table', self.html, re.IGNORECASE))
        close_tables = len(re.findall(r'</table>', self.html, re.IGNORECASE))
        
        if open_tables != close_tables:
            self.issues.append({
                "type": "table_mismatch",
                "message": f"Mismatched table tags: {open_tables} open, {close_tables} close"
            })
        
        # Check for empty tables
        empty_table_pattern = r'<table[^>]*>\s*</table>'
        if re.search(empty_table_pattern, self.html, re.IGNORECASE):
            self.issues.append({
                "type": "empty_table",
                "message": "Empty table found"
            })
        
        return len([i for i in self.issues if "table" in i["type"]]) == 0
    
    def validate_encoding(self) -> bool:
        """Validate proper encoding of Polish characters"""
        # Check for proper charset declaration
        if not re.search(r'charset[=\s]*["\']?utf-8', self.html, re.IGNORECASE):
            self.issues.append({
                "type": "encoding",
                "message": "Missing UTF-8 charset declaration"
            })
        
        # Check for encoding issues (common mojibake patterns)
        mojibake_patterns = [
            r'Ã\x85',  # Garbled Å
            r'Ã\x82',  # Garbled Â
            r'\xc3\x85\xc2\x82',  # Double-encoded
        ]
        
        for pattern in mojibake_patterns:
            if re.search(pattern, self.html):
                self.issues.append({
                    "type": "encoding_error",
                    "message": f"Possible encoding issue found: {pattern}"
                })
        
        return len([i for i in self.issues if "encoding" in i["type"]]) == 0
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all HTML validations"""
        results = {
            "structure": self.validate_structure(),
            "tables": self.validate_tables(),
            "encoding": self.validate_encoding(),
        }
        
        return {
            "valid": all(results.values()),
            "results": results,
            "issues": self.issues,
        }


@pytest.fixture
def http_client():
    """HTTP client for tests"""
    return httpx.AsyncClient(timeout=30.0)


@pytest.mark.asyncio
class TestDocGeneratorAPI:
    """Tests for Document Generator API"""
    
    async def test_list_templates(self, http_client):
        """Test listing available templates"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/templates")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "templates" in data
            assert len(data["templates"]) > 0
            
            # Check template structure
            for template in data["templates"]:
                assert "id" in template
                assert "name" in template
                assert "category" in template
    
    async def test_get_template_detail(self, http_client):
        """Test getting template details"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/templates/project_card")
            
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "template_content" in data
    
    async def test_list_data_sources(self, http_client):
        """Test listing data sources"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/data-sources")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "sources" in data
            # Should have at least basic B+R sources
            source_names = [s["name"] for s in data["sources"]]
            expected_sources = ["project_info", "expenses_summary", "nexus_calculation"]
            for expected in expected_sources:
                assert expected in source_names, f"Missing expected source: {expected}"
    
    async def test_generate_document(self, http_client):
        """Test document generation"""
        async with http_client:
            # First get list of projects
            response = await http_client.get(f"{API_BASE}/projects")
            
            if response.status_code != 200:
                pytest.skip("No projects available")
            
            projects = response.json()
            if not projects:
                pytest.skip("No projects available")
            
            project_id = projects[0].get("id")
            
            # Generate document
            response = await http_client.post(
                f"{API_BASE}/doc-generator/generate",
                json={
                    "template_id": "project_card",
                    "params": {
                        "project_id": project_id,
                        "year": 2025,
                    },
                    "use_llm": False,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "content" in data
            assert len(data["content"]) > 100
            
            # Validate document
            validator = DocumentValidator(data["content"], "project_card")
            result = validator.validate_all()
            
            assert result["valid"], f"Document validation failed: {result['issues']}"


@pytest.mark.asyncio
class TestDocumentValidation:
    """Tests for document content validation"""
    
    async def test_project_card_structure(self, http_client):
        """Test project card document structure"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/demo/project_card")
            
            if response.status_code != 200:
                pytest.skip("Demo not available")
            
            data = response.json()
            content = data.get("content", "")
            
            validator = DocumentValidator(content, "project_card")
            result = validator.validate_all()
            
            # Check structure
            assert result["results"]["structure"], f"Structure issues: {result['issues']}"
    
    async def test_expense_registry_calculations(self, http_client):
        """Test expense registry calculations"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/demo/expense_registry")
            
            if response.status_code != 200:
                pytest.skip("Demo not available")
            
            data = response.json()
            content = data.get("content", "")
            
            validator = DocumentValidator(content, "expense_registry")
            result = validator.validate_all()
            
            # Check calculations
            assert result["results"]["calculations"], f"Calculation issues: {result['issues']}"
    
    async def test_nexus_calculation_validity(self, http_client):
        """Test Nexus calculation document validity"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/demo/nexus_calculation")
            
            if response.status_code != 200:
                pytest.skip("Demo not available")
            
            data = response.json()
            content = data.get("content", "")
            
            validator = DocumentValidator(content, "nexus_calculation")
            result = validator.validate_all()
            
            # Nexus must be valid
            assert result["results"]["nexus"], f"Nexus issues: {result['issues']}"
    
    async def test_nip_validation(self, http_client):
        """Test NIP numbers in documents"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/demo/project_card")
            
            if response.status_code != 200:
                pytest.skip("Demo not available")
            
            data = response.json()
            content = data.get("content", "")
            
            validator = DocumentValidator(content, "project_card")
            valid = validator.validate_nip()
            
            assert valid, f"Invalid NIP found: {validator.issues}"


@pytest.mark.asyncio
class TestHTMLRendering:
    """Tests for HTML rendering"""
    
    async def test_html_structure(self, http_client):
        """Test HTML output structure"""
        async with http_client:
            # Generate markdown
            response = await http_client.get(f"{API_BASE}/doc-generator/demo/project_card")
            
            if response.status_code != 200:
                pytest.skip("Demo not available")
            
            data = response.json()
            md_content = data.get("content", "")
            
            # Convert to HTML (if endpoint exists)
            html_response = await http_client.post(
                f"{API_BASE}/doc-generator/render-html",
                json={"markdown": md_content, "template_id": "project_card"}
            )
            
            if html_response.status_code != 200:
                # Try rendering locally
                from md_render import md2html
                html = md2html(md_content, title="Test")
                
                validator = HTMLValidator(html)
                result = validator.validate_all()
                
                assert result["valid"], f"HTML validation failed: {result['issues']}"
    
    async def test_polish_encoding(self, http_client):
        """Test Polish characters are properly encoded"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/doc-generator/demo/project_card")
            
            if response.status_code != 200:
                pytest.skip("Demo not available")
            
            data = response.json()
            content = data.get("content", "")
            
            # Check for proper Polish characters
            polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']
            has_polish = any(char in content.lower() for char in polish_chars)
            
            # If document should have Polish content but doesn't, it might be encoding issue
            if "Projekt" in content or "projekt" in content:
                # Document is in Polish, should have diacritics
                assert has_polish or "B+R" in content, "Polish document missing diacritics"


@pytest.mark.asyncio
class TestVariableAPI:
    """Tests for Variable API integration"""
    
    async def test_variable_access(self, http_client):
        """Test accessing variables via API"""
        async with http_client:
            # Get projects first
            response = await http_client.get(f"{API_BASE}/projects")
            
            if response.status_code != 200 or not response.json():
                pytest.skip("No projects available")
            
            project_id = response.json()[0].get("id")
            
            # Access variable
            response = await http_client.get(
                f"{API_BASE}/project/{project_id}/variable/expenses_by_category",
                params={"path": "total_gross"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "variable" in data
                assert "verification_url" in data
    
    async def test_nexus_api(self, http_client):
        """Test Nexus calculation API"""
        async with http_client:
            response = await http_client.get(f"{API_BASE}/projects")
            
            if response.status_code != 200 or not response.json():
                pytest.skip("No projects available")
            
            project_id = response.json()[0].get("id")
            
            response = await http_client.get(
                f"{API_BASE}/project/{project_id}/nexus",
                params={"year": 2025}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "nexus" in data
                assert 0 <= data["nexus"] <= 1, f"Invalid Nexus value: {data['nexus']}"
                assert "verification_urls" in data
    
    async def test_invoice_variable(self, http_client):
        """Test invoice variable access"""
        async with http_client:
            # This would need a known invoice ID
            # For now, just test the endpoint exists
            response = await http_client.get(
                f"{API_BASE}/invoice/test-invoice/variable/gross_amount"
            )
            
            # Should return 404 for non-existent invoice, not 500
            assert response.status_code in [200, 401, 404]


@pytest.mark.asyncio
class TestDocGeneratorPage:
    """Tests for the doc-generator web page"""
    
    async def test_page_loads(self, http_client):
        """Test that the page loads"""
        async with http_client:
            response = await http_client.get(DOC_GENERATOR_PAGE)
            
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
    
    async def test_page_has_generator_ui(self, http_client):
        """Test page has document generator UI elements"""
        async with http_client:
            response = await http_client.get(DOC_GENERATOR_PAGE)
            
            if response.status_code == 200:
                html = response.text
                
                # Should have template selector or similar
                assert "template" in html.lower() or "dokument" in html.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
