"""OpenAI critic node."""

import os

from quorum.llm import OpenAILLMClient
from quorum.nodes.critic_helpers import run_critic
from quorum.schemas.critique import CritiqueResult
from quorum.state import AgentState

OPENAI_CRITIC_MODEL = "gpt-5.5-2026-04-23"

openai_client = OpenAILLMClient(api_key=os.getenv("OPENAI_API_KEY", "missing-openai-api-key"))


def critic_openai(state: AgentState) -> dict[str, CritiqueResult]:
    """Run Critic A using OpenAI GPT-5.5."""
    critique = run_critic(
        state=state,
        critic_id="openai",
        client=openai_client,
        model_string=OPENAI_CRITIC_MODEL,
    )
    return {"critique_openai": critique}
