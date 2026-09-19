import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from src.orchestrator.state import AgentState, StepExecutionTrace


class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        ...

    def start_trace_timing(self) -> Tuple[datetime, float]:
        return datetime.now(timezone.utc), time.perf_counter()

    def log_trace(
        self,
        state: AgentState,
        input_received: Dict[str, Any],
        rationale: str,
        output: Dict[str, Any],
        *,
        step_name: str,
        sequence_number: int,
        started_at: datetime,
        start_perf: float,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        completed_at = datetime.now(timezone.utc)
        duration_ms = max(0.0, (time.perf_counter() - start_perf) * 1000.0)
        trace = StepExecutionTrace(
            agent_name=self.name,
            step_name=step_name,
            sequence_number=sequence_number,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round(duration_ms, 3),
            timestamp=completed_at,
            error_message=error_message,
            input_received=input_received,
            agent_rationale=rationale,
            output_generated=output,
        )
        state.execution_traces.append(trace)
