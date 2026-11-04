"""
Excel (.xlsx) Document Processor.

Provides:
- Worksheet discovery and structure inspection
- Reading cell values and formula extraction
- Controlled cell value updates and formula insertion
- Cell search and replacement (exact match and value update)
- Duplicate row removal
- Column addition and custom calculations
- Data sorting
"""

import io
import openpyxl
from openpyxl.utils import get_column_letter
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional


def load_workbook_from_bytes(content_bytes: bytes, data_only: bool = False) -> openpyxl.Workbook:
    """Loads an openpyxl Workbook from raw bytes."""
    return openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=data_only)


def save_workbook_to_bytes(wb: openpyxl.Workbook) -> bytes:
    """Serializes an openpyxl Workbook back into raw bytes."""
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def inspect_excel(content_bytes: bytes) -> Dict[str, Any]:
    """
    Inspects sheets, headers, sample rows, and formulas.
    """
    wb_formulas = load_workbook_from_bytes(content_bytes, data_only=False)
    wb_values = load_workbook_from_bytes(content_bytes, data_only=True)

    sheet_names = wb_formulas.sheetnames
    structure = {"sheet_names": sheet_names, "sheets": {}}

    for name in sheet_names:
        ws_f = wb_formulas[name]
        ws_v = wb_values[name]

        max_row = ws_f.max_row or 0
        max_col = ws_f.max_column or 0

        headers = []
        for c in range(1, max_col + 1):
            val = ws_v.cell(row=1, column=c).value
            headers.append(str(val) if val is not None else f"Column_{get_column_letter(c)}")

        formulas = []
        sample_rows = []

        row_limit = min(max_row, 30)
        for r in range(1, row_limit + 1):
            row_dict = {}
            for c in range(1, max_col + 1):
                col_letter = get_column_letter(c)
                f_val = ws_f.cell(row=r, column=c).value
                v_val = ws_v.cell(row=r, column=c).value

                if isinstance(f_val, str) and f_val.startswith("="):
                    formulas.append({
                        "cell": f"{col_letter}{r}",
                        "formula": f_val,
                        "value": str(v_val) if v_val is not None else ""
                    })

                col_name = headers[c - 1] if c - 1 < len(headers) else col_letter
                row_dict[col_name] = v_val

            if r > 1 and len(sample_rows) < 10:
                sample_rows.append(row_dict)

        structure["sheets"][name] = {
            "max_row": max_row,
            "max_col": max_col,
            "headers": headers,
            "formulas": formulas,
            "sample_rows": sample_rows
        }

    wb_formulas.close()
    wb_values.close()
    return structure


def update_cell_value(
    content_bytes: bytes,
    sheet_name: str,
    coordinate: str,
    new_value: Any
) -> Tuple[bytes, Any, Any]:
    """
    Updates a specific cell (e.g. 'B5') with a value or formula.
    Returns: (modified_bytes, old_value, new_value)
    """
    wb = load_workbook_from_bytes(content_bytes, data_only=False)
    sheet = sheet_name if sheet_name in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet]
    cell = ws[coordinate]
    old_value = cell.value

    # Parse numeric values if passed as string numbers
    val_str = str(new_value).strip()
    if val_str.startswith("="):
        cell.value = val_str  # Formula
    else:
        try:
            if "." in val_str:
                cell.value = float(val_str)
            else:
                cell.value = int(val_str)
        except ValueError:
            cell.value = new_value

    modified_bytes = save_workbook_to_bytes(wb)
    wb.close()
    return modified_bytes, old_value, cell.value


def replace_excel_cell_value(
    content_bytes: bytes,
    target_value: str,
    replacement_value: str,
    sheet_name: Optional[str] = None,
    match_all: bool = False
) -> Tuple[bytes, int, List[str]]:
    """
    Finds cells containing target_value and replaces them with replacement_value.
    If match_all is False, replaces the exact first match. If match_all is True, replaces all matches.
    Preserves other rows, columns, styles, and formulas.

    Returns:
    (modified_bytes, count_of_cells_replaced, list_of_coordinates_changed)
    """
    wb = load_workbook_from_bytes(content_bytes, data_only=False)
    target_clean = str(target_value).strip().lower()
    repl_clean = str(replacement_value).strip()

    # Determine sheets to inspect
    sheets_to_check = [sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.sheetnames
    replaced_coords = []

    for s_name in sheets_to_check:
        ws = wb[s_name]
        max_r = ws.max_row or 0
        max_c = ws.max_column or 0

        for r in range(1, max_r + 1):
            for c in range(1, max_c + 1):
                cell = ws.cell(row=r, column=c)
                val = cell.value
                if val is not None and str(val).strip().lower() == target_clean:
                    # Apply replacement
                    if repl_clean.startswith("="):
                        cell.value = repl_clean
                    else:
                        try:
                            if "." in repl_clean:
                                cell.value = float(repl_clean)
                            elif repl_clean.isdigit() or (repl_clean.startswith("-") and repl_clean[1:].isdigit()):
                                cell.value = int(repl_clean)
                            else:
                                cell.value = repl_clean
                        except ValueError:
                            cell.value = repl_clean

                    col_letter = get_column_letter(c)
                    replaced_coords.append(f"{s_name}!{col_letter}{r}")
                    if not match_all:
                        break
            if replaced_coords and not match_all:
                break
        if replaced_coords and not match_all:
            break

    if not replaced_coords:
        wb.close()
        raise ValueError(f"Target value '{target_value}' was not found in worksheet.")

    modified_bytes = save_workbook_to_bytes(wb)
    wb.close()
    return modified_bytes, len(replaced_coords), replaced_coords


def remove_duplicate_rows(content_bytes: bytes, sheet_name: str) -> Tuple[bytes, int]:
    """
    Removes duplicate data rows from a sheet using Pandas.
    Returns: (modified_bytes, rows_removed_count)
    """
    excel_file = io.BytesIO(content_bytes)
    # Check sheets
    wb = openpyxl.load_workbook(io.BytesIO(content_bytes), read_only=True)
    target_sheet = sheet_name if sheet_name in wb.sheetnames else wb.sheetnames[0]
    wb.close()

    df = pd.read_excel(excel_file, sheet_name=target_sheet)
    initial_count = len(df)
    df_cleaned = df.drop_duplicates()
    removed = initial_count - len(df_cleaned)

    # Save back
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_cleaned.to_excel(writer, sheet_name=target_sheet, index=False)
    return output.getvalue(), removed


def sort_sheet_data(
    content_bytes: bytes,
    sheet_name: str,
    column_name: str,
    ascending: bool = True
) -> bytes:
    """
    Sorts a worksheet by a specified column.
    """
    excel_file = io.BytesIO(content_bytes)
    wb = openpyxl.load_workbook(io.BytesIO(content_bytes), read_only=True)
    target_sheet = sheet_name if sheet_name in wb.sheetnames else wb.sheetnames[0]
    wb.close()

    df = pd.read_excel(excel_file, sheet_name=target_sheet)
    if column_name not in df.columns:
        # Case insensitive match
        col_map = {c.lower(): c for c in df.columns}
        if column_name.lower() in col_map:
            column_name = col_map[column_name.lower()]
        else:
            raise ValueError(f"Column '{column_name}' not found in sheet '{target_sheet}'. Available: {list(df.columns)}")

    df_sorted = df.sort_values(by=column_name, ascending=ascending)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_sorted.to_excel(writer, sheet_name=target_sheet, index=False)
    return output.getvalue()
