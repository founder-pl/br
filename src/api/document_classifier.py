"""
Document Classifier - Auto-detect document type from OCR text
"""
import re
from typing import Dict, Any, Optional, Tuple

# Keywords for document type detection
DOCUMENT_PATTERNS = {
    'invoice': {
        'keywords': [
            'faktura', 'faktura vat', 'invoice', 'numer faktury', 'nr faktury',
            'data wystawienia', 'data sprzedaży', 'nabywca', 'sprzedawca',
            'netto', 'brutto', 'vat', 'stawka vat', 'kwota do zapłaty',
            'termin płatności', 'forma płatności', 'nip'
        ],
        'patterns': [
            r'faktura\s*(vat|nr|numer)?',
            r'nip[:\s]*\d{10}',
            r'nip[:\s]*\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}',
            r'kwota\s*(netto|brutto)',
            r'\d+[,\.]\d{2}\s*zł',
            r'stawka\s*vat\s*\d+%'
        ],
        'weight': 0
    },
    'receipt': {
        'keywords': [
            'paragon', 'paragon fiskalny', 'nr paragonu', 'kasa fiskalna',
            'kasjer', 'ptu', 'suma', 'razem', 'gotówka', 'karta',
            'fiskalny', 'nr kasy'
        ],
        'patterns': [
            r'paragon\s*(fiskalny)?',
            r'nr\s*kasy',
            r'ptu\s*[a-d]',
            r'suma\s*pln',
            r'razem\s*\d+[,\.]\d{2}'
        ],
        'weight': 0
    },
    'contract': {
        'keywords': [
            'umowa', 'umowa o pracę', 'umowa zlecenie', 'umowa o dzieło',
            'strony umowy', 'przedmiot umowy', 'wynagrodzenie', 'okres obowiązywania',
            'warunki', 'postanowienia', 'zleceniodawca', 'zleceniobiorca',
            'pracodawca', 'pracownik', 'aneks', 'wypowiedzenie'
        ],
        'patterns': [
            r'umowa\s*(o\s*pracę|zlecenie|o\s*dzieło)?',
            r'strony\s*umowy',
            r'przedmiot\s*umowy',
            r'§\s*\d+',
            r'art\.\s*\d+'
        ],
        'weight': 0
    },
    'protocol': {
        'keywords': [
            'protokół', 'protokol', 'badania', 'przegląd', 'przeglądu',
            'kontroli', 'odbioru', 'zdawczo-odbiorczy', 'serwisowy',
            'technicznego', 'stanu'
        ],
        'patterns': [
            r'protokół\s*(badania|przeglądu|kontroli|odbioru)?',
            r'protokol\s*(badania)?',
            r'data\s*badania',
            r'wynik\s*(pozytywny|negatywny)'
        ],
        'weight': 0
    },
    'report': {
        'keywords': [
            'raport', 'sprawozdanie', 'zestawienie', 'podsumowanie',
            'analiza', 'wyniki', 'wnioski', 'rekomendacje'
        ],
        'patterns': [
            r'raport\s*(miesięczny|kwartalny|roczny)?',
            r'sprawozdanie',
            r'zestawienie'
        ],
        'weight': 0
    }
}

# Data extraction patterns for each document type
EXTRACTION_PATTERNS = {
    'invoice': {
        'invoice_number': [
            r'(?:faktura|invoice)\s*(?:vat)?\s*(?:nr|numer|no\.?)?[:\s]*([A-Z0-9/\-]+)',
            r'nr\s*faktury[:\s]*([A-Z0-9/\-]+)',
            r'numer\s*faktury[:\s]*([A-Z0-9/\-]+)'
        ],
        'nip_seller': [
            r'(?:sprzedawca|seller).*?nip[:\s]*(\d{10}|\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})',
            r'nip[:\s]*(\d{10}|\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})'
        ],
        'nip_buyer': [
            r'(?:nabywca|buyer).*?nip[:\s]*(\d{10}|\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})'
        ],
        'total_gross': [
            r'(?:razem|suma|total|do\s*zapłaty).*?(\d+[\s,\.]\d{2})\s*(?:zł|pln)?',
            r'brutto[:\s]*(\d+[\s,\.]\d{2})',
            r'(\d+[\s,\.]\d{2})\s*(?:zł|pln)\s*(?:brutto)?'
        ],
        'total_net': [
            r'netto[:\s]*(\d+[\s,\.]\d{2})'
        ],
        'vat_amount': [
            r'(?:vat|podatek)[:\s]*(\d+[\s,\.]\d{2})'
        ],
        'issue_date': [
            r'(?:data\s*wystawienia|issue\s*date)[:\s]*(\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4})',
            r'(\d{1,2}[\./-]\d{1,2}[\./-]\d{4})'
        ],
        'due_date': [
            r'(?:termin\s*płatności|due\s*date|płatne\s*do)[:\s]*(\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4})'
        ]
    },
    'receipt': {
        'receipt_number': [
            r'(?:paragon|nr)[:\s]*([A-Z0-9/\-]+)'
        ],
        'total': [
            r'(?:suma|razem|total)[:\s]*(\d+[,\.]\d{2})'
        ],
        'date': [
            r'(\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4})'
        ]
    },
    'contract': {
        'contract_date': [
            r'(?:zawarta\s*(?:w\s*dniu|dnia)|data)[:\s]*(\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4})'
        ],
        'parties': [
            r'(?:pomiędzy|między)[:\s]*(.+?)(?:a\s+|oraz)'
        ]
    },
    'protocol': {
        'protocol_number': [
            r'(?:protokół|nr)[:\s]*([A-Z0-9/\-]+)'
        ],
        'inspection_date': [
            r'(?:data\s*badania|data\s*przeglądu)[:\s]*(\d{1,2}[\./-]\d{1,2}[\./-]\d{2,4})'
        ],
        'result': [
            r'(?:wynik|rezultat)[:\s]*(pozytywny|negatywny|passed|failed)'
        ]
    }
}


def detect_document_type(ocr_text: str) -> Tuple[str, float]:
    """
    Detect document type from OCR text.
    Returns (document_type, confidence)
    """
    if not ocr_text:
        return 'other', 0.0
    
    text_lower = ocr_text.lower()
    scores = {}
    
    for doc_type, config in DOCUMENT_PATTERNS.items():
        score = 0
        
        # Check keywords
        for keyword in config['keywords']:
            if keyword in text_lower:
                score += 1
        
        # Check regex patterns
        for pattern in config['patterns']:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 2
        
        scores[doc_type] = score
    
    if not scores or max(scores.values()) == 0:
        return 'other', 0.0
    
    # Get best match
    best_type = max(scores, key=scores.get)
    max_score = scores[best_type]
    
    # Calculate confidence (normalized)
    total_possible = len(DOCUMENT_PATTERNS[best_type]['keywords']) + \
                     len(DOCUMENT_PATTERNS[best_type]['patterns']) * 2
    confidence = min(max_score / max(total_possible * 0.3, 1), 1.0)
    
    return best_type, round(confidence, 2)


def extract_document_data(ocr_text: str, document_type: str) -> Dict[str, Any]:
    """
    Extract structured data from OCR text based on document type.
    """
    if not ocr_text or document_type not in EXTRACTION_PATTERNS:
        return {}
    
    patterns = EXTRACTION_PATTERNS[document_type]
    extracted = {}
    
    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                # Clean up value
                value = re.sub(r'\s+', ' ', value)
                extracted[field] = value
                break
    
    return extracted


def classify_and_extract(ocr_text: str, initial_type: str = 'auto') -> Dict[str, Any]:
    """
    Main function to classify document and extract data.
    Returns dict with document_type, confidence, and extracted_data
    """
    # Detect type if auto
    if initial_type == 'auto' or not initial_type:
        detected_type, confidence = detect_document_type(ocr_text)
    else:
        detected_type = initial_type
        confidence = 1.0
    
    # Extract data based on type
    extracted_data = extract_document_data(ocr_text, detected_type)
    
    return {
        'document_type': detected_type,
        'detection_confidence': confidence,
        'extracted_fields': extracted_data
    }
