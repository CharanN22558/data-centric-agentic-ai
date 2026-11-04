"""
Context-Preserving Document Chunking Module.

Splits loaded document items into coherent, semantically rich chunks
while preserving page numbers, sheet names, rows, and line references.
"""

from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag.document_loader import LoadedDocumentItem


class DocumentChunk:
    """A single searchable chunk tagged with full source provenance."""
    def __init__(self, text: str, location_label: str, metadata: Dict[str, Any]):
        self.text = text
        self.location_label = location_label
        self.metadata = metadata


def chunk_document_items(items: List[LoadedDocumentItem], chunk_size: int = 500, chunk_overlap: int = 50) -> List[DocumentChunk]:
    """
    Applies RecursiveCharacterTextSplitter to text passages while retaining location metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks: List[DocumentChunk] = []

    for item in items:
        # If the item text is already small (e.g. single excel row), keep it intact
        if len(item.text) <= chunk_size:
            chunks.append(DocumentChunk(
                text=item.text,
                location_label=item.location_label,
                metadata=item.metadata
            ))
        else:
            sub_texts = splitter.split_text(item.text)
            for idx, st in enumerate(sub_texts):
                chunks.append(DocumentChunk(
                    text=st,
                    location_label=f"{item.location_label} (part {idx+1})",
                    metadata={**item.metadata, "chunk_part": idx + 1}
                ))

    return chunks

