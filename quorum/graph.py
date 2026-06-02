"""LangGraph assembly and public Quorum agent interfaces."""

import asyncio
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

load_dotenv()

from quorum.nodes import (
    arbiter,
    critic_deepseek,
    critic_gemini,
    critic_openai,
    executor,
    planner,
    sql_generator,
    step_router,
    synthesizer,
)
from quorum.state import AgentState
from quorum.tools import get_schema_context

NodeFn = Callable[[AgentState], dict[str, Any]]


def build_compiled_graph(
    *,
    planner_node: NodeFn = planner,
    sql_generator_node: NodeFn = sql_generator,
    executor_node: NodeFn = executor,
    critic_openai_node: NodeFn = critic_openai,
    critic_gemini_node: NodeFn = critic_gemini,
    critic_deepseek_node: NodeFn = critic_deepseek,
    arbiter_node: NodeFn = arbiter,
    step_router_node: NodeFn = step_router,
    synthesizer_node: NodeFn = synthesizer,
):
    """Build and compile the Quorum LangGraph workflow."""

    def ensemble_critic_node(state: AgentState) -> dict[str, Any]:
        return asyncio.run(
            _run_critics_concurrently(
                state=state,
                critic_nodes=[
                    critic_openai_node,
                    critic_gemini_node,
                    critic_deepseek_node,
                ],
            )
        )

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("sql_generator", sql_generator_node)
    graph.add_node("executor", executor_node)
    graph.add_node("ensemble_critic", ensemble_critic_node)
    graph.add_node("arbiter", arbiter_node)
    graph.add_node("step_router", step_router_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "sql_generator")
    graph.add_edge("sql_generator", "executor")
    graph.add_edge("executor", "ensemble_critic")
    graph.add_edge("ensemble_critic", "arbiter")
    graph.add_conditional_edges(
        "arbiter",
        route_after_arbiter,
        {
            "retry": "sql_generator",
            "advance": "step_router",
            "synthesize": "synthesizer",
        },
    )
    graph.add_conditional_edges(
        "step_router",
        route_after_step_router,
        {
            "continue": "sql_generator",
            "synthesize": "synthesizer",
        },
    )
    graph.add_edge("synthesizer", END)

    return graph.compile()


async def _run_critics_concurrently(
    *,
    state: AgentState,
    critic_nodes: list[NodeFn],
) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=3) as executor_pool:
        loop = asyncio.get_running_loop()
        results = await asyncio.gather(
            *[
                loop.run_in_executor(executor_pool, critic_node, state)
                for critic_node in critic_nodes
            ]
        )

    merged: dict[str, Any] = {}
    for result in results:
        merged.update(result)
    return merged


def route_after_arbiter(state: AgentState) -> str:
    """Route after arbitration to retry, advance, or synthesize."""
    if state.arbitration is None:
        return "synthesize"

    if not state.arbitration.final_approved and state.attempts < state.max_attempts:
        return "retry"

    if state.attempts >= state.max_attempts and not all(
        state.arbitration.vote_summary.values()
    ):
        return "synthesize"

    return "advance"


def route_after_step_router(state: AgentState) -> str:
    """Route to the next step or final synthesis after a step is accepted."""
    if state.query_plan is None:
        return "synthesize"
    if state.current_step_index < state.query_plan.total_steps:
        return "continue"
    return "synthesize"


compiled_graph = build_compiled_graph()


def run_agent(question: str) -> AgentState:
    """Run Quorum to completion for a natural-language question."""
    initial_state = AgentState(question=question, schema_context=get_schema_context())
    result = compiled_graph.invoke(initial_state)
    return AgentState.model_validate(result)


def stream_agent(question: str) -> Iterator[dict[str, Any]]:
    """Stream Quorum graph updates for a natural-language question."""
    initial_state = AgentState(question=question, schema_context=get_schema_context())
    yield from compiled_graph.stream(initial_state)
