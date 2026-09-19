import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from src.dashboard.trace_display import (
    build_pipeline_inspector_rows,
    format_trace_clock_time,
    format_trace_iso_milliseconds,
)
from src.orchestrator.engine import run_pipeline
from src.orchestrator.state import AgentState, StepExecutionTrace

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_contract_loader() -> None:
    dummy_zip = PROJECT_ROOT / "tests" / "dummy_dataset.zip"
    contract = {
        "title": "TEST_CONTRACT",
        "paragraphs": [
            {
                "context": "Synthetic contract.",
                "qas": [
                    {
                        "question": "Highlight the parts related to 'Governing Law'...",
                        "id": "qa-governing-law",
                        "is_impossible": False,
                        "answers": [{"text": "Delaware law", "answer_start": 1}],
                    }
                ],
            }
        ],
    }
    with patch(
        "src.agents.extraction._load_contract_from_zip",
        return_value=contract,
    ), patch(
        "src.agents.extraction.get_dataset_zip_path",
        return_value=dummy_zip,
    ):
        yield


def test_trace_timestamps_include_milliseconds(mock_contract_loader: None) -> None:
    state = AgentState(session_id="trace-test", contract_title="TEST_CONTRACT")
    result = asyncio.run(run_pipeline(state))

    assert len(result.execution_traces) == 3
    for trace in result.execution_traces:
        iso_started = format_trace_iso_milliseconds(trace.started_at)
        assert "." in iso_started
        assert len(iso_started.split(".")[-1]) >= 3


def test_trace_sequence_numbers_are_one_two_three(mock_contract_loader: None) -> None:
    state = AgentState(session_id="trace-test", contract_title="TEST_CONTRACT")
    result = asyncio.run(run_pipeline(state))

    sequence_numbers = [trace.sequence_number for trace in result.execution_traces]
    assert sequence_numbers == [1, 2, 3]


def test_trace_duration_ms_exists_and_non_negative(mock_contract_loader: None) -> None:
    state = AgentState(session_id="trace-test", contract_title="TEST_CONTRACT")
    result = asyncio.run(run_pipeline(state))

    for trace in result.execution_traces:
        assert trace.duration_ms >= 0.0
        assert trace.status == "success"


def test_traces_ordered_extraction_risk_summary(mock_contract_loader: None) -> None:
    state = AgentState(session_id="trace-test", contract_title="TEST_CONTRACT")
    result = asyncio.run(run_pipeline(state))

    agent_names = [trace.agent_name for trace in result.execution_traces]
    step_names = [trace.step_name for trace in result.execution_traces]
    assert agent_names == ["ExtractionAgent", "RiskAgent", "SummaryAgent"]
    assert step_names == ["extraction", "risk_assessment", "advisory"]


def test_dashboard_formatting_preserves_millisecond_precision() -> None:
    started = datetime(2026, 6, 20, 10, 1, 3, 120000, tzinfo=timezone.utc)
    completed = datetime(2026, 6, 20, 10, 1, 3, 621000, tzinfo=timezone.utc)
    trace = StepExecutionTrace(
        agent_name="ExtractionAgent",
        step_name="extraction",
        sequence_number=1,
        status="success",
        started_at=started,
        completed_at=completed,
        duration_ms=501.0,
        timestamp=completed,
        input_received={},
        agent_rationale="test",
        output_generated={},
    )

    rows = build_pipeline_inspector_rows([trace])
    assert rows[0]["Started (UTC)"] == "10:01:03.120"
    assert rows[0]["Completed (UTC)"] == "10:01:03.621"
    assert rows[0]["Duration (ms)"] == "501.000"


def test_timestamp_display_does_not_collapse_to_second_only() -> None:
    traces = [
        StepExecutionTrace(
            agent_name="ExtractionAgent",
            step_name="extraction",
            sequence_number=1,
            status="success",
            started_at=datetime(2026, 6, 20, 10, 1, 3, 120000, tzinfo=timezone.utc),
            completed_at=datetime(2026, 6, 20, 10, 1, 3, 461000, tzinfo=timezone.utc),
            duration_ms=341.0,
            timestamp=datetime(2026, 6, 20, 10, 1, 3, 461000, tzinfo=timezone.utc),
            input_received={},
            agent_rationale="a",
            output_generated={},
        ),
        StepExecutionTrace(
            agent_name="RiskAgent",
            step_name="risk_assessment",
            sequence_number=2,
            status="success",
            started_at=datetime(2026, 6, 20, 10, 1, 3, 462000, tzinfo=timezone.utc),
            completed_at=datetime(2026, 6, 20, 10, 1, 3, 621000, tzinfo=timezone.utc),
            duration_ms=159.0,
            timestamp=datetime(2026, 6, 20, 10, 1, 3, 621000, tzinfo=timezone.utc),
            input_received={},
            agent_rationale="b",
            output_generated={},
        ),
    ]

    rows = build_pipeline_inspector_rows(traces)
    completed_values = [row["Completed (UTC)"] for row in rows]
    assert completed_values == ["10:01:03.461", "10:01:03.621"]
    assert len(set(completed_values)) == 2
    assert all("." in value and len(value.split(".")[-1]) == 3 for value in completed_values)


def test_format_trace_clock_time_string_not_datetime_object() -> None:
    formatted = format_trace_clock_time(
        datetime(2026, 6, 20, 10, 1, 3, 5000, tzinfo=timezone.utc)
    )
    assert isinstance(formatted, str)
    assert formatted == "10:01:03.005"
