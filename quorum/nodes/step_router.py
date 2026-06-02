"""Step router node for advancing approved plan steps."""

from typing import Any

from quorum.state import AgentState


def step_router(state: AgentState) -> dict[str, Any]:
    """Append the approved result, advance the step index, and reset step fields."""
    all_results = list(state.all_results)
    if state.query_result is not None:
        all_results.append(state.query_result)

    arbitration_history = list(state.arbitration_history)
    if state.arbitration is not None:
        arbitration_history.append(state.arbitration)

    return {
        "all_results": all_results,
        "arbitration_history": arbitration_history,
        "current_step_index": state.current_step_index + 1,
        "critique_openai": None,
        "critique_gemini": None,
        "critique_deepseek": None,
        "arbitration": None,
        "validated_query": None,
        "query_result": None,
        "attempts": 0,
    }
