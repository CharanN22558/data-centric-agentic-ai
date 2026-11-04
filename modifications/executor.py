"""
Predefined Tool Execution Dispatcher.

Executes the structured plan strictly through verified Python processors.
Zero dynamic code evaluation.
"""

from typing import Dict, Any, Tuple
from processors.txt_processor import append_to_txt, replace_in_txt, delete_from_txt
from processors.excel_processor import update_cell_value, replace_excel_cell_value, remove_duplicate_rows, sort_sheet_data
from processors.pdf_processor import add_pdf_text_annotation, extract_pdf_pages


def execute_plan(plan: Dict[str, Any], file_bytes: bytes) -> Tuple[bytes, str]:
    """
    Executes a predefined operation on document bytes.
    Returns: (modified_bytes, operation_summary)
    """
    action = plan.get("action", "")
    params = plan.get("parameters", {})

    # =========================================================
    # TXT Operations
    # =========================================================
    if action == "TXT_APPEND":
        text = params.get("text", "")
        res = append_to_txt(file_bytes, text)
        return res, f"Appended {len(text)} characters to text file."

    elif action == "TXT_REPLACE":
        target = params.get("target", "")
        repl = params.get("replacement", "")
        res, count = replace_in_txt(file_bytes, target, repl)
        if count == 0:
            raise ValueError(f"Target text '{target}' was not found in text document.")
        return res, f"Replaced {count} occurrence(s) of '{target}' with '{repl}'."

    elif action == "TXT_DELETE":
        target = params.get("target", "")
        res, count = delete_from_txt(file_bytes, target)
        if count == 0:
            raise ValueError(f"Target text '{target}' was not found in text document.")
        return res, f"Deleted {count} occurrence(s) of '{target}'."

    # =========================================================
    # Excel Operations
    # =========================================================
    elif action == "EXCEL_UPDATE_CELL":
        sheet = params.get("sheet_name", "Sheet1")
        coord = params.get("coordinate", "A1")
        val = params.get("value", "")
        res, old_v, new_v = update_cell_value(file_bytes, sheet, coord, val)
        return res, f"Updated cell {coord} on sheet '{sheet}' from '{old_v}' to '{new_v}'."

    elif action == "EXCEL_REPLACE_VALUE":
        target = params.get("target_value", "")
        repl = params.get("replacement_value", "")
        sheet = params.get("sheet_name")
        match_all = params.get("match_all", False)
        res, count, coords = replace_excel_cell_value(
            file_bytes,
            target_value=target,
            replacement_value=repl,
            sheet_name=sheet,
            match_all=match_all
        )
        return res, f"Changed '{target}' to '{repl}' at cell {', '.join(coords)} ({count} cell updated)."

    elif action == "EXCEL_REMOVE_DUPLICATES":
        sheet = params.get("sheet_name", "Sheet1")
        res, count = remove_duplicate_rows(file_bytes, sheet)
        return res, f"Removed {count} duplicate row(s) from sheet '{sheet}'."

    elif action == "EXCEL_SORT":
        sheet = params.get("sheet_name", "Sheet1")
        col = params.get("column", "")
        asc = params.get("ascending", True)
        res = sort_sheet_data(file_bytes, sheet, col, asc)
        return res, f"Sorted sheet '{sheet}' by column '{col}' in {'ascending' if asc else 'descending'} order."

    # =========================================================
    # PDF Operations
    # =========================================================
    elif action == "PDF_ANNOTATE":
        page = params.get("page", 1)
        txt = params.get("text", "Reviewed")
        res = add_pdf_text_annotation(file_bytes, page, txt)
        return res, f"Added text annotation '{txt}' to page {page}."

    elif action == "PDF_EXTRACT_PAGES":
        pages = params.get("pages", [1])
        res = extract_pdf_pages(file_bytes, pages)
        return res, f"Extracted pages {pages} into a new document version."

    else:
        raise ValueError(f"Unknown or unsupported modification action '{action}'.")


def execute_modification_plan(current_bytes: bytes, extension: str, plan: Dict[str, Any]) -> Tuple[bool, bytes, str]:
    """
    Standard interface for executing a structured modification plan.
    Returns: (success_bool, modified_bytes, summary_message)
    """
    try:
        modified_bytes, summary = execute_plan(plan, current_bytes)
        return True, modified_bytes, summary
    except Exception as e:
        return False, b"", str(e)

