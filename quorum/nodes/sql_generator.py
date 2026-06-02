"""SQL generator node for producing validated analytical SQL."""

import asyncio
import os
import re
from pathlib import Path

from quorum.llm import AnthropicLLMClient
from quorum.schemas.query import ValidatedQuery
from quorum.state import AgentState
from quorum.tools import validate_and_fix_sql

CLAUDE_SONNET_MODEL = "claude-sonnet-4-6"

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "sql_generator.txt"
SQL_GENERATOR_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

claude_client = AnthropicLLMClient(
    api_key=os.getenv("ANTHROPIC_API_KEY", "missing-anthropic-api-key")
)


def sql_generator(state: AgentState) -> dict[str, ValidatedQuery | int]:
    """Generate SQL for the current plan step and enforce deterministic SQL rules."""
    if state.query_plan is None:
        raise ValueError("SQL generator requires state.query_plan")

    try:
        current_step = state.query_plan.steps[state.current_step_index]
    except IndexError as exc:
        raise ValueError("current_step_index is outside query_plan.steps") from exc

    critic_feedback = None
    if state.arbitration is not None and not state.arbitration.final_approved:
        critic_feedback = state.arbitration.merged_correction

    user_prompt = f"""TPCH_SF1 schema context:
{state.schema_context}

Current QueryStep:
{current_step.model_dump_json()}

Critic feedback:
{critic_feedback or "None"}
"""

    validated_query = asyncio.run(
        claude_client.call_llm(
            system_prompt=SQL_GENERATOR_PROMPT,
            user_prompt=user_prompt,
            response_model=ValidatedQuery,
            model_string=CLAUDE_SONNET_MODEL,
        )
    )

    fixed_sql = validate_and_fix_sql(validated_query.sql)
    validated_query = ValidatedQuery(
        **{
            **validated_query.model_dump(),
            "sql": fixed_sql,
            "estimated_row_limit": _extract_limit(fixed_sql),
            "critic_feedback": critic_feedback,
        }
    )

    return {
        "validated_query": validated_query,
        "attempts": state.attempts + 1,
    }


def _extract_limit(sql: str) -> int:
    """Extract the final LIMIT value from validator-corrected SQL."""
    match = re.search(r"\bLIMIT\s+(\d+)\s*$", sql, re.IGNORECASE)
    if match is None:
        raise ValueError("validated SQL is missing a final LIMIT clause")
    return int(match.group(1))
