"""Tests for invoice type detection (cost vs revenue)."""
import pytest
from src.api.routers.documents import detect_invoice_type


class TestInvoiceTypeDetection:
    """Test suite for detect_invoice_type function."""
    
    OUR_NIP = "5881918662"
    
    def test_cost_invoice_vendor_nip_different(self):
        """Invoice from external vendor should be detected as expense."""
        data = {
            "vendor_nip": "1234567890",
            "buyer_nip": self.OUR_NIP,
            "gross_amount": 100.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "expense"
    
    def test_revenue_invoice_we_are_seller(self):
        """Invoice where we are seller should be detected as revenue."""
        data = {
            "vendor_nip": self.OUR_NIP,
            "buyer_nip": "9876543210",
            "gross_amount": 500.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "revenue"
    
    def test_cost_invoice_seller_nip_field(self):
        """Test with seller_nip field instead of vendor_nip."""
        data = {
            "seller_nip": "5542926469",
            "nip_nabywcy": self.OUR_NIP,
            "gross_amount": 55.09
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "expense"
    
    def test_revenue_invoice_nip_sprzedawcy_field(self):
        """Test with Polish field names."""
        data = {
            "nip_sprzedawcy": self.OUR_NIP,
            "nip_nabywcy": "1111111111",
            "kwota_brutto": 1500.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "revenue"
    
    def test_cost_invoice_no_buyer_nip(self):
        """Invoice with no buyer NIP but different seller should be expense."""
        data = {
            "vendor_nip": "2222222222",
            "gross_amount": 200.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "expense"
    
    def test_revenue_invoice_nip_with_dashes(self):
        """NIP with formatting should still match."""
        data = {
            "vendor_nip": "588-191-86-62",  # Same as OUR_NIP with dashes
            "buyer_nip": "999-888-77-66",
            "gross_amount": 300.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "revenue"
    
    def test_cost_invoice_empty_nips(self):
        """Invoice with empty NIPs defaults to expense."""
        data = {
            "vendor_nip": "",
            "buyer_nip": "",
            "gross_amount": 50.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "expense"
    
    def test_cost_invoice_none_nips(self):
        """Invoice with None NIPs defaults to expense."""
        data = {
            "vendor_nip": None,
            "buyer_nip": None,
            "gross_amount": 75.0
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "expense"
    
    def test_revenue_from_ocr_text_hint(self):
        """Test detection from OCR text hints."""
        data = {
            "vendor_nip": None,
            "ocr_text": "FAKTURA VAT SPRZEDAŻ nr FV/2025/001"
        }
        assert detect_invoice_type(data, self.OUR_NIP) == "revenue"


# Sample invoice data for e2e testing
SAMPLE_COST_INVOICE = {
    "invoice_number": "FV/2025/COST/001",
    "invoice_date": "2025-12-15",
    "vendor_name": "Test Vendor Sp. z o.o.",
    "vendor_nip": "5542926469",
    "buyer_name": "Tomasz Sapletta",
    "buyer_nip": "5881918662",
    "net_amount": 1000.00,
    "vat_amount": 230.00,
    "gross_amount": 1230.00,
    "currency": "PLN",
    "description": "Usługi programistyczne - rozwój prototypu"
}

SAMPLE_REVENUE_INVOICE = {
    "invoice_number": "FV/2025/REV/001", 
    "invoice_date": "2025-12-20",
    "vendor_name": "Tomasz Sapletta",
    "vendor_nip": "5881918662",
    "buyer_name": "Klient ABC Sp. z o.o.",
    "buyer_nip": "1234567890",
    "net_amount": 5000.00,
    "vat_amount": 1150.00,
    "gross_amount": 6150.00,
    "currency": "PLN",
    "description": "Licencja na oprogramowanie B+R"
}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
