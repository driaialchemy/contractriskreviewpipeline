"""Executor node for deterministic SQL query execution."""

from quorum.schemas.query import QueryResult
from quorum.state import AgentState
from quorum.tools import get_query_client

query_client = get_query_client()


def executor(state: AgentState) -> dict[str, QueryResult]:
    """Execute the validated SQL and return only the query result update."""
    if state.validated_query is None:
        return {
            "query_result": QueryResult(
                step_number=0,
                sql_executed="",
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=0.0,
                success=False,
                error_detail="Executor requires state.validated_query.",
            )
        }

    try:
        query_result = query_client.execute_query(
            sql=state.validated_query.sql,
            step_number=state.validated_query.step_number,
        )
    except Exception as exc:
        query_result = QueryResult(
            step_number=state.validated_query.step_number,
            sql_executed=state.validated_query.sql,
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            success=False,
            error_detail=str(exc),
        )

    return {"query_result": query_result}
