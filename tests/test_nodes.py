"""Focused tests for Planner and SQL Generator nodes."""

import importlib

import pytest

from quorum.schemas.critique import ArbitrationResult
from quorum.schemas.plan import QueryPlan, QueryStep
from quorum.schemas.query import ValidatedQuery
from quorum.state import AgentState
from quorum.tools import SQLValidationError

planner_module = importlib.import_module("quorum.nodes.planner")
sql_generator_module = importlib.import_module("quorum.nodes.sql_generator")


class FakeClaudeClient:
    """Simple async fake for node-level LLM client tests."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    async def call_llm(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_step(step_number: int = 1) -> QueryStep:
    return QueryStep(
        step_number=step_number,
        objective=f"Retrieve step {step_number} revenue metrics",
        tables_required=["CUSTOMER", "ORDERS"],
        expected_columns=["CUSTOMER_NAME", "REVENUE"],
        expected_output_description="Ranked revenue table",
    )


def make_plan(step_count: int = 1) -> QueryPlan:
    steps = [make_step(index + 1) for index in range(step_count)]
    return QueryPlan(
        original_question="Which customers generated the most revenue?",
        reasoning="Revenue can be calculated from TPCH order and line item tables.",
        steps=steps,
        total_steps=len(steps),
    )


def make_state(**overrides) -> AgentState:
    values = {
        "question": "Which customers generated the most revenue?",
        "schema_context": "CUSTOMER, ORDERS, LINEITEM. Revenue = L_EXTENDEDPRICE * (1 - L_DISCOUNT).",
    }
    values.update(overrides)
    return AgentState(**values)


def make_validated_query(sql: str, limit: int = 50) -> ValidatedQuery:
    return ValidatedQuery(
        step_number=1,
        sql=sql,
        target_tables=["CUSTOMER"],
        explanation="Returns customer rows.",
        estimated_row_limit=limit,
    )


def make_rejected_arbitration() -> ArbitrationResult:
    return ArbitrationResult(
        step_number=1,
        final_approved=False,
        vote_summary={"openai": False, "gemini": True, "deepseek": False},
        avg_confidence=0.42,
        dissenting_critics=["gemini"],
        disagreement_analysis="Critics disagreed on whether revenue was calculated correctly.",
        merged_correction="Use LINEITEM revenue formula and sort by total revenue descending.",
        final_confidence=0.38,
        arbitration_reasoning="The SQL needs a corrected revenue calculation.",
    )


class TestPlannerNode:
    def test_planner_returns_query_plan_update_only(self, monkeypatch):
        query_plan = make_plan()
        fake_client = FakeClaudeClient(query_plan)
        monkeypatch.setattr(planner_module, "claude_client", fake_client)

        result = planner_module.planner(make_state())

        assert result == {"query_plan": query_plan}
        assert fake_client.calls[0]["system_prompt"] == planner_module.PLANNER_PROMPT
        assert fake_client.calls[0]["response_model"] is QueryPlan
        assert fake_client.calls[0]["model_string"] == "claude-sonnet-4-6"
        assert "Which customers generated the most revenue?" in fake_client.calls[0]["user_prompt"]
        assert "Revenue = L_EXTENDEDPRICE" in fake_client.calls[0]["user_prompt"]

    def test_planner_truncates_plan_to_three_steps(self, monkeypatch):
        fake_client = FakeClaudeClient(make_plan(step_count=4))
        monkeypatch.setattr(planner_module, "claude_client", fake_client)

        result = planner_module.planner(make_state())

        query_plan = result["query_plan"]
        assert query_plan.total_steps == 3
        assert len(query_plan.steps) == 3


class TestSQLGeneratorNode:
    def test_sql_generator_adds_missing_limit_and_increments_attempts(
        self, monkeypatch
    ):
        fake_client = FakeClaudeClient(make_validated_query("SELECT C_NAME FROM CUSTOMER"))
        monkeypatch.setattr(sql_generator_module, "claude_client", fake_client)
        state = make_state(query_plan=make_plan(), attempts=2)

        result = sql_generator_module.sql_generator(state)

        assert set(result) == {"validated_query", "attempts"}
        assert result["attempts"] == 3
        assert result["validated_query"].sql == "SELECT C_NAME FROM CUSTOMER LIMIT 50"
        assert result["validated_query"].estimated_row_limit == 50
        assert result["validated_query"].critic_feedback is None
        assert fake_client.calls[0]["system_prompt"] == sql_generator_module.SQL_GENERATOR_PROMPT
        assert fake_client.calls[0]["response_model"] is ValidatedQuery
        assert fake_client.calls[0]["model_string"] == "claude-sonnet-4-6"

    def test_sql_generator_caps_limit_above_100(self, monkeypatch):
        fake_client = FakeClaudeClient(
            make_validated_query("SELECT C_NAME FROM CUSTOMER LIMIT 500", limit=500)
        )
        monkeypatch.setattr(sql_generator_module, "claude_client", fake_client)

        result = sql_generator_module.sql_generator(
            make_state(query_plan=make_plan(), attempts=0)
        )

        assert result["validated_query"].sql == "SELECT C_NAME FROM CUSTOMER LIMIT 100"
        assert result["validated_query"].estimated_row_limit == 100

    def test_sql_generator_injects_rejected_arbitration_feedback(
        self, monkeypatch
    ):
        fake_client = FakeClaudeClient(
            make_validated_query("SELECT C_NAME FROM CUSTOMER LIMIT 10", limit=10)
        )
        monkeypatch.setattr(sql_generator_module, "claude_client", fake_client)
        arbitration = make_rejected_arbitration()

        result = sql_generator_module.sql_generator(
            make_state(query_plan=make_plan(), arbitration=arbitration)
        )

        assert arbitration.merged_correction in fake_client.calls[0]["user_prompt"]
        assert result["validated_query"].critic_feedback == arbitration.merged_correction

    def test_sql_generator_rejects_fully_qualified_table_names(
        self, monkeypatch
    ):
        fake_client = FakeClaudeClient(
            make_validated_query(
                "SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS LIMIT 50"
            )
        )
        monkeypatch.setattr(sql_generator_module, "claude_client", fake_client)

        with pytest.raises(SQLValidationError):
            sql_generator_module.sql_generator(make_state(query_plan=make_plan()))

    def test_sql_generator_requires_query_plan(self):
        with pytest.raises(ValueError, match="query_plan"):
            sql_generator_module.sql_generator(make_state())
