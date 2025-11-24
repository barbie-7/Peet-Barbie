#!/usr/bin/env python3
"""
Hybrid Study Notes Summarizer:
- Extracts text from PDFs/images
- Optional OCR
- Chunked summarization
- Uses high-quality GPT-4.1 (NoteGPT style)
- Saves Markdown + DOCX
"""

import os, sys, argparse, logging, time, io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2, glob
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

# Optional: pdf2image for scanned PDFs
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
    PROJECT_POPPLER_BIN = Path(__file__).parent / "poppler" / "bin"
    PDF2IMAGE_POPPLER_PATH = str(PROJECT_POPPLER_BIN) if PROJECT_POPPLER_BIN.exists() else None
except Exception:
    PDF2IMAGE_AVAILABLE = False
    PDF2IMAGE_POPPLER_PATH = None

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# Config
# ----------------------------
CHUNK_MAX_CHARS = 4500
STYLE_CHOICES = ["notion", "pastel", "cornell", "plain"]
MAX_WORKERS = 4

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ----------------------------
# Utilities
# ----------------------------
def chunk_text(text: str, max_chars=CHUNK_MAX_CHARS):
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            nl = text.rfind("\n", start, end)
            if nl > start + 50:
                end = nl
        chunks.append(text[start:end].strip())
        start = end
    return chunks

def safe_write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ----------------------------
# Extraction
# ----------------------------
def extract_text_from_pdf(pdf_path: Path) -> str:
    text_parts = []
    try:
        with open(pdf_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""
    return "\n\n".join(text_parts)

def convert_pdf_page_to_image_bytes(pdf_path: Path, page_number: int, dpi=150):
    if not PDF2IMAGE_AVAILABLE:
        return None
    try:
        images = convert_from_path(
            str(pdf_path), dpi=dpi,
            first_page=page_number, last_page=page_number,
            poppler_path=PDF2IMAGE_POPPLER_PATH
        )
        bio = io.BytesIO()
        images[0].save(bio, format="PNG")
        return bio.getvalue()
    except Exception as e:
        logger.warning(f"pdf2image failed for page {page_number}: {e}")
        return None

# ----------------------------
# OpenAI/NoteGPT integration
# ----------------------------
def summarize_with_notegpt(text: str) -> str:
    """High-quality NoteGPT style summarization"""
    prompt = f"""
    You are an elite university study-note creator.

    Transform RAW NOTES into EXAM-READY STUDY NOTES.
    Produce:
    - H1/H2/H3 hierarchy
    - Bullet points + short explanations
    - Key formulas explained
    - Short illustrative examples
    - Warnings/pitfalls highlighted
    - Definitions clearly marked
    - Summary boxes at end of sections
    - Exam tips or memory tricks
    No fluff.

    RAW NOTES:
    {text}
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"NoteGPT summarization failed: {e}")
        time.sleep(2)
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return resp.choices[0].message.content

def chunk_summarize(text: str) -> str:
    chunks = chunk_text(text)
    summaries = [summarize_with_notegpt(c) for c in chunks]
    combined = "\n\n".join(summaries)
    # Final polish
    final_prompt = f"Combine the following summaries into a cohesive study guide:\n\n{combined}"
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.3
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"Final polish failed: {e}")
        return combined

# ----------------------------
# Save to Markdown/DOCX
# ----------------------------
def save_summary_docx(summary: str, out_path: Path, style: str = "notion"):
    doc = Document()
    title = doc.add_paragraph("📚 Study Notes")
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = title.runs[0]
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 55, 115)
    doc.add_paragraph()
    for line in summary.split("\n"):
        line = line.rstrip()
        if not line:
            doc.add_paragraph()
            continue
        if line.startswith("###"):
            h = doc.add_paragraph(line.replace("###","").strip())
            h.style = "Heading 2"
        elif line.startswith("- "):
            doc.add_paragraph(line.replace("- ","").strip(), style="List Bullet")
        else:
            p = doc.add_paragraph(line)
            if p.runs:
                p.runs[0].font.size = Pt(11)
            p.paragraph_format.line_spacing = 1.2
    doc.save(out_path)
    logger.info(f"DOCX saved: {out_path}")

def save_summary_markdown(summary: str, out_path: Path):
    safe_write_text(out_path, summary)
    logger.info(f"Markdown saved: {out_path}")

# ----------------------------
# File/Folders
# ----------------------------
def summarize_pdf_file(path: Path, style: str="notion") -> str:
    out_cache = path.parent / f"{path.stem}_summary.txt"
    if out_cache.exists():
        return out_cache.read_text()
    raw_text = extract_text_from_pdf(path)
    master_summary = chunk_summarize(raw_text)
    save_summary_markdown(master_summary, path.parent / f"{path.stem}_summary.md")
    save_summary_docx(master_summary, path.parent / f"{path.stem}_summary.docx", style)
    safe_write_text(out_cache, master_summary)
    return master_summary

def summarize_folder(folder: Path, combine=False, style="notion"):
    files = sorted([Path(f) for f in glob.glob(str(folder / "**/*"), recursive=True)
                    if Path(f).suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]])
    if not files:
        logger.warning("No PDF/image files found.")
        return
    if combine:
        combined_raw = ""
        for f in files:
            if f.suffix.lower() == ".pdf":
                combined_raw += extract_text_from_pdf(f) + "\n\n"
        master_summary = chunk_summarize(combined_raw)
        save_summary_markdown(master_summary, folder / "combined_summary.md")
        save_summary_docx(master_summary, folder / "combined_summary.docx", style)
        safe_write_text(folder / "combined_summary.txt", master_summary)
        logger.info("Combined folder summary complete.")
        return
    # Parallel processing
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(summarize_pdf_file, f, style) for f in files if f.suffix.lower()==".pdf"]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.warning(f"Error during parallel summarization: {e}")

# ----------------------------
# CLI
# ----------------------------
def build_arg_parser():
    p = argparse.ArgumentParser(description="Hybrid Study Notes Summarizer")
    p.add_argument("path", help="PDF file or folder")
    p.add_argument("--folder", action="store_true")
    p.add_argument("--combine", action="store_true")
    p.add_argument("--style", choices=STYLE_CHOICES, default="notion")
    return p

def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    path = Path(args.path)
    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        sys.exit(1)
    if args.folder:
        summarize_folder(path, combine=args.combine, style=args.style)
    else:
        if path.suffix.lower() == ".pdf":
            summarize_pdf_file(path, style=args.style)
        else:
            logger.error("Unsupported file type.")
            sys.exit(1)

if __name__ == "__main__":
    if not PDF2IMAGE_AVAILABLE:
        logger.warning("pdf2image not installed. Scanned PDFs will not be processed.")
    elif PDF2IMAGE_AVAILABLE and not PDF2IMAGE_POPPLER_PATH:
        logger.warning("Poppler not found. Scanned PDFs may fail. Place 'poppler/bin' in project folder.")
    main()
