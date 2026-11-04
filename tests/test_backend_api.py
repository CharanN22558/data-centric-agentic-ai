"""
FastAPI Backend API Unit Tests.
Uses direct handler execution to guarantee zero network hanging during test runs.
"""

import pytest
import server
from database.db_manager import init_database
from history.history_manager import record_history_entry


@pytest.fixture(autouse=True)
def setup_db():
    init_database()


def test_health_check_endpoint():
    res = server.health_check()
    assert res["status"] == "healthy"
    assert res["port"] == 8000
    assert res["database_connected"] is True


def test_metrics_endpoint():
    # Insert a test history entry
    record_history_entry(
        user_id=1,
        doc_id="doc_test_metrics",
        instruction="Update cell A1",
        ai_interpretation="Updating cell",
        intent_classification="MODIFICATION",
        planned_operation="EXCEL_UPDATE_CELL",
        execution_status="SUCCESS",
        validation_result="Passed",
        previous_version=1,
        new_version=2,
        summary_result="Cell updated"
    )

    data = server.get_dashboard_metrics(user_id=1)
    assert data["status"] == "success"
    assert data["backend_online"] is True
    assert "metrics" in data
    assert data["metrics"]["successful_modifications"] >= 1
