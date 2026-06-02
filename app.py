"""Streamlit UI for the Quorum agentic data analyst."""

from __future__ import annotations

from typing import Any

import streamlit as st

from quorum.graph import stream_agent
from quorum.schemas.critique import ArbitrationResult, CritiqueResult
from quorum.schemas.query import QueryResult, ValidatedQuery
from quorum.schemas.report import InsightReport


def main() -> None:
    st.set_page_config(page_title="Quorum", page_icon="Q", layout="wide")
    st.title("Quorum")
    st.caption("Natural language to local DuckDB or Snowflake SQL to critiqued business insight.")

    question = st.text_area(
        "Business question",
        placeholder="Which customers generated the most revenue last year?",
        height=90,
    )

    run_clicked = st.button("Run analysis", type="primary", disabled=not question.strip())

    progress_container = st.container()
    report_container = st.container()

    if run_clicked:
        try:
            final_state = _run_stream(question.strip(), progress_container)
            _render_final_state(final_state, report_container)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            st.error(f"Quorum could not complete the analysis: {exc}")


def _run_stream(question: str, container) -> dict[str, Any]:
    final_state: dict[str, Any] = {}
    with container:
        with st.status("Running Quorum workflow...", expanded=True) as status:
            for event in stream_agent(question):
                for node_name, update in event.items():
                    st.write(f"Completed `{node_name}`")
                    if isinstance(update, dict):
                        final_state.update(update)
                        _render_update(update)
            status.update(label="Workflow complete", state="complete")
    return final_state


def _render_update(update: dict[str, Any]) -> None:
    validated_query = update.get("validated_query")
    if isinstance(validated_query, ValidatedQuery):
        st.code(validated_query.sql, language="sql")

    query_result = update.get("query_result")
    if isinstance(query_result, QueryResult):
        if query_result.success:
            st.write(f"Rows returned: {query_result.row_count}")
        else:
            st.warning(query_result.error_detail or "Query execution failed.")

    for field_name in ("critique_openai", "critique_gemini", "critique_deepseek"):
        critique = update.get(field_name)
        if isinstance(critique, CritiqueResult):
            vote = "Approved" if critique.approved else "Rejected"
            st.write(f"{critique.critic_id}: {vote} ({critique.confidence_score:.2f})")

    arbitration = update.get("arbitration")
    if isinstance(arbitration, ArbitrationResult):
        vote = "Approved" if arbitration.final_approved else "Retry requested"
        st.write(f"Arbiter: {vote} ({arbitration.final_confidence:.2f})")


def _render_final_state(final_state: dict[str, Any], container) -> None:
    report = final_state.get("insight_report")
    if not isinstance(report, InsightReport):
        return

    with container:
        st.subheader("Insight Report")
        st.write(report.executive_summary)

        if report.key_findings:
            st.markdown("**Key Findings**")
            for finding in report.key_findings:
                st.write(f"- {finding}")

        if report.data_tables:
            st.markdown("**Approved Data Tables**")
            for result in report.data_tables:
                st.code(result.sql_executed, language="sql")
                st.dataframe(_rows_as_dicts(result), use_container_width=True)

        if report.ensemble_summary:
            st.markdown("**Ensemble Decisions**")
            for arbitration in report.ensemble_summary:
                st.write(
                    {
                        "step": arbitration.step_number,
                        "approved": arbitration.final_approved,
                        "avg_confidence": arbitration.avg_confidence,
                        "final_confidence": arbitration.final_confidence,
                    }
                )

        if report.caveats:
            st.markdown("**Caveats**")
            for caveat in report.caveats:
                st.write(f"- {caveat}")

        st.download_button(
            "Download report JSON",
            data=report_to_json(report),
            file_name="quorum_insight_report.json",
            mime="application/json",
        )


def _rows_as_dicts(result: QueryResult) -> list[dict[str, Any]]:
    return [
        {column: row[index] if index < len(row) else None for index, column in enumerate(result.columns)}
        for row in result.rows
    ]


def report_to_json(report: InsightReport) -> str:
    """Serialize an InsightReport for download."""
    return report.model_dump_json(indent=2)


if __name__ == "__main__":
    main()
