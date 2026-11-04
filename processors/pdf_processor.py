"""
PDF Document Processor.

Provides:
- Text extraction with page tracking
- Scanned PDF detection (notifies user when OCR is required)
- PDF merging
- PDF splitting / page extraction
- Page reordering
- Safe text annotations
"""

import io
from typing import List, Dict, Any, Tuple
import pypdf
import pymupdf as fitz  # Modern import, eliminates deprecation warnings


def extract_pdf_pages_and_text(content_bytes: bytes) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Extracts text page-by-page.
    Detects if the PDF is scanned (total extracted text < 50 characters across pages).

    Returns:
    (pages_data, is_scanned)
    """
    doc = fitz.open(stream=content_bytes, filetype="pdf")
    pages_data = []
    total_text_length = 0

    for idx, page in enumerate(doc, start=1):
        text = page.get_text() or ""
        cleaned = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        total_text_length += len(cleaned)
        pages_data.append({
            "page_number": idx,
            "text": cleaned,
            "char_count": len(cleaned)
        })

    doc.close()
    is_scanned = (total_text_length < 50 and len(pages_data) > 0)
    return pages_data, is_scanned


def merge_pdfs(pdf_bytes_list: List[bytes]) -> bytes:
    """Merges multiple PDF byte streams into a single PDF document."""
    merger = pypdf.PdfMerger()
    for data in pdf_bytes_list:
        merger.append(io.BytesIO(data))
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    return output.getvalue()


def extract_pdf_pages(content_bytes: bytes, page_numbers: List[int]) -> bytes:
    """
    Extracts specified 1-based page numbers from a PDF document.
    """
    reader = pypdf.PdfReader(io.BytesIO(content_bytes))
    writer = pypdf.PdfWriter()

    total_pages = len(reader.pages)
    for p in page_numbers:
        if 1 <= p <= total_pages:
            writer.add_page(reader.pages[p - 1])
        else:
            raise ValueError(f"Page {p} out of bounds (document has {total_pages} pages).")

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def reorder_pdf_pages(content_bytes: bytes, new_order: List[int]) -> bytes:
    """
    Reorders pages in a PDF document based on a list of 1-based page indices.
    """
    return extract_pdf_pages(content_bytes, new_order)


def add_pdf_text_annotation(
    content_bytes: bytes,
    page_number: int,
    text: str,
    x: float = 50.0,
    y: float = 50.0
) -> bytes:
    """
    Safely adds a visible text stamp/annotation to a specific page using PyMuPDF.
    """
    doc = fitz.open(stream=content_bytes, filetype="pdf")
    if page_number < 1 or page_number > len(doc):
        doc.close()
        raise ValueError(f"Page number {page_number} is out of bounds.")

    page = doc.load_page(page_number - 1)
    rect = fitz.Rect(x, y, x + 300, y + 40)
    page.insert_textbox(rect, text, fontsize=11, color=(0.1, 0.1, 0.7))

    output = doc.tobytes()
    doc.close()
    return output
