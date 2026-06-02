"""Focused tests for the deterministic Executor node."""

import importlib

from quorum.schemas.query import QueryResult, ValidatedQuery
from quorum.state import AgentState

executor_module = importlib.import_module("quorum.nodes.executor")


class FakeQueryClient:
    """Simple fake for executor-level database tests."""

    def __init__(self, result: QueryResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls = []

    def execute_query(self, *, sql: str, step_number: int) -> QueryResult:
        self.calls.append({"sql": sql, "step_number": step_number})
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("FakeQueryClient requires result or error")
        return self.result


def make_state(validated_query: ValidatedQuery | None = None) -> AgentState:
    return AgentState(
        question="Which customers generated the most revenue?",
        schema_context="TPCH schema context",
        validated_query=validated_query,
    )


def make_validated_query() -> ValidatedQuery:
    return ValidatedQuery(
        step_number=2,
        sql="SELECT C_NAME FROM CUSTOMER LIMIT 50",
        target_tables=["CUSTOMER"],
        explanation="Returns customer names.",
        estimated_row_limit=50,
    )


def make_query_result() -> QueryResult:
    return QueryResult(
        step_number=2,
        sql_executed="SELECT C_NAME FROM CUSTOMER LIMIT 50",
        columns=["C_NAME"],
        rows=[["Customer#000000001"]],
        row_count=1,
        execution_time_ms=12.5,
        success=True,
    )


def test_executor_returns_query_result_unchanged(monkeypatch):
    query_result = make_query_result()
    fake_client = FakeQueryClient(result=query_result)
    monkeypatch.setattr(executor_module, "query_client", fake_client)

    result = executor_module.executor(make_state(validated_query=make_validated_query()))

    assert result == {"query_result": query_result}
    assert result["query_result"] is query_result
    assert fake_client.calls == [
        {"sql": "SELECT C_NAME FROM CUSTOMER LIMIT 50", "step_number": 2}
    ]


def test_executor_converts_database_exception_to_failed_query_result(monkeypatch):
    fake_client = FakeQueryClient(error=RuntimeError("Database timeout"))
    monkeypatch.setattr(executor_module, "query_client", fake_client)

    result = executor_module.executor(make_state(validated_query=make_validated_query()))

    query_result = result["query_result"]
    assert query_result.step_number == 2
    assert query_result.sql_executed == "SELECT C_NAME FROM CUSTOMER LIMIT 50"
    assert query_result.success is False
    assert query_result.error_detail == "Database timeout"
    assert query_result.columns == []
    assert query_result.rows == []
    assert query_result.row_count == 0


def test_executor_returns_failed_query_result_when_validated_query_missing():
    result = executor_module.executor(make_state(validated_query=None))

    query_result = result["query_result"]
    assert query_result.success is False
    assert query_result.error_detail == "Executor requires state.validated_query."
    assert query_result.sql_executed == ""
    assert query_result.step_number == 0


def test_executor_module_does_not_import_llm_clients():
    module_names = set(executor_module.__dict__)

    assert "AnthropicLLMClient" not in module_names
    assert "OpenAILLMClient" not in module_names
    assert "GeminiLLMClient" not in module_names
    assert "claude_client" not in module_names
