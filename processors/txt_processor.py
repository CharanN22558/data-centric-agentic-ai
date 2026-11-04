"""
Plain Text (TXT) Document Processor.

Provides:
- Reading raw text
- Appending text
- Exact text replacement
- Text deletion
"""

from typing import Tuple


def read_txt(content_bytes: bytes) -> str:
    """Decodes plain text bytes handling UTF-8 and Latin-1."""
    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return content_bytes.decode("latin-1")


def append_to_txt(content_bytes: bytes, text_to_append: str) -> bytes:
    """Appends text to the end of a plain text file."""
    text = read_txt(content_bytes)
    if text and not text.endswith("\n"):
        text += "\n"
    text += text_to_append
    return text.encode("utf-8")


def replace_in_txt(content_bytes: bytes, target_text: str, replacement_text: str) -> Tuple[bytes, int]:
    """
    Replaces exact target text with replacement text.
    Returns: (modified_bytes, occurrences_replaced)
    """
    text = read_txt(content_bytes)
    count = text.count(target_text)
    if count == 0:
        return content_bytes, 0
    modified_text = text.replace(target_text, replacement_text)
    return modified_text.encode("utf-8"), count


def delete_from_txt(content_bytes: bytes, text_to_delete: str) -> Tuple[bytes, int]:
    """
    Deletes occurrences of text_to_delete from a plain text file.
    Returns: (modified_bytes, occurrences_deleted)
    """
    return replace_in_txt(content_bytes, text_to_delete, "")

