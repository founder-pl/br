"""
OCR Service Module
"""
from .engines import get_ocr_engine, TesseractEngine, PaddleOCREngine, EasyOCREngine, OCRResult
from .extractors import InvoiceExtractor, validate_nip, validate_regon, get_extractor
from .preprocessing import preprocess_image, preprocess_pdf
from .models import ProcessingStatus, DocumentType, ExtractedInvoiceData

__all__ = [
    'get_ocr_engine',
    'TesseractEngine',
    'PaddleOCREngine',
    'EasyOCREngine',
    'OCRResult',
    'InvoiceExtractor',
    'validate_nip',
    'validate_regon',
    'get_extractor',
    'preprocess_image',
    'preprocess_pdf',
    'ProcessingStatus',
    'DocumentType',
    'ExtractedInvoiceData',
]
