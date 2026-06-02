"""Focused tests for the Synthesizer node."""

import importlib

from quorum.schemas.critique import ArbitrationResult
from quorum.schemas.plan import QueryPlan, QueryStep
from quorum.schemas.query import QueryResult
from quorum.schemas.report import InsightReport
from quorum.state import AgentState

synthesizer_module = importlib.import_module("quorum.nodes.synthesizer")


class FakeClaudeClient:
    """Simple async fake for synthesizer LLM calls."""

    def __init__(self, response: InsightReport):
        self.response = response
        self.calls = []

    async def call_llm(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_query_result(
    *,
    step_number: int = 1,
    sql_executed: str = "SELECT C_NAME, 123.45 AS TOTAL_REVENUE FROM CUSTOMER LIMIT 50",
    rows: list[list[object]] | None = None,
) -> QueryResult:
    return QueryResult(
        step_number=step_number,
        sql_executed=sql_executed,
        columns=["C_NAME", "TOTAL_REVENUE"],
        rows=rows or [["Customer#000000001", 123.45]],
        row_count=1,
        execution_time_ms=10.0,
        success=True,
    )


def make_plan() -> QueryPlan:
    step = QueryStep(
        step_number=1,
        objective="Rank customers by total revenue",
        tables_required=["CUSTOMER"],
        expected_columns=["C_NAME", "TOTAL_REVENUE"],
        expected_output_description="Ranked customer revenue table",
    )
    return QueryPlan(
        original_question="Which customers generated the most revenue?",
        reasoning="A single aggregate query can answer the question.",
        steps=[step],
        total_steps=1,
    )


def make_arbitration() -> ArbitrationResult:
    return ArbitrationResult(
        step_number=1,
        final_approved=True,
        vote_summary={"openai": True, "gemini": True, "deepseek": True},
        avg_confidence=0.82,
        dissenting_critics=[],
        disagreement_analysis="All critics approved with shared row-limit caveats.",
        merged_correction=None,
        final_confidence=0.84,
        arbitration_reasoning="The result answers the objective.",
    )


def make_state(**overrides) -> AgentState:
    values = {
        "question": "Which customers generated the most revenue?",
        "schema_context": "TPCH schema context",
        "query_plan": make_plan(),
        "attempts": 2,
    }
    values.update(overrides)
    return AgentState(**values)


def make_llm_report() -> InsightReport:
    return InsightReport(
        original_question="wrong question",
        executive_summary="Customer#000000001 generated 123.45 in revenue.",
        key_findings=["Customer#000000001 generated 123.45 in revenue."],
        data_tables=[],
        caveats=["LLM-provided caveat."],
        ensemble_summary=[],
        total_attempts=0,
        steps_executed=0,
        models_used=[],
    )


def test_empty_results_returns_failure_report_without_llm(monkeypatch):
    fake_client = FakeClaudeClient(make_llm_report())
    monkeypatch.setattr(synthesizer_module, "claude_client", fake_client)

    result = synthesizer_module.synthesizer(make_state(all_results=[]))

    report = result["insight_report"]
    assert result["status"] == "failed"
    assert fake_client.calls == []
    assert report.original_question == "Which customers generated the most revenue?"
    assert report.key_findings == []
    assert report.data_tables == []
    assert report.steps_executed == 0
    assert "No query result was approved within the retry limit." in report.caveats
    for caveat in synthesizer_module.MANDATORY_CAVEATS:
        assert caveat in report.caveats


def test_synthesizer_calls_claude_with_approved_results_only(monkeypatch):
    approved_result = make_query_result()
    unapproved_current_result = make_query_result(
        step_number=2,
        sql_executed="SELECT * FROM SHOULD_NOT_APPEAR LIMIT 50",
        rows=[["unapproved", 0]],
    )
    fake_client = FakeClaudeClient(make_llm_report())
    monkeypatch.setattr(synthesizer_module, "claude_client", fake_client)

    result = synthesizer_module.synthesizer(
        make_state(
            all_results=[approved_result],
            query_result=unapproved_current_result,
            arbitration=make_arbitration(),
        )
    )

    report = result["insight_report"]
    assert result["status"] == "complete"
    assert fake_client.calls[0]["system_prompt"] == synthesizer_module.SYNTHESIZER_PROMPT
    assert fake_client.calls[0]["model_string"] == "claude-sonnet-4-6"
    assert fake_client.calls[0]["response_model"] is InsightReport
    assert "Customer#000000001" in fake_client.calls[0]["user_prompt"]
    assert "SHOULD_NOT_APPEAR" not in fake_client.calls[0]["user_prompt"]
    assert report.data_tables == [approved_result]
    assert report.steps_executed == 1


def test_synthesizer_attaches_runtime_fields_and_mandatory_caveats(monkeypatch):
    approved_result = make_query_result()
    arbitration = make_arbitration()
    fake_client = FakeClaudeClient(make_llm_report())
    monkeypatch.setattr(synthesizer_module, "claude_client", fake_client)

    result = synthesizer_module.synthesizer(
        make_state(
            all_results=[approved_result],
            arbitration_history=[arbitration],
            attempts=3,
        )
    )

    report = result["insight_report"]
    assert report.original_question == "Which customers generated the most revenue?"
    assert report.data_tables == [approved_result]
    assert report.ensemble_summary == [arbitration]
    assert report.total_attempts == 3
    assert report.steps_executed == 1
    assert report.models_used == synthesizer_module.MODELS_USED
    assert report.generated_at is not None
    assert "LLM-provided caveat." in report.caveats
    for caveat in synthesizer_module.MANDATORY_CAVEATS:
        assert caveat in report.caveats
