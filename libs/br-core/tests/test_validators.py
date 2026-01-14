"""Tests for br_core validators"""
import pytest
from br_core.validators import (
    validate_nip,
    validate_date_range,
    validate_fiscal_year,
    validate_amount,
    validate_nexus,
)


class TestValidateNIP:
    """Tests for NIP validation"""
    
    def test_valid_nip(self):
        # Valid NIP: 5881918662
        valid, error = validate_nip("5881918662")
        assert valid is True
        assert error is None
    
    def test_valid_nip_with_separators(self):
        valid, error = validate_nip("588-191-86-62")
        assert valid is True
        assert error is None
    
    def test_invalid_nip_wrong_checksum(self):
        valid, error = validate_nip("5881918661")
        assert valid is False
        assert "suma kontrolna" in error.lower()
    
    def test_invalid_nip_too_short(self):
        valid, error = validate_nip("12345")
        assert valid is False
        assert "10 cyfr" in error
    
    def test_invalid_nip_empty(self):
        valid, error = validate_nip("")
        assert valid is False
        assert "pusty" in error.lower()
    
    def test_invalid_nip_non_numeric(self):
        valid, error = validate_nip("ABCD123456")
        assert valid is False


class TestValidateDateRange:
    """Tests for date range validation"""
    
    def test_valid_date_range(self):
        valid, error = validate_date_range("2025-01-01", "2025-12-31")
        assert valid is True
        assert error is None
    
    def test_same_date(self):
        valid, error = validate_date_range("2025-06-15", "2025-06-15")
        assert valid is True
    
    def test_invalid_range_reversed(self):
        valid, error = validate_date_range("2025-12-31", "2025-01-01")
        assert valid is False
        assert "późniejsza" in error


class TestValidateFiscalYear:
    """Tests for fiscal year validation"""
    
    def test_valid_current_year(self):
        valid, error = validate_fiscal_year(2025)
        assert valid is True
    
    def test_valid_past_year(self):
        valid, error = validate_fiscal_year(2020)
        assert valid is True
    
    def test_invalid_too_old(self):
        valid, error = validate_fiscal_year(2003)
        assert valid is False
        assert "2004" in error
    
    def test_invalid_future_year(self):
        valid, error = validate_fiscal_year(2030, allow_future=False)
        assert valid is False
        assert "przyszłości" in error


class TestValidateNexus:
    """Tests for Nexus indicator validation"""
    
    def test_valid_nexus(self):
        valid, error = validate_nexus(0.85)
        assert valid is True
    
    def test_nexus_exactly_one(self):
        valid, error = validate_nexus(1.0)
        assert valid is True
    
    def test_invalid_nexus_greater_than_one(self):
        valid, error = validate_nexus(1.5)
        assert valid is False
        assert "przekraczać 1.0" in error
    
    def test_invalid_nexus_negative(self):
        valid, error = validate_nexus(-0.1)
        assert valid is False
        assert "ujemny" in error
