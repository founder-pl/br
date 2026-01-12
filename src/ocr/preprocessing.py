"""
Image Preprocessing for OCR
Includes deskewing, denoising, binarization for optimal OCR results
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple
import asyncio

import numpy as np
from PIL import Image
import cv2
import structlog

logger = structlog.get_logger()


async def preprocess_image(
    image_path: Path,
    dpi: int = 300,
    denoise: bool = True,
    deskew: bool = True,
    binarize: bool = False
) -> np.ndarray:
    """
    Preprocess an image for optimal OCR results.
    
    Args:
        image_path: Path to the image file
        dpi: Target DPI for scaling
        denoise: Apply denoising
        deskew: Correct image rotation
        binarize: Convert to binary (black/white)
    
    Returns:
        Preprocessed image as numpy array
    """
    # Load image
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Scale to target DPI if needed
    # Assuming source is 72 DPI (typical screen resolution)
    source_dpi = 72
    if dpi != source_dpi:
        scale_factor = dpi / source_dpi
        new_width = int(gray.shape[1] * scale_factor)
        new_height = int(gray.shape[0] * scale_factor)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # Deskew
    if deskew:
        gray = await _deskew_image(gray)
    
    # Denoise
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # Binarize (optional - sometimes better without for colored documents)
    if binarize:
        gray = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 2
        )
    
    logger.debug("Image preprocessed", 
                 shape=gray.shape, 
                 dpi=dpi, 
                 deskew=deskew, 
                 denoise=denoise)
    
    return gray


async def preprocess_pdf(
    pdf_path: Path,
    dpi: int = 300,
    denoise: bool = True,
    deskew: bool = True
) -> List[np.ndarray]:
    """
    Convert PDF pages to preprocessed images.
    
    Args:
        pdf_path: Path to PDF file
        dpi: DPI for rendering
        denoise: Apply denoising
        deskew: Correct rotation
    
    Returns:
        List of preprocessed images (one per page)
    """
    import fitz  # PyMuPDF
    
    images = []
    
    # Open PDF
    doc = fitz.open(str(pdf_path))
    logger.info("Processing PDF", path=str(pdf_path), pages=len(doc))
    
    for page_num, page in enumerate(doc):
        # Check if page has text (native PDF)
        text = page.get_text()
        
        if text.strip():
            # Native PDF with text - still render for OCR to verify
            logger.debug("Page has native text", page=page_num)
        
        # Render page to image
        zoom = dpi / 72  # 72 is default PDF DPI
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        
        # Convert to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        
        # Convert to grayscale
        if pix.n == 4:  # RGBA
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        elif pix.n == 3:  # RGB
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img
        
        # Apply preprocessing
        if deskew:
            gray = await _deskew_image(gray)
        
        if denoise:
            gray = cv2.fastNlMeansDenoising(gray, None, h=10)
        
        images.append(gray)
        logger.debug("Page processed", page=page_num, shape=gray.shape)
    
    doc.close()
    return images


async def _deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Detect and correct image skew (rotation).
    
    Uses Hough transform to detect dominant line angles.
    """
    # Threshold
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Hough transform to find lines
    lines = cv2.HoughLinesP(
        edges, 
        rho=1, 
        theta=np.pi/180, 
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )
    
    if lines is None or len(lines) == 0:
        return image
    
    # Calculate angles
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 != 0:
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            # Only consider near-horizontal lines
            if abs(angle) < 45:
                angles.append(angle)
    
    if not angles:
        return image
    
    # Median angle
    median_angle = np.median(angles)
    
    # Skip if angle is very small
    if abs(median_angle) < 0.5:
        return image
    
    # Rotate image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        image, 
        rotation_matrix, 
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    
    logger.debug("Image deskewed", angle=median_angle)
    return rotated


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Enhance image contrast using CLAHE"""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(image)


def remove_shadows(image: np.ndarray) -> np.ndarray:
    """Remove shadows from document image"""
    # Dilate to get background
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    bg = cv2.dilate(image, kernel)
    
    # Gaussian blur for smooth background
    bg = cv2.GaussianBlur(bg, (11, 11), 0)
    
    # Divide original by background
    result = cv2.divide(image, bg, scale=255)
    
    return result


def detect_document_type(image: np.ndarray) -> str:
    """
    Attempt to detect document type based on visual features.
    
    Returns:
        Document type: 'invoice', 'receipt', 'contract', 'unknown'
    """
    # This is a simple heuristic - could be enhanced with ML
    h, w = image.shape[:2]
    aspect_ratio = w / h
    
    # Receipts are typically tall and narrow
    if aspect_ratio < 0.5:
        return 'receipt'
    
    # Standard A4 documents
    if 0.65 < aspect_ratio < 0.75:
        return 'document'
    
    return 'unknown'
