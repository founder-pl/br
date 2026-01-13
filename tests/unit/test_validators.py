"""
Unit Tests - NIP, REGON, Invoice and Currency Validation
"""
import pytest
from src.ocr.extractors import validate_nip, validate_regon
from src.api.validators.invoice_validator import InvoiceValidator, InvoiceValidationResult


class TestNIPValidation:
    """Tests for Polish NIP (tax identification number) validation"""
    
    @pytest.mark.unit
    def test_valid_nip_tomasz_sapletta(self):
        """Test valid NIP - Tomasz Sapletta"""
        assert validate_nip("5881918662") is True
    
    @pytest.mark.unit
    def test_valid_nip_with_dashes(self):
        """Test valid NIP with dashes"""
        assert validate_nip("588-191-86-62") is True
    
    @pytest.mark.unit
    def test_valid_nip_with_spaces(self):
        """Test valid NIP with spaces"""
        assert validate_nip("588 191 86 62") is True
    
    @pytest.mark.unit
    def test_invalid_nip_wrong_checksum(self):
        """Test invalid NIP - wrong checksum"""
        assert validate_nip("1234567890") is False
    
    @pytest.mark.unit
    def test_invalid_nip_too_short(self):
        """Test invalid NIP - too short"""
        assert validate_nip("123456789") is False
    
    @pytest.mark.unit
    def test_invalid_nip_too_long(self):
        """Test invalid NIP - too long"""
        assert validate_nip("12345678901") is False
    
    @pytest.mark.unit
    def test_invalid_nip_all_zeros(self):
        """Test invalid NIP - all zeros"""
        assert validate_nip("0000000000") is False
    
    @pytest.mark.unit
    def test_invalid_nip_letters(self):
        """Test invalid NIP - contains letters"""
        assert validate_nip("588A918662") is False
    
    @pytest.mark.unit
    def test_empty_nip(self):
        """Test empty NIP"""
        assert validate_nip("") is False
    
    @pytest.mark.unit
    @pytest.mark.parametrize("nip,expected", [
        ("5881918662", True),
        ("5252344078", True),
        ("8232197954", True),
        ("1111111111", False),
        ("9999999999", False),
    ])
    def test_various_nips(self, nip, expected):
        """Parametrized test for various NIPs"""
        assert validate_nip(nip) is expected


class TestREGONValidation:
    """Tests for Polish REGON validation"""
    
    @pytest.mark.unit
    def test_valid_regon_9_digit(self):
        """Test valid 9-digit REGON"""
        # Example valid REGON
        assert validate_regon("220665410") is True
    
    @pytest.mark.unit
    def test_invalid_regon_wrong_checksum(self):
        """Test invalid REGON - wrong checksum"""
        assert validate_regon("123456789") is False
    
    @pytest.mark.unit
    def test_invalid_regon_too_short(self):
        """Test invalid REGON - too short"""
        assert validate_regon("12345678") is False
    
    @pytest.mark.unit
    def test_invalid_regon_wrong_length(self):
        """Test invalid REGON - wrong length (not 9 or 14)"""
        assert validate_regon("1234567890") is False
    
    @pytest.mark.unit
    def test_empty_regon(self):
        """Test empty REGON"""
        assert validate_regon("") is False


class TestInvoiceValidator:
    """Tests for Polish invoice number validation"""
    
    @pytest.fixture
    def validator(self):
        return InvoiceValidator()
    
    @pytest.mark.unit
    def test_valid_invoice_fv_format(self, validator):
        """Test valid invoice number in FV format"""
        result = validator.validate("FV/123/01/2025")
        assert result.is_valid is True
        assert result.normalized_number == "FV/123/01/2025"
    
    @pytest.mark.unit
    def test_valid_invoice_numeric_format(self, validator):
        """Test valid invoice number in numeric format"""
        result = validator.validate("269/11/2025")
        assert result.is_valid is True
    
    @pytest.mark.unit
    def test_valid_invoice_alphanumeric(self, validator):
        """Test valid alphanumeric invoice number"""
        result = validator.validate("SVFOB8UM-0001")
        assert result.is_valid is True
    
    @pytest.mark.unit
    def test_generic_invoice_faktury(self, validator):
        """Test generic 'faktury' is rejected"""
        result = validator.validate("faktury")
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "Generyczny" in result.errors[0]
    
    @pytest.mark.unit
    def test_generic_invoice_sprzedazy(self, validator):
        """Test generic 'sprzedazy' is rejected"""
        result = validator.validate("sprzedazy")
        assert result.is_valid is False
    
    @pytest.mark.unit
    def test_generic_invoice_short_number(self, validator):
        """Test short numbers (1-3 digits) are rejected"""
        result = validator.validate("123")
        assert result.is_valid is False
    
    @pytest.mark.unit
    def test_empty_invoice(self, validator):
        """Test empty invoice number"""
        result = validator.validate("")
        assert result.is_valid is False
        assert "Brak numeru faktury" in result.errors[0]
    
    @pytest.mark.unit
    def test_none_invoice(self, validator):
        """Test None invoice number"""
        result = validator.validate(None)
        assert result.is_valid is False
    
    @pytest.mark.unit
    def test_is_generic_helper(self, validator):
        """Test is_generic helper method"""
        assert validator.is_generic("faktury") is True
        assert validator.is_generic("FV/123/01/2025") is False
        assert validator.is_generic(None) is True
    
    @pytest.mark.unit
    @pytest.mark.parametrize("invoice,expected_valid", [
        ("FV/123/01/2025", True),
        ("269/11/2025", True),
        ("SVFOB8UM-0001", True),
        ("12345678", True),  # Long numeric ID
        ("faktury", False),
        ("sprzedazy", False),
        ("brak", False),
        ("123", False),
        ("", False),
    ])
    def test_various_invoice_numbers(self, validator, invoice, expected_valid):
        """Parametrized test for various invoice numbers"""
        result = validator.validate(invoice)
        assert result.is_valid is expected_valid
