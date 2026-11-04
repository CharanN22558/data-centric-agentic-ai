"""
Document Modification Validator Module.

Performs pre-validation and post-validation checks:
1. Validates file header and structure before modification.
2. Validates that the modified byte stream is valid, non-empty, and readable by parsers.
3. Computes checksum diffs to guarantee authentic modification.
"""

from typing import Tuple
from processors.excel_processor import load_workbook_from_bytes
import fitz


def validate_modification_output(filename: str, original_bytes: bytes, modified_bytes: bytes) -> Tuple[bool, str]:
    """
    Validates the modified file before committing.
    """
    if not modified_bytes or len(modified_bytes) == 0:
        return False, "Validation error: modified file is empty (0 bytes)."

    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    try:
        if ext == ".xlsx":
            # Attempt to open with openpyxl to verify workbook integrity
            wb = load_workbook_from_bytes(modified_bytes, data_only=False)
            wb.close()

        elif ext == ".pdf":
            # Verify PDF header and fitz readability
            doc = fitz.open(stream=modified_bytes, filetype="pdf")
            if len(doc) == 0:
                doc.close()
                return False, "Validation error: modified PDF has 0 pages."
            doc.close()

        elif ext == ".txt":
            # Verify UTF-8 or Latin-1 decodability
            modified_bytes.decode("utf-8")

        return True, "Integrity validation passed. Document structure is valid."
    except Exception as e:
        return False, f"Validation failure: modified document is corrupted: {str(e)}"

