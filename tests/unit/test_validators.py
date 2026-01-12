"""
Unit Tests - NIP and REGON Validation
"""
import pytest
from src.ocr.extractors import validate_nip, validate_regon


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
