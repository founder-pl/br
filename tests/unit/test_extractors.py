"""
Unit Tests - Invoice Data Extractors
"""
import pytest
from datetime import date
from src.ocr.extractors import InvoiceExtractor, get_extractor


class TestInvoiceExtractor:
    """Tests for invoice data extraction"""
    
    @pytest.fixture
    def extractor(self):
        return InvoiceExtractor()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_nip_from_text(self, extractor, sample_invoice_text):
        """Test NIP extraction from invoice text"""
        result = await extractor.extract(sample_invoice_text)
        
        assert "nip_numbers" in result
        assert len(result["nip_numbers"]) >= 1
        # Check vendor NIP
        nips = [n["cleaned"] for n in result["nip_numbers"]]
        assert "1234567890" in nips or "5881918662" in nips
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_invoice_number(self, extractor, sample_invoice_text):
        """Test invoice number extraction"""
        result = await extractor.extract(sample_invoice_text)
        
        assert "invoice_number" in result
        assert "FV/2025/01/001" in result.get("invoice_number", "")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_dates(self, extractor, sample_invoice_text):
        """Test date extraction from invoice"""
        result = await extractor.extract(sample_invoice_text)
        
        assert "dates" in result
        assert len(result["dates"]) >= 1
        # Should contain 2025-01-15
        assert any("2025-01-15" in d for d in result["dates"])
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_amounts(self, extractor, sample_invoice_text):
        """Test amount extraction from invoice"""
        result = await extractor.extract(sample_invoice_text)
        
        # Should find gross amount
        assert result.get("gross_amount") is not None or "amounts" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extraction_confidence(self, extractor, sample_invoice_text):
        """Test extraction confidence score"""
        result = await extractor.extract(sample_invoice_text)
        
        assert "extraction_confidence" in result
        assert 0 <= result["extraction_confidence"] <= 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extract_empty_text(self, extractor):
        """Test extraction from empty text"""
        result = await extractor.extract("")
        
        assert result["fields_found"] == 0
        assert result["extraction_confidence"] == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_type_default(self, extractor):
        """Test default document type"""
        result = await extractor.extract("Some text")
        
        assert result["document_type"] == "invoice"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_document_type_override(self, extractor):
        """Test document type override"""
        result = await extractor.extract("Some text", document_type="receipt")
        
        assert result["document_type"] == "receipt"


class TestDateParsing:
    """Tests for Polish date format parsing"""
    
    @pytest.fixture
    def extractor(self):
        return InvoiceExtractor()
    
    @pytest.mark.unit
    def test_parse_date_dd_mm_yyyy_dot(self, extractor):
        """Test parsing DD.MM.YYYY format"""
        result = extractor._parse_date("15.01.2025")
        assert result == date(2025, 1, 15)
    
    @pytest.mark.unit
    def test_parse_date_dd_mm_yyyy_dash(self, extractor):
        """Test parsing DD-MM-YYYY format"""
        result = extractor._parse_date("15-01-2025")
        assert result == date(2025, 1, 15)
    
    @pytest.mark.unit
    def test_parse_date_yyyy_mm_dd(self, extractor):
        """Test parsing YYYY-MM-DD format"""
        result = extractor._parse_date("2025-01-15")
        assert result == date(2025, 1, 15)
    
    @pytest.mark.unit
    def test_parse_date_polish_month(self, extractor):
        """Test parsing date with Polish month name"""
        result = extractor._parse_date("15 stycznia 2025")
        assert result == date(2025, 1, 15)
    
    @pytest.mark.unit
    def test_parse_invalid_date(self, extractor):
        """Test parsing invalid date"""
        result = extractor._parse_date("not a date")
        assert result is None


class TestAmountParsing:
    """Tests for Polish amount format parsing"""
    
    @pytest.fixture
    def extractor(self):
        return InvoiceExtractor()
    
    @pytest.mark.unit
    def test_parse_amount_comma_decimal(self, extractor):
        """Test parsing amount with comma decimal"""
        result = extractor._parse_amount("1230,00")
        assert result == 1230.00
    
    @pytest.mark.unit
    def test_parse_amount_dot_decimal(self, extractor):
        """Test parsing amount with dot decimal"""
        result = extractor._parse_amount("1230.00")
        assert result == 1230.00
    
    @pytest.mark.unit
    def test_parse_amount_with_spaces(self, extractor):
        """Test parsing amount with thousand separator spaces"""
        result = extractor._parse_amount("1 230,00")
        assert result == 1230.00
    
    @pytest.mark.unit
    def test_parse_amount_large(self, extractor):
        """Test parsing large amount"""
        result = extractor._parse_amount("123 456 789,99")
        assert result == 123456789.99
    
    @pytest.mark.unit
    def test_parse_amount_empty(self, extractor):
        """Test parsing empty amount"""
        result = extractor._parse_amount("")
        assert result is None
    
    @pytest.mark.unit
    def test_parse_amount_none(self, extractor):
        """Test parsing None amount"""
        result = extractor._parse_amount(None)
        assert result is None


class TestExtractorFactory:
    """Tests for extractor factory function"""
    
    @pytest.mark.unit
    def test_get_invoice_extractor(self):
        """Test getting invoice extractor"""
        extractor = get_extractor("invoice")
        assert isinstance(extractor, InvoiceExtractor)
    
    @pytest.mark.unit
    def test_get_default_extractor(self):
        """Test getting default extractor"""
        extractor = get_extractor()
        assert isinstance(extractor, InvoiceExtractor)
    
    @pytest.mark.unit
    def test_get_unknown_extractor(self):
        """Test getting unknown extractor type falls back to invoice"""
        extractor = get_extractor("unknown")
        assert isinstance(extractor, InvoiceExtractor)
