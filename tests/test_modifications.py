"""
Test Suite for Multi-Format Document Modifications.
"""

import openpyxl
import io
from processors.txt_processor import append_to_txt, replace_in_txt, delete_from_txt
from processors.excel_processor import update_cell_value, remove_duplicate_rows
from modifications.planner import generate_structured_plan
from modifications.executor import execute_plan


def test_txt_modifications():
    base_text = b"Line 1: Hello World\nLine 2: Temporary Text"

    # Append
    appended = append_to_txt(base_text, "Line 3: Extra Info")
    assert b"Line 3: Extra Info" in appended

    # Replace
    replaced, count = replace_in_txt(base_text, "Hello World", "Welcome Home")
    assert count == 1
    assert b"Welcome Home" in replaced

    # Delete
    deleted, del_count = delete_from_txt(base_text, "Temporary Text")
    assert del_count == 1
    assert b"Temporary Text" not in deleted


def test_excel_modifications():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["A1"] = "Metric"
    ws["B1"] = "Value"
    ws["A2"] = "Headcount"
    ws["B2"] = 50
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    excel_bytes = buf.getvalue()

    # Plan generation from natural language
    plan = generate_structured_plan("Update cell B2 with 75", "test.xlsx")
    assert plan["action"] == "EXCEL_UPDATE_CELL"
    assert plan["parameters"]["coordinate"] == "B2"

    # Execution
    mod_bytes, summary = execute_plan(plan, excel_bytes)
    assert "75" in summary

    # Verify updated value
    wb_updated = openpyxl.load_workbook(io.BytesIO(mod_bytes))
    assert wb_updated["Sheet1"]["B2"].value == 75
    wb_updated.close()

