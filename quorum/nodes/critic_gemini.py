"""Gemini critic node."""

import os

from quorum.llm import GeminiLLMClient
from quorum.nodes.critic_helpers import run_critic
from quorum.schemas.critique import CritiqueResult
from quorum.state import AgentState

GEMINI_CRITIC_MODEL = "gemini-3.1-pro-preview"

gemini_client = GeminiLLMClient(api_key=os.getenv("GOOGLE_API_KEY", "missing-google-api-key"))


def critic_gemini(state: AgentState) -> dict[str, CritiqueResult]:
    """Run Critic B using Gemini 3.1 Pro Preview."""
    critique = run_critic(
        state=state,
        critic_id="gemini",
        client=gemini_client,
        model_string=GEMINI_CRITIC_MODEL,
    )
    return {"critique_gemini": critique}
