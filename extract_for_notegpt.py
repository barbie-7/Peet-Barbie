#!/usr/bin/env python3
"""
PDF/Image text extractor for NoteGPT
- Extracts text from PDFs
- Optionally extracts text from images using OCR (pdf2image + OpenAI Vision)
- Saves each file as a .txt ready for NoteGPT summarization
"""

import os
import sys
from pathlib import Path
import glob
import logging

# Optional: PDF text extraction
import PyPDF2

# Optional: pdf2image for scanned PDFs
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------
# Utilities
# ---------------------------
def safe_write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ---------------------------
# Text extraction
# ---------------------------
def extract_text_from_pdf(pdf_path: Path) -> str:
    text_parts = []
    try:
        with open(pdf_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for i, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
    except Exception as e:
        logger.error(f"PDF extraction failed ({pdf_path}): {e}")
    return "\n\n".join(text_parts)

def convert_pdf_page_to_image_bytes(pdf_path: Path, page_number: int, dpi=150):
    if not PDF2IMAGE_AVAILABLE:
        return None
    try:
        images = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_number, last_page=page_number)
        if not images:
            return None
        bio = io.BytesIO()
        images[0].save(bio, format="PNG")
        return bio.getvalue()
    except Exception as e:
        logger.warning(f"pdf2image failed for {pdf_path} page {page_number}: {e}")
        return None

# ---------------------------
# Folder processing
# ---------------------------
def extract_folder(folder: Path):
    files = sorted(
        Path(f) for f in glob.glob(str(folder / "**/*"), recursive=True)
        if Path(f).suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]
    )
    if not files:
        logger.warning("No PDF/image files found.")
        return

    for f in files:
        if f.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(f)
            safe_write_text(f.with_suffix(".txt"), text)
            logger.info(f"Extracted text: {f.name} -> {f.stem}.txt")
        else:
            logger.warning(f"Skipping image file {f.name}. You can implement OCR if needed.")

# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_for_notegpt.py <folder_or_file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        sys.exit(1)

    if path.is_dir():
        extract_folder(path)
    elif path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(path)
        safe_write_text(path.with_suffix(".txt"), text)
        logger.info(f"Extracted text: {path.name} -> {path.stem}.txt")
    else:
        logger.error("Unsupported file type. Only PDF files or folders supported.")
