"""Focused tests for critic helper logic and critic nodes."""

import importlib

import pytest

from quorum.schemas.critique import CritiqueResult
from quorum.schemas.plan import QueryPlan, QueryStep
from quorum.schemas.query import QueryResult
from quorum.state import AgentState

critic_openai_module = importlib.import_module("quorum.nodes.critic_openai")
critic_gemini_module = importlib.import_module("quorum.nodes.critic_gemini")
critic_deepseek_module = importlib.import_module("quorum.nodes.critic_deepseek")
critic_helpers = importlib.import_module("quorum.nodes.critic_helpers")


class FakeCriticClient:
    """Simple async fake for critic node LLM calls."""

    def __init__(self, response: CritiqueResult):
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


def make_query_result(
    *,
    success: bool = True,
    row_count: int = 1,
    rows: list[list[object]] | None = None,
    columns: list[str] | None = None,
    error_detail: str | None = None,
) -> QueryResult:
    if columns is None:
        columns = ["C_NAME", "TOTAL_REVENUE"]
    if rows is None:
        rows = [["Customer#000000001", 123.45]] if row_count else []
    return QueryResult(
        step_number=1,
        sql_executed="SELECT C_NAME, 123.45 AS TOTAL_REVENUE FROM CUSTOMER LIMIT 50",
        columns=columns,
        rows=rows,
        row_count=row_count,
        execution_time_ms=10.0,
        success=success,
        error_detail=error_detail,
    )


def make_state(query_result: QueryResult) -> AgentState:
    return AgentState(
        question="Which customers generated the most revenue?",
        schema_context="TPCH schema context",
        query_plan=make_plan(),
        query_result=query_result,
    )


def make_llm_critique(critic_id: str = "openai") -> CritiqueResult:
    return CritiqueResult(
        critic_id=critic_id,
        step_number=99,
        approved=True,
        confidence_score=0.82,
        issues_found=[],
        reasoning="The result appears to answer the objective.",
    )


@pytest.mark.parametrize(
    ("module", "client_attr", "node_name", "field_name", "critic_id"),
    [
        (
            critic_openai_module,
            "openai_client",
            "critic_openai",
            "critique_openai",
            "openai",
        ),
        (
            critic_gemini_module,
            "gemini_client",
            "critic_gemini",
            "critique_gemini",
            "gemini",
        ),
        (
            critic_deepseek_module,
            "deepseek_client",
            "critic_deepseek",
            "critique_deepseek",
            "deepseek",
        ),
    ],
)
def test_failed_sql_precheck_rejects_without_llm_call(
    monkeypatch,
    module,
    client_attr,
    node_name,
    field_name,
    critic_id,
):
    fake_client = FakeCriticClient(make_llm_critique(critic_id))
    monkeypatch.setattr(module, client_attr, fake_client)

    result = getattr(module, node_name)(
        make_state(
            make_query_result(
                success=False,
                row_count=0,
                rows=[],
                error_detail="SQL compilation error",
            )
        )
    )

    critique = result[field_name]
    assert fake_client.calls == []
    assert critique.critic_id == critic_id
    assert critique.approved is False
    assert critique.confidence_score == 0.0
    assert critique.issues_found == ["SQL compilation error"]


def test_zero_rows_precheck_rejects_without_llm_call(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("openai"))
    monkeypatch.setattr(critic_openai_module, "openai_client", fake_client)

    result = critic_openai_module.critic_openai(
        make_state(make_query_result(row_count=0, rows=[]))
    )

    critique = result["critique_openai"]
    assert fake_client.calls == []
    assert critique.approved is False
    assert critique.issues_found == ["Query returned no rows"]


def test_all_null_column_precheck_rejects_without_llm_call(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("gemini"))
    monkeypatch.setattr(critic_gemini_module, "gemini_client", fake_client)

    result = critic_gemini_module.critic_gemini(
        make_state(
            make_query_result(
                columns=["C_NAME", "TOTAL_REVENUE"],
                rows=[["Customer#000000001", None], ["Customer#000000002", None]],
                row_count=2,
            )
        )
    )

    critique = result["critique_gemini"]
    assert fake_client.calls == []
    assert critique.approved is False
    assert critique.issues_found == ["Column TOTAL_REVENUE all NULL"]


def test_openai_critic_calls_gpt_55_and_sets_identity(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("gemini"))
    monkeypatch.setattr(critic_openai_module, "openai_client", fake_client)

    result = critic_openai_module.critic_openai(make_state(make_query_result()))

    critique = result["critique_openai"]
    assert critique.critic_id == "openai"
    assert critique.step_number == 1
    assert fake_client.calls[0]["model_string"] == "gpt-5.5-2026-04-23"
    assert fake_client.calls[0]["response_model"] is CritiqueResult
    assert fake_client.calls[0]["system_prompt"] == critic_helpers.CRITIC_PROMPT
    assert "Rank customers by total revenue" in fake_client.calls[0]["user_prompt"]


def test_gemini_critic_calls_gemini_model(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("openai"))
    monkeypatch.setattr(critic_gemini_module, "gemini_client", fake_client)

    result = critic_gemini_module.critic_gemini(make_state(make_query_result()))

    assert result["critique_gemini"].critic_id == "gemini"
    assert fake_client.calls[0]["model_string"] == "gemini-3.1-pro-preview"


def test_deepseek_critic_calls_deepseek_with_thinking_enabled(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("openai"))
    monkeypatch.setattr(critic_deepseek_module, "deepseek_client", fake_client)

    result = critic_deepseek_module.critic_deepseek(make_state(make_query_result()))

    assert result["critique_deepseek"].critic_id == "deepseek"
    assert fake_client.calls[0]["model_string"] == "deepseek-v4-pro"
    assert fake_client.calls[0]["enable_thinking"] is True


def test_high_row_count_adds_truncation_warning_to_prompt(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("openai"))
    monkeypatch.setattr(critic_openai_module, "openai_client", fake_client)

    critic_openai_module.critic_openai(
        make_state(
            make_query_result(
                row_count=95,
                rows=[["Customer#000000001", 123.45]],
            )
        )
    )

    assert critic_helpers.TRUNCATION_WARNING in fake_client.calls[0]["user_prompt"]


def test_lower_row_count_omits_truncation_warning_from_prompt(monkeypatch):
    fake_client = FakeCriticClient(make_llm_critique("openai"))
    monkeypatch.setattr(critic_openai_module, "openai_client", fake_client)

    critic_openai_module.critic_openai(make_state(make_query_result(row_count=94)))

    assert critic_helpers.TRUNCATION_WARNING not in fake_client.calls[0]["user_prompt"]
