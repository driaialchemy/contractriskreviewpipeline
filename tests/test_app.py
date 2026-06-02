"""Smoke tests for Streamlit UI helper functions."""

import json

from app import _rows_as_dicts, report_to_json
from quorum.schemas.query import QueryResult
from quorum.schemas.report import InsightReport


def make_query_result() -> QueryResult:
    return QueryResult(
        step_number=1,
        sql_executed="SELECT C_NAME FROM CUSTOMER LIMIT 50",
        columns=["C_NAME", "TOTAL_REVENUE"],
        rows=[["Customer#000000001", 123.45]],
        row_count=1,
        execution_time_ms=10.0,
        success=True,
    )


def test_rows_as_dicts_maps_columns_to_row_values():
    assert _rows_as_dicts(make_query_result()) == [
        {"C_NAME": "Customer#000000001", "TOTAL_REVENUE": 123.45}
    ]


def test_report_to_json_exports_valid_report_json():
    report = InsightReport(
        original_question="Question?",
        executive_summary="Answer.",
        key_findings=["Finding."],
        data_tables=[make_query_result()],
        caveats=["Caveat."],
        total_attempts=1,
        steps_executed=1,
        models_used=["mock-model"],
    )

    exported = json.loads(report_to_json(report))

    assert exported["original_question"] == "Question?"
    assert exported["data_tables"][0]["sql_executed"] == "SELECT C_NAME FROM CUSTOMER LIMIT 50"
