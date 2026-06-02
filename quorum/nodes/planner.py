"""Planner node for generating a typed query plan."""

import asyncio
import os
from pathlib import Path

from quorum.llm import AnthropicLLMClient
from quorum.schemas.plan import QueryPlan
from quorum.state import AgentState

CLAUDE_SONNET_MODEL = "claude-sonnet-4-6"
MAX_PLAN_STEPS = 3

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "planner.txt"
PLANNER_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

claude_client = AnthropicLLMClient(
    api_key=os.getenv("ANTHROPIC_API_KEY", "missing-anthropic-api-key")
)


def planner(state: AgentState) -> dict[str, QueryPlan]:
    """Generate a query plan for the user's question."""
    user_prompt = f"""User question:
{state.question}

TPCH_SF1 schema context:
{state.schema_context}
"""

    query_plan = asyncio.run(
        claude_client.call_llm(
            system_prompt=PLANNER_PROMPT,
            user_prompt=user_prompt,
            response_model=QueryPlan,
            model_string=CLAUDE_SONNET_MODEL,
        )
    )

    if len(query_plan.steps) > MAX_PLAN_STEPS:
        query_plan = QueryPlan(
            original_question=query_plan.original_question,
            reasoning=query_plan.reasoning,
            steps=query_plan.steps[:MAX_PLAN_STEPS],
            total_steps=MAX_PLAN_STEPS,
        )

    return {"query_plan": query_plan}
