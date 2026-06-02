"""DeepSeek critic node through the Anthropic-compatible API."""

import os

from quorum.llm import AnthropicLLMClient
from quorum.nodes.critic_helpers import run_critic
from quorum.schemas.critique import CritiqueResult
from quorum.state import AgentState

DEEPSEEK_CRITIC_MODEL = "deepseek-v4-pro"

deepseek_client = AnthropicLLMClient(
    api_key=os.getenv("DEEPSEEK_API_KEY", "missing-deepseek-api-key"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic"),
)


def critic_deepseek(state: AgentState) -> dict[str, CritiqueResult]:
    """Run Critic C using DeepSeek V4 Pro with thinking enabled."""
    critique = run_critic(
        state=state,
        critic_id="deepseek",
        client=deepseek_client,
        model_string=DEEPSEEK_CRITIC_MODEL,
        enable_thinking=True,
    )
    return {"critique_deepseek": critique}
