"""Focused tests for Arbiter and Step Router nodes."""

import importlib
from pytest import approx

from quorum.schemas.critique import ArbitrationResult, CritiqueResult
from quorum.schemas.plan import QueryPlan, QueryStep
from quorum.schemas.query import QueryResult, ValidatedQuery
from quorum.state import AgentState

arbiter_module = importlib.import_module("quorum.nodes.arbiter")
step_router_module = importlib.import_module("quorum.nodes.step_router")


class FakeClaudeClient:
    """Simple async fake for arbiter LLM calls."""

    def __init__(self, response: ArbitrationResult):
        self.response = response
        self.calls = []

    async def call_llm(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_plan() -> QueryPlan:
    step = QueryStep(
        step_number=1,
        objective="Rank customers by total revenue",
        tables_required=["CUSTOMER", "ORDERS", "LINEITEM"],
        expected_columns=["C_NAME", "TOTAL_REVENUE"],
        expected_output_description="Ranked customer revenue table",
    )
    return QueryPlan(
        original_question="Which customers generated the most revenue?",
        reasoning="A joined aggregate query can rank customers by revenue.",
        steps=[step],
        total_steps=1,
    )


def make_query_result(step_number: int = 1) -> QueryResult:
    return QueryResult(
        step_number=step_number,
        sql_executed="SELECT C_NAME FROM CUSTOMER LIMIT 50",
        columns=["C_NAME"],
        rows=[["Customer#000000001"]],
        row_count=1,
        execution_time_ms=11.0,
        success=True,
    )


def make_validated_query(step_number: int = 1) -> ValidatedQuery:
    return ValidatedQuery(
        step_number=step_number,
        sql="SELECT C_NAME FROM CUSTOMER LIMIT 50",
        target_tables=["CUSTOMER"],
        explanation="Returns customer names.",
        estimated_row_limit=50,
    )


def make_critique(
    critic_id: str,
    *,
    approved: bool = True,
    confidence_score: float = 0.8,
) -> CritiqueResult:
    return CritiqueResult(
        critic_id=critic_id,
        step_number=1,
        approved=approved,
        confidence_score=confidence_score,
        issues_found=[] if approved else [f"{critic_id} issue"],
        suggested_correction=None if approved else f"Fix {critic_id} issue.",
        reasoning=f"{critic_id} critique reasoning.",
    )


def make_arbitration_response(
    *,
    final_approved: bool = True,
    avg_confidence: float = 0.01,
) -> ArbitrationResult:
    return ArbitrationResult(
        step_number=99,
        final_approved=final_approved,
        vote_summary={"openai": False, "gemini": False, "deepseek": False},
        avg_confidence=avg_confidence,
        dissenting_critics=[],
        disagreement_analysis="LLM disagreement analysis.",
        merged_correction=None,
        final_confidence=0.76,
        arbitration_reasoning="LLM arbitration reasoning.",
    )


def make_state(**overrides) -> AgentState:
    values = {
        "question": "Which customers generated the most revenue?",
        "schema_context": "TPCH schema context",
        "query_plan": make_plan(),
        "validated_query": make_validated_query(),
        "query_result": make_query_result(),
        "critique_openai": make_critique("openai", confidence_score=0.9),
        "critique_gemini": make_critique("gemini", confidence_score=0.8),
        "critique_deepseek": make_critique("deepseek", confidence_score=0.7),
        "attempts": 1,
        "max_attempts": 3,
    }
    values.update(overrides)
    return AgentState(**values)


def test_arbiter_calculates_avg_confidence_in_python(monkeypatch):
    fake_client = FakeClaudeClient(make_arbitration_response(avg_confidence=0.01))
    monkeypatch.setattr(arbiter_module, "claude_opus_client", fake_client)

    result = arbiter_module.arbiter(make_state())

    arbitration = result["arbitration"]
    assert arbitration.avg_confidence == approx(0.8)
    assert arbitration.step_number == 1
    assert arbitration.vote_summary == {
        "openai": True,
        "gemini": True,
        "deepseek": True,
    }
    assert fake_client.calls[0]["model_string"] == "claude-opus-4-6"
    assert fake_client.calls[0]["response_model"] is ArbitrationResult
    assert "avg_confidence calculated by Python:" in fake_client.calls[0]["user_prompt"]
    assert "0.8" in fake_client.calls[0]["user_prompt"]


def test_arbiter_treats_missing_critique_as_zero_confidence_rejection(monkeypatch):
    fake_client = FakeClaudeClient(make_arbitration_response(final_approved=True))
    monkeypatch.setattr(arbiter_module, "claude_opus_client", fake_client)

    result = arbiter_module.arbiter(
        make_state(
            critique_gemini=None,
            critique_openai=make_critique("openai", confidence_score=0.9),
            critique_deepseek=make_critique("deepseek", confidence_score=0.6),
        )
    )

    arbitration = result["arbitration"]
    assert arbitration.avg_confidence == approx(0.5)
    assert arbitration.vote_summary == {
        "openai": True,
        "gemini": False,
        "deepseek": True,
    }
    assert "gemini critique missing" in fake_client.calls[0]["user_prompt"]


def test_arbiter_rejects_unanimous_low_confidence_approval(monkeypatch):
    fake_client = FakeClaudeClient(make_arbitration_response(final_approved=True))
    monkeypatch.setattr(arbiter_module, "claude_opus_client", fake_client)

    result = arbiter_module.arbiter(
        make_state(
            critique_openai=make_critique("openai", confidence_score=0.65),
            critique_gemini=make_critique("gemini", confidence_score=0.66),
            critique_deepseek=make_critique("deepseek", confidence_score=0.67),
        )
    )

    assert result["arbitration"].avg_confidence < 0.70
    assert result["arbitration"].final_approved is False


def test_arbiter_approves_when_max_attempts_reached(monkeypatch):
    fake_client = FakeClaudeClient(make_arbitration_response(final_approved=False))
    monkeypatch.setattr(arbiter_module, "claude_opus_client", fake_client)

    result = arbiter_module.arbiter(
        make_state(
            critique_openai=make_critique("openai", approved=False, confidence_score=0.2),
            critique_gemini=make_critique("gemini", approved=False, confidence_score=0.3),
            critique_deepseek=make_critique("deepseek", approved=False, confidence_score=0.4),
            attempts=3,
            max_attempts=3,
        )
    )

    assert result["arbitration"].final_approved is True


def test_step_router_appends_result_advances_step_and_resets_step_fields():
    prior_result = make_query_result(step_number=0)
    current_result = make_query_result(step_number=1)
    state = make_state(
        all_results=[prior_result],
        current_step_index=0,
        query_result=current_result,
        arbitration=make_arbitration_response(final_approved=True),
        attempts=2,
    )

    result = step_router_module.step_router(state)

    assert result == {
        "all_results": [prior_result, current_result],
        "arbitration_history": [state.arbitration],
        "current_step_index": 1,
        "critique_openai": None,
        "critique_gemini": None,
        "critique_deepseek": None,
        "arbitration": None,
        "validated_query": None,
        "query_result": None,
        "attempts": 0,
    }
