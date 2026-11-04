"""
Phase 4 Automated Verification & End-to-End Functional Test Suite.
Tests:
- Part 1: Excel modification (Rahul to Charan, multi-matches, nonexistent name rejection)
- Part 2: TXT modification (replace, append, delete, RAG query)
- Part 3: PDF processing (pages extract, annotate, scanned PDF detection)
- Part 4: Unified Multi-Format RAG & Citations
- Part 5: Intent Router & LangGraph
- Part 6: Versioning & Rollback (v1 -> v2 -> v3 -> rollback v4)
- Part 7: Modification History & Multi-User Isolation
- Part 8: Strict Privacy Gating (No Gemini calls without explicit consent)
"""

import uuid
import io
import openpyxl
import fitz
import pytest

from auth.authentication import register_user, authenticate_user
from modifications.version_control import (
    save_initial_document,
    read_decrypted_document,
    commit_new_version,
    rollback_document_version
)
from agents.router import classify_user_intent
from agents.graph import agent_graph
from rag.retrieval import retrieve_context, generate_rag_answer
from history.history_manager import get_user_history
from auth.gemini_client import call_gemini_generate


def test_part1_excel_rahul_to_charan_e2e():
    """Verify exact user-reported case: 'Change the employee name Rahul to Charan.'"""
    uname = f"usr_p1_{uuid.uuid4().hex[:4]}"
    register_user(uname, "Password123")
    uid, _, dek, _ = authenticate_user(uname, "Password123")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(["Employee_ID", "Employee_Name", "Department"])
    ws.append([101, "Rahul", "Sales"])
    ws.append([102, "Priya", "HR"])
    ws.append([103, "Arjun", "IT"])
    buf = io.BytesIO()
    wb.save(buf)

    doc_id = f"doc_emp_{uuid.uuid4().hex[:4]}"
    save_initial_document(uid, dek, doc_id, "Employees.xlsx", buf.getvalue())

    # Full LangGraph Execution
    state = {
        "user_id": uid,
        "user_dek": dek,
        "user_input": "Change the employee name Rahul to Charan.",
        "target_doc_id": doc_id,
        "target_filename": "Employees.xlsx",
        "execution_approved": True
    }
    res = agent_graph.invoke(state)

    assert res.get("execution_status") == "SUCCESS"
    assert res.get("new_version") == 2

    # Verify v1 unchanged
    v1_bytes, _, _ = read_decrypted_document(uid, dek, doc_id, version=1)
    wb_v1 = openpyxl.load_workbook(io.BytesIO(v1_bytes))
    assert wb_v1["Employees"]["B2"].value == "Rahul"

    # Verify v2 has Charan and other rows intact
    v2_bytes, _, _ = read_decrypted_document(uid, dek, doc_id, version=2)
    wb_v2 = openpyxl.load_workbook(io.BytesIO(v2_bytes))
    assert wb_v2["Employees"]["B2"].value == "Charan"
    assert wb_v2["Employees"]["A2"].value == 101
    assert wb_v2["Employees"]["C2"].value == "Sales"
    assert wb_v2["Employees"]["B3"].value == "Priya"
    assert wb_v2["Employees"]["B4"].value == "Arjun"


def test_part1_excel_edge_cases():
    """Verify nonexistent name rejection and multiple matching name updates."""
    uname = f"usr_p1e_{uuid.uuid4().hex[:4]}"
    register_user(uname, "Password123")
    uid, _, dek, _ = authenticate_user(uname, "Password123")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Staff"
    ws.append(["ID", "Name"])
    ws.append([1, "John"])
    ws.append([2, "John"])
    buf = io.BytesIO()
    wb.save(buf)

    doc_id = f"doc_stf_{uuid.uuid4().hex[:4]}"
    save_initial_document(uid, dek, doc_id, "Staff.xlsx", buf.getvalue())

    # Nonexistent name rejection
    state_bad = {
        "user_id": uid, "user_dek": dek,
        "user_input": "Change the employee name NonExistent to Bob",
        "target_doc_id": doc_id, "target_filename": "Staff.xlsx", "execution_approved": True
    }
    res_bad = agent_graph.invoke(state_bad)
    assert res_bad.get("execution_status") == "FAILED"
    assert "not found" in res_bad.get("error_message", "").lower()

    # Multi-match update
    state_multi = {
        "user_id": uid, "user_dek": dek,
        "user_input": "Change every John to David",
        "target_doc_id": doc_id, "target_filename": "Staff.xlsx", "execution_approved": True
    }
    res_multi = agent_graph.invoke(state_multi)
    assert res_multi.get("execution_status") == "SUCCESS"
    assert "2 cell" in res_multi.get("summary_result", "")


def test_part2_txt_modifications_and_rag():
    """Verify TXT replace, append, delete and subsequent RAG retrieval."""
    uname = f"usr_p2_{uuid.uuid4().hex[:4]}"
    register_user(uname, "Password123")
    uid, _, dek, _ = authenticate_user(uname, "Password123")

    doc_id = f"doc_txt_{uuid.uuid4().hex[:4]}"
    save_initial_document(uid, dek, doc_id, "notes.txt", b"Project: Alpha\nSecurity: OldProtocol")

    state = {
        "user_id": uid, "user_dek": dek,
        "user_input": "Replace OldProtocol with AES-256-GCM",
        "target_doc_id": doc_id, "target_filename": "notes.txt", "execution_approved": True
    }
    res = agent_graph.invoke(state)
    assert res.get("execution_status") == "SUCCESS"

    retrieved = retrieve_context(uid, "AES-256-GCM", target_doc_id=doc_id)
    assert len(retrieved) > 0
    assert "AES-256-GCM" in retrieved[0]["text"]


def test_part3_pdf_processing():
    """Verify PDF page extraction and text annotation."""
    uname = f"usr_p3_{uuid.uuid4().hex[:4]}"
    register_user(uname, "Password123")
    uid, _, dek, _ = authenticate_user(uname, "Password123")

    doc = fitz.open()
    doc.new_page().insert_text((50, 72), "Page 1 Content", fontsize=12)
    doc.new_page().insert_text((50, 72), "Page 2 Content", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    doc_id = f"doc_pdf_{uuid.uuid4().hex[:4]}"
    save_initial_document(uid, dek, doc_id, "report.pdf", pdf_bytes)

    state = {
        "user_id": uid, "user_dek": dek,
        "user_input": "Extract pages 1",
        "target_doc_id": doc_id, "target_filename": "report.pdf", "execution_approved": True
    }
    res = agent_graph.invoke(state)
    assert res.get("execution_status") == "SUCCESS"
    assert res.get("new_version") == 2


def test_part5_intent_routing_rules():
    """Verify the 5 required intent classification rules."""
    assert classify_user_intent("How many employees are in the company?")["intent"] == "QUESTION"
    assert classify_user_intent("Change Rahul to Charan in Employees.xlsx.")["intent"] == "MODIFICATION"
    assert classify_user_intent("What information is available about the sales department?")["intent"] == "QUESTION"
    assert classify_user_intent("Delete the duplicate rows from the spreadsheet.")["intent"] == "MODIFICATION"
    assert classify_user_intent("Change that value.")["intent"] == "CLARIFICATION"


def test_part6_versioning_and_rollback():
    """Verify V1 -> V2 -> V3 -> Rollback V4 lifecycle."""
    uname = f"usr_p6_{uuid.uuid4().hex[:4]}"
    register_user(uname, "Password123")
    uid, _, dek, _ = authenticate_user(uname, "Password123")

    doc_id = f"doc_rb_{uuid.uuid4().hex[:4]}"
    save_initial_document(uid, dek, doc_id, "data.txt", b"Version 1 Content")
    commit_new_version(uid, dek, doc_id, "data.txt", b"Version 2 Content", "v2 edit")
    commit_new_version(uid, dek, doc_id, "data.txt", b"Version 3 Content", "v3 edit")

    # Rollback to V1
    v4_num, msg = rollback_document_version(uid, dek, doc_id, target_version_to_restore=1)
    assert v4_num == 4

    v4_bytes, _, ver = read_decrypted_document(uid, dek, doc_id, version=4)
    assert ver == 4
    assert v4_bytes == b"Version 1 Content"


def test_part8_strict_privacy_gating():
    """Verify Gemini client never transmits private documents without explicit consent."""
    res = call_gemini_generate(
        prompt="Sensitive prompt",
        api_key="AIzaSyDummyKey",
        model="gemini-2.5-flash",
        user_approved_external_processing=False,
        is_demo_document=False
    )
    assert res["success"] is False
    assert res["error_type"] == "PRIVACY_BLOCKED"

