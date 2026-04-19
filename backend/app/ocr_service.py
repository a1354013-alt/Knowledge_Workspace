"""OCR service for extracting text from images."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("enterprise_ai")

try:
    import pytesseract
    from PIL import Image

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract or PIL not installed. OCR functionality will be disabled.")


def extract_text_from_image(image_path: str | Path) -> str:
    """
    Extract text from an image file using OCR.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Extracted text content, or empty string if OCR fails
    """
    if not PYTESSERACT_AVAILABLE:
        logger.info("OCR is not available. Install pytesseract and PIL for OCR support.")
        return ""
    
    try:
        image_path = Path(image_path)
        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return ""
        
        # Open image with PIL
        img = Image.open(image_path)
        
        # Configure tesseract for better accuracy
        custom_config = r"--oem 3 --psm 6"
        
        # Extract text
        text = pytesseract.image_to_string(img, config=custom_config)
        
        # Clean up the extracted text
        cleaned_text = " ".join(text.split())
        
        logger.info(f"Extracted {len(cleaned_text)} characters from {image_path.name}")
        return cleaned_text
        
    except Exception as exc:
        logger.error(f"OCR failed for {image_path}: {exc}")
        return ""


def batch_extract_text(image_paths: list[str | Path]) -> dict[str, str]:
    """
    Extract text from multiple images.
    
    Args:
        image_paths: List of image file paths
        
    Returns:
        Dictionary mapping file paths to extracted text
    """
    results: dict[str, str] = {}
    for path in image_paths:
        path_str = str(path)
        results[path_str] = extract_text_from_image(path)
    return results
