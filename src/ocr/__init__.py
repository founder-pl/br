"""
OCR Service Module
"""
from .extractors import InvoiceExtractor, validate_nip, validate_regon, get_extractor
from .models import ProcessingStatus, DocumentType, ExtractedInvoiceData


def get_ocr_engine(*args, **kwargs):
    from .engines import get_ocr_engine as _get_ocr_engine
    return _get_ocr_engine(*args, **kwargs)


def preprocess_image(*args, **kwargs):
    from .preprocessing import preprocess_image as _preprocess_image
    return _preprocess_image(*args, **kwargs)


def preprocess_pdf(*args, **kwargs):
    from .preprocessing import preprocess_pdf as _preprocess_pdf
    return _preprocess_pdf(*args, **kwargs)

__all__ = [
    'get_ocr_engine',
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
