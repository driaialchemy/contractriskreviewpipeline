"""LangGraph workflow tests with mocked node behavior."""

from dataclasses import dataclass, field

from quorum.graph import build_compiled_graph, run_agent, stream_agent
from quorum.schemas.critique import ArbitrationResult, CritiqueResult
from quorum.schemas.plan import QueryPlan, QueryStep
from quorum.schemas.query import QueryResult, ValidatedQuery
from quorum.schemas.report import InsightReport
from quorum.state import AgentState


@dataclass
class GraphScenario:
    plan_steps: int = 1
    reject_until_attempt: int = 0
    all_reject: bool = False
    two_one_split: bool = False
    sql_calls: list[int] = field(default_factory=list)


def make_plan(step_count: int) -> QueryPlan:
    steps = [
        QueryStep(
            step_number=index + 1,
            objective=f"Retrieve approved result for step {index + 1}",
            tables_required=["CUSTOMER"],
            expected_columns=["C_NAME"],
            expected_output_description="Customer rows",
        )
        for index in range(step_count)
    ]
    return QueryPlan(
        original_question="Which customers generated the most revenue?",
        reasoning="Mock graph plan.",
        steps=steps,
        total_steps=len(steps),
    )


def make_critique(
    critic_id: str,
    *,
    step_number: int,
    approved: bool,
    confidence_score: float = 0.85,
) -> CritiqueResult:
    return CritiqueResult(
        critic_id=critic_id,
        step_number=step_number,
        approved=approved,
        confidence_score=confidence_score if approved else 0.2,
        issues_found=[] if approved else [f"{critic_id} rejected the result"],
        suggested_correction=None if approved else "Retry with corrected SQL.",
        reasoning=f"{critic_id} mocked critique.",
    )


def make_graph_for_scenario(scenario: GraphScenario):
    def planner_node(state: AgentState):
        return {"query_plan": make_plan(scenario.plan_steps)}

    def sql_generator_node(state: AgentState):
        step_number = state.current_step_index + 1
        scenario.sql_calls.append(step_number)
        return {
            "validated_query": ValidatedQuery(
                step_number=step_number,
                sql=f"SELECT C_NAME FROM CUSTOMER LIMIT 50 /* step {step_number} */",
                target_tables=["CUSTOMER"],
                explanation=f"Mock SQL for step {step_number}.",
                estimated_row_limit=50,
            ),
            "attempts": state.attempts + 1,
        }

    def executor_node(state: AgentState):
        return {
            "query_result": QueryResult(
                step_number=state.validated_query.step_number,
                sql_executed=state.validated_query.sql,
                columns=["C_NAME"],
                rows=[[f"Customer step {state.validated_query.step_number}"]],
                row_count=1,
                execution_time_ms=1.0,
                success=True,
            )
        }

    def critic_node(critic_id: str):
        def node(state: AgentState):
            approved = True
            if scenario.all_reject:
                approved = False
            elif state.attempts <= scenario.reject_until_attempt:
                approved = False
            elif scenario.two_one_split and critic_id == "gemini":
                approved = False
            return {
                f"critique_{critic_id}": make_critique(
                    critic_id=critic_id,
                    step_number=state.query_result.step_number,
                    approved=approved,
                )
            }

        return node

    def arbiter_node(state: AgentState):
        critiques = [
            state.critique_openai,
            state.critique_gemini,
            state.critique_deepseek,
        ]
        vote_summary = {
            critique.critic_id: critique.approved for critique in critiques
        }
        avg_confidence = sum(critique.confidence_score for critique in critiques) / 3
        final_approved = all(vote_summary.values()) or scenario.two_one_split
        if (
            any(not approved for approved in vote_summary.values())
            and state.attempts < state.max_attempts
            and not scenario.two_one_split
        ):
            final_approved = False
        if state.attempts >= state.max_attempts:
            final_approved = True
        return {
            "arbitration": ArbitrationResult(
                step_number=state.query_result.step_number,
                final_approved=final_approved,
                vote_summary=vote_summary,
                avg_confidence=avg_confidence,
                dissenting_critics=[
                    critic_id
                    for critic_id, approved in vote_summary.items()
                    if not approved
                ],
                disagreement_analysis="Mock arbitration.",
                merged_correction=None if final_approved else "Retry the SQL.",
                final_confidence=avg_confidence,
                arbitration_reasoning="Mock arbitration reasoning.",
            )
        }

    def synthesizer_node(state: AgentState):
        status = "complete" if state.all_results else "failed"
        return {
            "insight_report": InsightReport(
                original_question=state.question,
                executive_summary=f"Mock {status} report.",
                key_findings=[] if not state.all_results else ["Mock finding."],
                data_tables=state.all_results,
                caveats=["Mock caveat."],
                ensemble_summary=state.arbitration_history
                + ([state.arbitration] if state.arbitration is not None else []),
                total_attempts=max(state.attempts, len(state.all_results)),
                steps_executed=len(state.all_results),
                models_used=["mock-model"],
            ),
            "status": status,
        }

    return build_compiled_graph(
        planner_node=planner_node,
        sql_generator_node=sql_generator_node,
        executor_node=executor_node,
        critic_openai_node=critic_node("openai"),
        critic_gemini_node=critic_node("gemini"),
        critic_deepseek_node=critic_node("deepseek"),
        arbiter_node=arbiter_node,
        synthesizer_node=synthesizer_node,
    )


def invoke_scenario(scenario: GraphScenario, *, max_attempts: int = 3) -> AgentState:
    graph = make_graph_for_scenario(scenario)
    result = graph.invoke(
        AgentState(
            question="Which customers generated the most revenue?",
            schema_context="Mock schema context",
            max_attempts=max_attempts,
        )
    )
    return AgentState.model_validate(result)


def test_graph_happy_path():
    state = invoke_scenario(GraphScenario())

    assert state.status == "complete"
    assert state.current_step_index == 1
    assert len(state.all_results) == 1
    assert len(state.arbitration_history) == 1
    assert state.insight_report.steps_executed == 1


def test_graph_retry_path():
    scenario = GraphScenario(reject_until_attempt=1)

    state = invoke_scenario(scenario)

    assert state.status == "complete"
    assert scenario.sql_calls == [1, 1]
    assert len(state.all_results) == 1
    assert state.insight_report.steps_executed == 1


def test_graph_max_retries_routes_to_empty_result_synthesis():
    state = invoke_scenario(GraphScenario(all_reject=True), max_attempts=2)

    assert state.status == "failed"
    assert len(state.all_results) == 0
    assert state.insight_report.data_tables == []
    assert state.insight_report.steps_executed == 0


def test_graph_multi_step_success():
    scenario = GraphScenario(plan_steps=2)

    state = invoke_scenario(scenario)

    assert state.status == "complete"
    assert scenario.sql_calls == [1, 2]
    assert state.current_step_index == 2
    assert len(state.all_results) == 2
    assert state.insight_report.steps_executed == 2


def test_graph_two_one_critic_split_can_be_approved_by_arbiter():
    state = invoke_scenario(GraphScenario(two_one_split=True))

    assert state.status == "complete"
    assert len(state.all_results) == 1
    assert state.arbitration_history[0].vote_summary == {
        "openai": True,
        "gemini": False,
        "deepseek": True,
    }


def test_graph_all_critics_reject_until_max_retries():
    scenario = GraphScenario(all_reject=True)

    state = invoke_scenario(scenario, max_attempts=1)

    assert state.status == "failed"
    assert scenario.sql_calls == [1]
    assert len(state.all_results) == 0
    assert state.arbitration.vote_summary == {
        "openai": False,
        "gemini": False,
        "deepseek": False,
    }


def test_graph_empty_approved_results_are_handled_deterministically():
    state = invoke_scenario(GraphScenario(all_reject=True), max_attempts=1)

    assert state.insight_report is not None
    assert state.insight_report.data_tables == []
    assert state.insight_report.key_findings == []
    assert state.status == "failed"


def test_public_graph_interfaces_use_compiled_graph(monkeypatch):
    class FakeCompiledGraph:
        def __init__(self):
            self.invoke_calls = []
            self.stream_calls = []

        def invoke(self, state):
            self.invoke_calls.append(state)
            return {
                **state.model_dump(),
                "status": "complete",
            }

        def stream(self, state):
            self.stream_calls.append(state)
            yield {"planner": {"query_plan": "mock"}}

    fake_graph = FakeCompiledGraph()

    import quorum.graph as graph_module

    monkeypatch.setattr(graph_module, "compiled_graph", fake_graph)
    monkeypatch.setattr(graph_module, "get_schema_context", lambda: "mock schema")

    result = run_agent("Question?")
    events = list(stream_agent("Question?"))

    assert result.status == "complete"
    assert fake_graph.invoke_calls[0].schema_context == "mock schema"
    assert events == [{"planner": {"query_plan": "mock"}}]
    assert fake_graph.stream_calls[0].question == "Question?"
