"""
Invoice Data Extractors
Extract structured data from OCR text: NIP, dates, amounts, etc.
"""
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, date
import structlog

logger = structlog.get_logger()


def validate_nip(nip: str) -> bool:
    """
    Validate Polish NIP (tax identification number).
    NIP has 10 digits with a checksum based on weights [6,5,7,2,3,4,5,6,7].
    """
    nip = re.sub(r'\D', '', nip)
    
    if len(nip) != 10 or not nip.isdigit():
        return False
    
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    checksum = sum(int(nip[i]) * weights[i] for i in range(9)) % 11
    
    if checksum == 10:
        return False
    
    return checksum == int(nip[9])


def validate_regon(regon: str) -> bool:
    """Validate Polish REGON (business registry number)."""
    regon = re.sub(r'\D', '', regon)
    
    if len(regon) == 9:
        weights = [8, 9, 2, 3, 4, 5, 6, 7]
        checksum = sum(int(regon[i]) * weights[i] for i in range(8)) % 11
        if checksum == 10:
            checksum = 0
        return checksum == int(regon[8])
    elif len(regon) == 14:
        if not validate_regon(regon[:9]):
            return False
        weights = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
        checksum = sum(int(regon[i]) * weights[i] for i in range(13)) % 11
        if checksum == 10:
            checksum = 0
        return checksum == int(regon[13])
    return False


class InvoiceExtractor:
    """Extract structured data from invoice text"""
    
    PATTERNS = {
        'nip': [
            r'NIP[:\s]*(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})',
            r'NIP[:\s]*(\d{10})',
        ],
        'regon': [r'REGON[:\s]*(\d{9}|\d{14})'],
        'invoice_number': [
            r'(?:Faktura\s+(?:VAT\s+)?(?:nr|numer)?[:\s]*)([\w\-/]+)',
            r'(?:Nr\s+faktury|Numer\s+faktury)[:\s]*([\w\-/]+)',
            r'(?:FV|FA|F)[:\s]*([\w\-/]+\d+[\w\-/]*)',
        ],
        'date': [
            r'(\d{2}[-./]\d{2}[-./]\d{4})',
            r'(\d{4}[-./]\d{2}[-./]\d{2})',
            r'(\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{4})',
        ],
        'amount': [
            r'(?:Razem|RAZEM|Suma|Do\s+zapłaty|Kwota)[:\s]*(\d+[\s\d]*[,\.]\d{2})\s*(?:zł|PLN)?',
            r'(?:brutto|BRUTTO)[:\s]*(\d+[\s\d]*[,\.]\d{2})\s*(?:zł|PLN)?',
        ],
        'vat_amount': [
            r'(?:VAT|Podatek\s+VAT)[:\s]*(\d+[\s\d]*[,\.]\d{2})',
            r'(?:23%|8%|5%)[:\s]*(\d+[\s\d]*[,\.]\d{2})',
        ],
        'net_amount': [
            r'(?:netto|NETTO)[:\s]*(\d+[\s\d]*[,\.]\d{2})',
            r'(?:Wartość\s+netto)[:\s]*(\d+[\s\d]*[,\.]\d{2})',
        ],
        'iban': [
            r'(PL\s?\d{2}[\s\d]{24,26})',
            r'(\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4})',
        ],
        'payment_due': [
            r'(?:Termin\s+płatności|Płatność\s+do)[:\s]*(\d{2}[-./]\d{2}[-./]\d{4})',
        ],
    }
    
    POLISH_MONTHS = {
        'stycznia': 1, 'lutego': 2, 'marca': 3, 'kwietnia': 4,
        'maja': 5, 'czerwca': 6, 'lipca': 7, 'sierpnia': 8,
        'września': 9, 'października': 10, 'listopada': 11, 'grudnia': 12
    }
    
    async def extract(self, text: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured data from invoice text."""
        result = {
            'document_type': document_type or 'invoice',
            'raw_text_length': len(text),
            'extraction_confidence': 0.0,
            'fields_found': 0,
            'fields_validated': 0,
        }
        
        # Extract NIP numbers
        nips = self._extract_nips(text)
        if nips:
            result['nip_numbers'] = nips
            if len(nips) >= 2:
                result['vendor_nip'] = nips[0]
                result['buyer_nip'] = nips[1]
            elif len(nips) == 1:
                result['vendor_nip'] = nips[0]
            result['fields_found'] += len(nips)
            result['fields_validated'] += sum(1 for n in nips if n.get('valid'))
        
        # Extract invoice number
        invoice_num = self._extract_pattern('invoice_number', text)
        if invoice_num:
            result['invoice_number'] = invoice_num
            result['fields_found'] += 1
        
        # Extract dates
        dates = self._extract_dates(text)
        if dates:
            result['dates'] = dates
            result['invoice_date'] = dates[0]
            result['fields_found'] += len(dates)
        
        # Extract amounts
        gross = self._extract_pattern('amount', text)
        if gross:
            result['gross_amount'] = self._parse_amount(gross)
            result['fields_found'] += 1
        
        net = self._extract_pattern('net_amount', text)
        if net:
            result['net_amount'] = self._parse_amount(net)
            result['fields_found'] += 1
        
        vat = self._extract_pattern('vat_amount', text)
        if vat:
            result['vat_amount'] = self._parse_amount(vat)
            result['fields_found'] += 1
        
        # Extract vendor name
        vendor_name = self._extract_vendor_name(text)
        if vendor_name:
            result['vendor_name'] = vendor_name
        
        # Extract IBAN
        iban = self._extract_pattern('iban', text)
        if iban:
            result['bank_account'] = iban.replace(' ', '')
            result['fields_found'] += 1
        
        # Calculate confidence
        if result['fields_found'] > 0:
            result['extraction_confidence'] = min(
                result['fields_validated'] / result['fields_found'] * 0.5 + 
                min(result['fields_found'] / 5, 1.0) * 0.5,
                1.0
            )
        
        logger.info("Data extracted", fields=result['fields_found'], confidence=result['extraction_confidence'])
        return result
    
    def _extract_nips(self, text: str) -> List[Dict[str, Any]]:
        """Extract and validate all NIP numbers."""
        nips = []
        seen = set()
        
        for pattern in self.PATTERNS['nip']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                nip_raw = match.group(1)
                nip_clean = re.sub(r'\D', '', nip_raw)
                
                if nip_clean not in seen and len(nip_clean) == 10:
                    seen.add(nip_clean)
                    is_valid = validate_nip(nip_clean)
                    nips.append({
                        'raw': nip_raw,
                        'cleaned': nip_clean,
                        'formatted': f"{nip_clean[:3]}-{nip_clean[3:6]}-{nip_clean[6:8]}-{nip_clean[8:]}",
                        'valid': is_valid
                    })
        return nips
    
    def _extract_pattern(self, field: str, text: str) -> Optional[str]:
        """Extract first match for a field pattern."""
        for pattern in self.PATTERNS.get(field, []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract and parse all dates from text."""
        dates = []
        seen = set()
        
        for pattern in self.PATTERNS['date']:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                parsed = self._parse_date(date_str)
                if parsed and parsed.isoformat() not in seen:
                    seen.add(parsed.isoformat())
                    dates.append(parsed.isoformat())
        return sorted(dates)
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse various Polish date formats."""
        formats = ['%d-%m-%Y', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y.%m.%d']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        for month_name, month_num in self.POLISH_MONTHS.items():
            if month_name in date_str.lower():
                match = re.search(r'(\d{1,2})\s+' + month_name + r'\s+(\d{4})', date_str.lower())
                if match:
                    try:
                        return date(int(match.group(2)), month_num, int(match.group(1)))
                    except ValueError:
                        continue
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse Polish amount format to float."""
        if not amount_str:
            return None
        cleaned = re.sub(r'[\s\xa0]', '', amount_str).replace(',', '.')
        parts = cleaned.split('.')
        if len(parts) > 2:
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _extract_vendor_name(self, text: str) -> Optional[str]:
        """Extract vendor name using heuristics."""
        lines = text.split('\n')
        patterns = [r'([\w\s]+(?:sp\.\s*z\s*o\.?\s*o\.?|s\.a\.|spółka)[\w\s]*)']
        
        for line in lines[:15]:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 3:
                        return name
        return None


def get_extractor(document_type: str = 'invoice'):
    """Factory function to get appropriate extractor."""
    return InvoiceExtractor()
