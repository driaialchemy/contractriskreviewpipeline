from datetime import datetime, timezone
from typing import Dict, List

from src.orchestrator.state import StepExecutionTrace


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_trace_clock_time(dt: datetime) -> str:
    """Format trace time as HH:MM:SS.mmm in UTC (string for Streamlit display)."""
    utc_dt = _to_utc(dt)
    milliseconds = utc_dt.microsecond // 1000
    return utc_dt.strftime("%H:%M:%S.") + f"{milliseconds:03d}"


def format_trace_iso_milliseconds(dt: datetime) -> str:
    return _to_utc(dt).isoformat(timespec="milliseconds")


def build_pipeline_inspector_rows(traces: List[StepExecutionTrace]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for trace in traces:
        rows.append(
            {
                "Seq": str(trace.sequence_number),
                "Agent": trace.agent_name,
                "Step": trace.step_name,
                "Status": trace.status,
                "Started (UTC)": format_trace_clock_time(trace.started_at),
                "Completed (UTC)": format_trace_clock_time(trace.completed_at),
                "Duration (ms)": f"{trace.duration_ms:.3f}",
            }
        )
    return rows


def format_trace_summary_line(trace: StepExecutionTrace) -> str:
    started = format_trace_clock_time(trace.started_at)
    completed = format_trace_clock_time(trace.completed_at)
    return (
        f"{trace.agent_name} — started {started}, completed {completed}, "
        f"{trace.duration_ms:.3f} ms"
    )
