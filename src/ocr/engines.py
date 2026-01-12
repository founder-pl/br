"""
OCR Engines - Tesseract, PaddleOCR, EasyOCR
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import asyncio
from pathlib import Path

import numpy as np
from PIL import Image
import structlog

logger = structlog.get_logger()


@dataclass
class OCRResult:
    """Result from OCR processing"""
    text: str
    confidence: float
    boxes: Optional[List[Dict[str, Any]]] = None
    raw_data: Optional[Any] = None


class BaseOCREngine(ABC):
    """Base class for OCR engines"""
    
    def __init__(self, language: str = "pol", use_gpu: bool = True):
        self.language = language
        self.use_gpu = use_gpu
        self._initialized = False
    
    @abstractmethod
    async def initialize(self):
        """Initialize the OCR engine"""
        pass
    
    @abstractmethod
    async def process(self, image: np.ndarray) -> OCRResult:
        """Process an image and return OCR result"""
        pass
    
    def _ensure_initialized(self):
        """Ensure engine is initialized"""
        if not self._initialized:
            asyncio.get_event_loop().run_until_complete(self.initialize())


class TesseractEngine(BaseOCREngine):
    """Tesseract OCR Engine"""
    
    LANG_MAP = {
        "pol": "pol",
        "eng": "eng",
        "deu": "deu",
        "pl": "pol",
        "en": "eng",
        "de": "deu"
    }
    
    async def initialize(self):
        """Initialize Tesseract"""
        import pytesseract
        
        # Verify Tesseract is available
        try:
            version = pytesseract.get_tesseract_version()
            logger.info("Tesseract initialized", version=str(version))
            self._initialized = True
        except Exception as e:
            logger.error("Failed to initialize Tesseract", error=str(e))
            raise
    
    async def process(self, image: np.ndarray) -> OCRResult:
        """Process image with Tesseract"""
        import pytesseract
        
        self._ensure_initialized()
        
        lang = self.LANG_MAP.get(self.language, self.language)
        
        # Configure Tesseract
        config = f'--psm 6 --oem 1 -l {lang}'
        
        # Get text and confidence
        data = pytesseract.image_to_data(
            image, 
            lang=lang,
            config=config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract text
        text_parts = []
        confidences = []
        boxes = []
        
        for i, word in enumerate(data['text']):
            if word.strip():
                text_parts.append(word)
                conf = data['conf'][i]
                if conf > 0:
                    confidences.append(conf / 100.0)
                    boxes.append({
                        'text': word,
                        'confidence': conf / 100.0,
                        'box': [
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ]
                    })
        
        text = ' '.join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=text,
            confidence=avg_confidence,
            boxes=boxes,
            raw_data=data
        )


class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR Engine with GPU support"""
    
    LANG_MAP = {
        "pol": "latin",
        "eng": "en",
        "deu": "latin",
        "pl": "latin",
        "en": "en",
        "de": "latin",
        "latin": "latin"
    }
    
    def __init__(self, language: str = "pol", use_gpu: bool = True):
        super().__init__(language, use_gpu)
        self.ocr = None
    
    async def initialize(self):
        """Initialize PaddleOCR"""
        from paddleocr import PaddleOCR
        
        lang = self.LANG_MAP.get(self.language, "latin")
        
        try:
            self.ocr = PaddleOCR(
                lang=lang,
                use_gpu=self.use_gpu,
                use_angle_cls=True,
                show_log=False,
                enable_mkldnn=True,
                use_mp=True,
                total_process_num=2
            )
            logger.info("PaddleOCR initialized", language=lang, gpu=self.use_gpu)
            self._initialized = True
        except Exception as e:
            logger.error("Failed to initialize PaddleOCR", error=str(e))
            raise
    
    async def process(self, image: np.ndarray) -> OCRResult:
        """Process image with PaddleOCR"""
        self._ensure_initialized()
        
        # Run OCR in thread pool to not block async loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.ocr.ocr, image, True)
        
        if not result or not result[0]:
            return OCRResult(text="", confidence=0.0, boxes=[])
        
        text_parts = []
        confidences = []
        boxes = []
        
        for line in result[0]:
            if line and len(line) >= 2:
                box_coords, (text, conf) = line[0], line[1]
                text_parts.append(text)
                confidences.append(conf)
                boxes.append({
                    'text': text,
                    'confidence': conf,
                    'box': box_coords
                })
        
        text = ' '.join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=text,
            confidence=avg_confidence,
            boxes=boxes,
            raw_data=result
        )


class EasyOCREngine(BaseOCREngine):
    """EasyOCR Engine"""
    
    LANG_MAP = {
        "pol": ["pl", "en"],
        "eng": ["en"],
        "deu": ["de", "en"],
        "pl": ["pl", "en"],
        "en": ["en"],
        "de": ["de", "en"]
    }
    
    def __init__(self, language: str = "pol", use_gpu: bool = True):
        super().__init__(language, use_gpu)
        self.reader = None
    
    async def initialize(self):
        """Initialize EasyOCR"""
        import easyocr
        
        langs = self.LANG_MAP.get(self.language, ["en"])
        
        try:
            self.reader = easyocr.Reader(
                langs,
                gpu=self.use_gpu,
                verbose=False
            )
            logger.info("EasyOCR initialized", languages=langs, gpu=self.use_gpu)
            self._initialized = True
        except Exception as e:
            logger.error("Failed to initialize EasyOCR", error=str(e))
            raise
    
    async def process(self, image: np.ndarray) -> OCRResult:
        """Process image with EasyOCR"""
        self._ensure_initialized()
        
        # Run OCR in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.reader.readtext(image, detail=1)
        )
        
        if not result:
            return OCRResult(text="", confidence=0.0, boxes=[])
        
        text_parts = []
        confidences = []
        boxes = []
        
        for detection in result:
            box_coords, text, conf = detection
            text_parts.append(text)
            confidences.append(conf)
            boxes.append({
                'text': text,
                'confidence': conf,
                'box': box_coords
            })
        
        text = ' '.join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=text,
            confidence=avg_confidence,
            boxes=boxes,
            raw_data=result
        )


async def get_ocr_engine(
    engine_name: str = "paddleocr",
    language: str = "pol",
    use_gpu: bool = True
) -> BaseOCREngine:
    """Factory function to get OCR engine instance (async)"""
    
    engines = {
        "tesseract": TesseractEngine,
        "paddleocr": PaddleOCREngine,
        "easyocr": EasyOCREngine
    }
    
    engine_class = engines.get(engine_name.lower())
    if not engine_class:
        raise ValueError(f"Unknown OCR engine: {engine_name}. Available: {list(engines.keys())}")
    
    engine = engine_class(language=language, use_gpu=use_gpu)
    
    # Initialize asynchronously
    await engine.initialize()
    
    return engine
