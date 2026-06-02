"""Shared helpers for deterministic critic pre-checks and prompt construction."""

import asyncio
import json
from pathlib import Path
from typing import Literal, Protocol

from quorum.schemas.critique import CritiqueResult
from quorum.state import AgentState

CriticId = Literal["openai", "gemini", "deepseek"]
TRUNCATION_WARNING = "Result may be truncated at LIMIT"

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "critic.txt"
CRITIC_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


class CriticClient(Protocol):
    """Protocol for the shared async LLM client interface used by critics."""

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[CritiqueResult],
        model_string: str,
    ) -> CritiqueResult:
        """Call an LLM and return a validated critique."""


def run_critic(
    *,
    state: AgentState,
    critic_id: CriticId,
    client: CriticClient,
    model_string: str,
    enable_thinking: bool = False,
) -> CritiqueResult:
    """Run deterministic pre-checks, then call the critic model if needed."""
    precheck = precheck_query_result(state, critic_id)
    if precheck is not None:
        return precheck

    user_prompt = build_critic_user_prompt(
        state=state,
        critic_id=critic_id,
        warnings=get_deterministic_warnings(state),
    )
    call_kwargs = {
        "system_prompt": CRITIC_PROMPT,
        "user_prompt": user_prompt,
        "response_model": CritiqueResult,
        "model_string": model_string,
    }
    if enable_thinking:
        call_kwargs["enable_thinking"] = True

    critique = asyncio.run(client.call_llm(**call_kwargs))
    return _with_critic_identity(
        critique=critique,
        critic_id=critic_id,
        step_number=_step_number(state),
    )


def precheck_query_result(
    state: AgentState,
    critic_id: CriticId,
) -> CritiqueResult | None:
    """Return an automatic rejection critique when deterministic checks fail."""
    query_result = state.query_result
    if query_result is None:
        return _auto_rejection(
            critic_id=critic_id,
            step_number=_step_number(state),
            issue="Query result is missing",
            reasoning="The critic cannot evaluate a missing query result.",
        )

    if not query_result.success:
        return _auto_rejection(
            critic_id=critic_id,
            step_number=query_result.step_number,
            issue=query_result.error_detail or "SQL execution failed",
            reasoning="The SQL execution failed before semantic review.",
        )

    if query_result.row_count == 0:
        return _auto_rejection(
            critic_id=critic_id,
            step_number=query_result.step_number,
            issue="Query returned no rows",
            reasoning="A result with zero rows cannot support the requested analysis.",
        )

    all_null_columns = _all_null_columns(query_result.columns, query_result.rows)
    if all_null_columns:
        issues = [f"Column {column} all NULL" for column in all_null_columns]
        return CritiqueResult(
            critic_id=critic_id,
            step_number=query_result.step_number,
            approved=False,
            confidence_score=0.0,
            issues_found=issues,
            suggested_correction="Revise the SQL so returned columns contain meaningful non-null values.",
            reasoning="One or more result columns contain only NULL values.",
        )

    return None


def get_deterministic_warnings(state: AgentState) -> list[str]:
    """Return deterministic warnings that should be included in the critic prompt."""
    if state.query_result is not None and state.query_result.row_count >= 95:
        return [TRUNCATION_WARNING]
    return []


def build_critic_user_prompt(
    *,
    state: AgentState,
    critic_id: CriticId,
    warnings: list[str],
) -> str:
    """Build dynamic critic context for the LLM prompt."""
    query_result = state.query_result
    if query_result is None:
        raise ValueError("Cannot build critic prompt without query_result")

    return f"""Critic id:
{critic_id}

Step objective:
{_step_objective(state)}

SQL executed:
{query_result.sql_executed}

Column names:
{json.dumps(query_result.columns)}

Row count:
{query_result.row_count}

First 10 result rows:
{json.dumps(query_result.rows[:10], default=str)}

Deterministic warnings:
{json.dumps(warnings)}
"""


def _auto_rejection(
    *,
    critic_id: CriticId,
    step_number: int,
    issue: str,
    reasoning: str,
) -> CritiqueResult:
    return CritiqueResult(
        critic_id=critic_id,
        step_number=step_number,
        approved=False,
        confidence_score=0.0,
        issues_found=[issue],
        suggested_correction="Fix the SQL query and rerun it before semantic review.",
        reasoning=reasoning,
    )


def _all_null_columns(columns: list[str], rows: list[list[object]]) -> list[str]:
    all_null_columns = []
    for index, column in enumerate(columns):
        if rows and all(index >= len(row) or row[index] is None for row in rows):
            all_null_columns.append(column)
    return all_null_columns


def _with_critic_identity(
    *,
    critique: CritiqueResult,
    critic_id: CriticId,
    step_number: int,
) -> CritiqueResult:
    return CritiqueResult(
        **{
            **critique.model_dump(),
            "critic_id": critic_id,
            "step_number": step_number,
        }
    )


def _step_number(state: AgentState) -> int:
    if state.query_result is not None:
        return state.query_result.step_number
    if state.validated_query is not None:
        return state.validated_query.step_number
    return state.current_step_index + 1


def _step_objective(state: AgentState) -> str:
    if state.query_plan is None:
        return "No query plan available."
    try:
        return state.query_plan.steps[state.current_step_index].objective
    except IndexError:
        return "Current step index is outside the query plan."
