"""
Format-Aware Document Loader Module.

Extracts structured sections from decrypted bytes for TXT, XLSX, and PDF files.
"""

from typing import List, Dict, Any, Tuple
from processors.txt_processor import read_txt
from processors.excel_processor import inspect_excel
from processors.pdf_processor import extract_pdf_pages_and_text


class LoadedDocumentItem:
    """Represents an extracted piece of document content with precise metadata."""
    def __init__(self, text: str, location_label: str, metadata: Dict[str, Any]):
        self.text = text
        self.location_label = location_label
        self.metadata = metadata


def load_document_content(filename: str, content_bytes: bytes) -> Tuple[List[LoadedDocumentItem], Dict[str, Any]]:
    """
    Parses file content bytes according to file extension.
    Returns: (list_of_loaded_items, summary_metadata)
    """
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    items: List[LoadedDocumentItem] = []
    summary: Dict[str, Any] = {"filename": filename, "format": ext}

    if ext == ".txt":
        raw_text = read_txt(content_bytes)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        # Group into 10-line passages
        for i in range(0, len(lines), 10):
            passage = "\n".join(lines[i:i + 10])
            items.append(LoadedDocumentItem(
                text=passage,
                location_label=f"Lines {i+1}-{min(i+10, len(lines))}",
                metadata={"filename": filename, "line_start": i+1, "line_end": min(i+10, len(lines))}
            ))
        summary["total_lines"] = len(lines)

    elif ext == ".xlsx":
        excel_info = inspect_excel(content_bytes)
        summary["sheet_names"] = excel_info["sheet_names"]
        for sheet_name, sheet_data in excel_info["sheets"].items():
            headers = sheet_data["headers"]
            sample_rows = sheet_data["sample_rows"]
            # Sheet header overview chunk
            overview = f"Worksheet: {sheet_name} | Columns: {', '.join(headers)}"
            items.append(LoadedDocumentItem(
                text=overview,
                location_label=f"Sheet '{sheet_name}' Header",
                metadata={"filename": filename, "sheet": sheet_name, "is_header": True}
            ))
            # Row level chunks
            for r_idx, row in enumerate(sample_rows, start=2):
                row_str = " | ".join([f"{k}: {v}" for k, v in row.items() if v is not None])
                if row_str:
                    items.append(LoadedDocumentItem(
                        text=f"Sheet: {sheet_name} | Row {r_idx} -> {row_str}",
                        location_label=f"Sheet '{sheet_name}', Row {r_idx}",
                        metadata={"filename": filename, "sheet": sheet_name, "row": r_idx}
                    ))

    elif ext == ".pdf":
        pages, is_scanned = extract_pdf_pages_and_text(content_bytes)
        summary["total_pages"] = len(pages)
        summary["is_scanned"] = is_scanned
        for p in pages:
            if p["text"]:
                items.append(LoadedDocumentItem(
                    text=p["text"],
                    location_label=f"Page {p['page_number']}",
                    metadata={"filename": filename, "page_number": p["page_number"]}
                ))

    return items, summary


def load_and_chunk_document(filename: str, content_bytes: bytes, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Convenience pipeline wrapper:
    Loads document content into items, then splits them into searchable chunks
    while preserving page, sheet, row, and line provenance.
    """
    from rag.chunking import chunk_document_items
    items, _ = load_document_content(filename, content_bytes)
    return chunk_document_items(items, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


