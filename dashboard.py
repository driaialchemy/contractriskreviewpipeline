import asyncio
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from governance.dashboard_view import (
    AUDIENCE_OPTIONS,
    Audience,
    GOVERNANCE_DATASET_INDEPENDENCE_NOTE,
    GovernanceCheckResult,
    get_architecture_explanation,
    get_remediation_lines,
    get_status_display_label,
    get_what_governance_checks,
    json_path_for_markdown_report,
    list_governance_report_markdown_files,
    load_latest_governance_report,
    resolve_governance_display_state,
    run_governance_check_sync,
    summarize_governance_for_audience,
)
from governance.models import GovernanceReport
from report_builder import SessionAuditReport
from src.agents.extraction import ExtractionAgent
from src.agents.risk import RiskAgent
from src.agents.summary import SummaryAgent
from src.config import (
    CUAD_JSON_NAME,
    get_dataset_configuration_help,
    get_dataset_zip_path,
    get_logs_dir,
    get_project_root,
    is_dataset_configured,
)
from src.dashboard.trace_display import build_pipeline_inspector_rows, format_trace_summary_line
from src.orchestrator.engine import run_pipeline
from src.orchestrator.state import AgentState

PROJECT_ROOT = get_project_root()
PLAYBOOK_PATH = PROJECT_ROOT / "data" / "playbook.json"
LOGS_DIR = get_logs_dir()

PIPELINE_MODES = [
    "Full Pipeline (All 3 Agents)",
    "Extraction Only",
    "Extraction + Risk Assessment",
]

SEVERITY_COLORS = {
    "critical": "#FF4B4B",
    "high": "#FFA500",
    "medium": "#FFD700",
    "low": "#28A745",
    "none": "#28A745",
    "unknown": "#808080",
}


def _init_session_state() -> None:
    defaults: Dict[str, Any] = {
        "session_log": [],
        "last_result": None,
        "contract_list": [],
        "contracts_loaded": False,
        "running": False,
        "governance_last_result": None,
        "governance_report_audience": "Executive",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_contract_titles() -> List[str]:
    with zipfile.ZipFile(get_dataset_zip_path(), "r") as archive:
        raw_json = archive.read(CUAD_JSON_NAME)
    dataset: Dict[str, Any] = json.loads(raw_json)
    titles: List[str] = []
    for contract in dataset.get("data", []):
        title = contract.get("title")
        if title:
            titles.append(str(title))
    return titles


def _state_to_log_entry(state: AgentState, pipeline_mode: str) -> Dict[str, Any]:
    return {
        "session_id": state.session_id,
        "contract_title": state.contract_title,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_mode": pipeline_mode,
        "current_step": state.current_step,
        "final_report": state.shared_data.get("final_report", {}),
        "risk_summary": state.shared_data.get("risk_summary", {}),
        "errors": list(state.errors),
        "execution_traces": [trace.model_dump() for trace in state.execution_traces],
    }


async def _run_extraction_only(state: AgentState) -> AgentState:
    agent = ExtractionAgent()
    return await agent.process(state)


async def _run_extraction_and_risk(state: AgentState) -> AgentState:
    state = await ExtractionAgent().process(state)
    if state.errors:
        return state
    return await RiskAgent().process(state)


async def _run_pipeline_by_mode(state: AgentState, pipeline_mode: str) -> AgentState:
    if pipeline_mode == "Full Pipeline (All 3 Agents)":
        return await run_pipeline(state)
    if pipeline_mode == "Extraction Only":
        return await _run_extraction_only(state)
    if pipeline_mode == "Extraction + Risk Assessment":
        return await _run_extraction_and_risk(state)
    raise ValueError(f"Unknown pipeline mode: {pipeline_mode}")


def _run_pipeline_sync(state: AgentState, pipeline_mode: str) -> AgentState:
    return asyncio.run(_run_pipeline_by_mode(state, pipeline_mode))


def _severity_color(severity: str) -> str:
    return SEVERITY_COLORS.get(severity.lower(), SEVERITY_COLORS["unknown"])


def _truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _action_severity(action: str, final_report: Dict[str, Any]) -> str:
    clause_by_clause = final_report.get("clause_by_clause", [])
    for clause in clause_by_clause:
        clause_type = clause.get("clause_type", "")
        if clause_type and clause_type in action:
            return str(clause.get("severity", "none")).lower()
    if "critical" in action.lower():
        return "critical"
    if "high" in action.lower():
        return "high"
    return "medium"


def _render_contract_review(final_report: Dict[str, Any], state: AgentState) -> None:
    overall_severity = final_report.get("overall_risk_severity", "unknown")
    clauses_found = final_report.get("clauses_found", 0)
    total_risk_flags = final_report.get("total_risk_flags", 0)
    contract_title = final_report.get("contract_title", state.contract_title)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Contract Name", _truncate_text(contract_title, 40))
    metric_cols[1].markdown(
        f"**Overall Risk Severity**  \n"
        f"<span style='color:{_severity_color(overall_severity)};"
        f"font-weight:bold;font-size:1.4rem;'>{overall_severity.upper()}</span>",
        unsafe_allow_html=True,
    )
    metric_cols[2].metric("Clauses Found", clauses_found)
    metric_cols[3].metric("Total Risk Flags", total_risk_flags)

    st.subheader("Executive Summary")
    executive_summary = final_report.get(
        "executive_summary",
        "Executive summary available after full pipeline completion.",
    )
    st.info(executive_summary)

    st.subheader("Top Priority Actions")
    top_actions = final_report.get("top_priority_actions", [])
    if top_actions:
        for action in top_actions:
            severity = _action_severity(action, final_report)
            if severity == "critical":
                st.error(action)
            elif severity == "high":
                st.warning(action)
            else:
                st.info(action)
    else:
        st.info("No priority actions recorded for this run.")

    st.subheader("Clause-by-Clause Breakdown")
    clause_rows: List[Dict[str, str]] = []
    for clause in final_report.get("clause_by_clause", []):
        clause_rows.append(
            {
                "Clause": clause.get("clause_type", ""),
                "Status": clause.get("status", ""),
                "Severity": clause.get("severity", ""),
                "Extracted Text": _truncate_text(clause.get("extracted_text", ""), 80),
                "Recommendation": clause.get("recommendation", ""),
            }
        )
    if clause_rows:
        st.dataframe(clause_rows, use_container_width=True)
    else:
        st.info("Clause breakdown available after full pipeline completion.")

    with st.expander("View Agent Execution Traces", expanded=False):
        if state.execution_traces:
            for trace in state.execution_traces:
                st.markdown(f"**{format_trace_summary_line(trace)}**")
                st.caption(trace.agent_rationale)
                st.json(trace.output_generated)
        else:
            st.caption("No execution traces recorded.")


def _build_session_log_dataframe(session_log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entry in session_log:
        risk_summary = entry.get("risk_summary", {})
        final_report = entry.get("final_report", {})
        rows.append(
            {
                "Contract Name": entry.get("contract_title", ""),
                "Risk Severity": final_report.get("overall_risk_severity")
                or risk_summary.get("overall_severity", "unknown"),
                "Critical": risk_summary.get("critical_count", 0),
                "High": risk_summary.get("high_count", 0),
                "Medium": risk_summary.get("medium_count", 0),
                "Timestamp": entry.get("timestamp", ""),
            }
        )
    return rows


def _render_sidebar() -> None:
    st.sidebar.title("CUAD Contract Review Pipeline")
    st.sidebar.caption("Multi-Agent Legal Risk Auditor")

    st.sidebar.subheader("Dataset Controls")
    dataset_ready = is_dataset_configured()
    if not dataset_ready:
        st.sidebar.warning(get_dataset_configuration_help())

    load_disabled = not dataset_ready
    if st.sidebar.button(
        "Load Contract List",
        use_container_width=True,
        disabled=load_disabled,
        help="Requires CUAD_DATASET_ZIP to be set to a valid data.zip path.",
    ):
        try:
            titles = _load_contract_titles()
            st.session_state["contract_list"] = titles
            st.session_state["contracts_loaded"] = True
            st.sidebar.success(f"Loaded {len(titles)} contracts from CUAD dataset.")
        except ValueError as exc:
            st.sidebar.warning(str(exc))
        except Exception as exc:
            st.sidebar.error(f"Failed to load contracts: {exc}")

    if st.session_state["contracts_loaded"]:
        st.sidebar.subheader("Contract Selection")
        st.sidebar.selectbox(
            "Select Contract",
            options=st.session_state["contract_list"],
            key="selected_contract",
        )
        st.sidebar.selectbox(
            "Pipeline Mode",
            options=PIPELINE_MODES,
            key="pipeline_mode",
        )
        if st.sidebar.button("Run Pipeline", use_container_width=True):
            if not dataset_ready:
                st.sidebar.warning(get_dataset_configuration_help())
            selected_contract = st.session_state.get("selected_contract")
            pipeline_mode = st.session_state.get("pipeline_mode", PIPELINE_MODES[0])
            if not selected_contract:
                st.sidebar.error("Select a contract before running the pipeline.")
            else:
                st.session_state["running"] = True
                session_id = str(uuid.uuid4())
                state = AgentState(
                    session_id=session_id,
                    contract_title=selected_contract,
                    current_step="extraction",
                )
                with st.spinner("Running agents..."):
                    try:
                        completed_state = _run_pipeline_sync(state, pipeline_mode)
                        log_entry = _state_to_log_entry(completed_state, pipeline_mode)
                        st.session_state["session_log"].append(log_entry)
                        st.session_state["last_result"] = completed_state
                        if completed_state.errors:
                            st.sidebar.error(
                                "Pipeline completed with errors: "
                                + "; ".join(completed_state.errors)
                            )
                        else:
                            st.sidebar.success(
                                f"Pipeline finished at step '{completed_state.current_step}'."
                            )
                    except Exception as exc:
                        st.sidebar.error(f"Pipeline run failed: {exc}")
                    finally:
                        st.session_state["running"] = False

    st.sidebar.subheader("Session Controls")
    st.sidebar.metric(
        "Contracts Reviewed This Session",
        len(st.session_state["session_log"]),
    )
    if st.sidebar.button("Clear Session", use_container_width=True):
        st.session_state["session_log"] = []
        st.session_state["last_result"] = None
        st.sidebar.info("Session cleared.")

    st.sidebar.subheader("Report Generation")
    session_count = len(st.session_state["session_log"])
    st.sidebar.text(f"Session log: {session_count} contracts ready for report")
    generate_disabled = session_count == 0
    if st.sidebar.button(
        "Generate Session Audit Report",
        use_container_width=True,
        disabled=generate_disabled,
    ):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        md_path = LOGS_DIR / f"audit_report_{timestamp}.md"
        json_path = LOGS_DIR / f"audit_report_{timestamp}.json"
        report = SessionAuditReport(st.session_state["session_log"])
        written_md = report.generate(str(md_path))
        report.to_json(str(json_path))
        st.sidebar.success(f"Audit report written to: {written_md}")
        st.balloons()


def _render_contract_review_tab() -> None:
    if not is_dataset_configured():
        st.warning(get_dataset_configuration_help())
        st.info(
            "Use the **Governance Layer** tab to review SDD governance without the CUAD dataset."
        )

    last_result: Optional[AgentState] = st.session_state.get("last_result")
    if last_result is None:
        if is_dataset_configured():
            st.info("Select a contract from the sidebar and run the pipeline.")
        else:
            st.caption("Contract Review results will appear here after you configure CUAD_DATASET_ZIP and run the pipeline.")
        return

    final_report = last_result.shared_data.get("final_report", {})
    if final_report:
        _render_contract_review(final_report, last_result)
        return

    st.warning(
        f"Partial pipeline completed at step '{last_result.current_step}'. "
        "Run the full pipeline for executive summary and clause breakdown."
    )
    st.metric("Current Step", last_result.current_step)
    st.metric("Extractions", len(last_result.shared_data.get("extractions", [])))
    risk_summary = last_result.shared_data.get("risk_summary", {})
    if risk_summary:
        st.subheader("Risk Summary")
        st.json(risk_summary)
    with st.expander("View Agent Execution Traces", expanded=False):
        for trace in last_result.execution_traces:
            st.markdown(f"**{format_trace_summary_line(trace)}**")
            st.caption(trace.agent_rationale)
            st.json(trace.output_generated)


def _render_session_log_tab() -> None:
    session_log: List[Dict[str, Any]] = st.session_state.get("session_log", [])
    if not session_log:
        st.info("No contracts reviewed yet this session.")
        return

    st.subheader(f"Contracts Reviewed: {len(session_log)}")
    st.dataframe(_build_session_log_dataframe(session_log), use_container_width=True)

    contract_names = [entry.get("contract_title", "Unknown") for entry in session_log]
    selected_name = st.selectbox("View detail for:", options=contract_names)
    selected_entry = next(
        entry for entry in session_log if entry.get("contract_title") == selected_name
    )
    final_report = selected_entry.get("final_report", {})
    if final_report:
        pseudo_state = AgentState(
            session_id=selected_entry.get("session_id", ""),
            contract_title=selected_entry.get("contract_title", ""),
            current_step=selected_entry.get("current_step", ""),
        )
        _render_contract_review(final_report, pseudo_state)
    else:
        st.warning("Full report not available for this entry. Partial pipeline run.")
        st.json(selected_entry)


def _render_governance_layer_tab() -> None:
    st.info(GOVERNANCE_DATASET_INDEPENDENCE_NOTE)

    if st.button("Run Governance Check", key="run_governance_check"):
        with st.spinner("Running governance validation..."):
            try:
                result = run_governance_check_sync(PROJECT_ROOT)
                st.session_state["governance_last_result"] = result
                st.rerun()
            except Exception as exc:
                st.error(f"Governance check could not complete: {exc}")

    audience: Audience = st.selectbox(
        "Report Audience",
        options=list(AUDIENCE_OPTIONS),
        key="governance_report_audience",
    )

    st.subheader("SDD Governance Architecture")
    st.markdown(get_architecture_explanation(audience))

    check_result: Optional[GovernanceCheckResult] = st.session_state.get("governance_last_result")
    latest_files = load_latest_governance_report(LOGS_DIR)
    active_report, metrics, metrics_source = resolve_governance_display_state(
        check_result,
        latest_files,
    )

    status_label = get_status_display_label(str(metrics.get("overall_status", "unknown")))
    st.subheader("Current Governance Status")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Overall Status", status_label)
    metric_cols[1].metric("Critical", metrics.get("critical_count", 0))
    metric_cols[2].metric("Warnings", metrics.get("warning_count", 0))
    metric_cols[3].metric("Info", metrics.get("info_count", 0))

    if metrics.get("timestamp"):
        st.caption(f"Latest report timestamp: {metrics['timestamp']}")
    elif latest_files is not None and metrics_source == "disk":
        st.caption(f"Latest saved report modified: {latest_files.modified_at.isoformat()}")

    if check_result is not None:
        if check_result.report.exit_code == 0:
            if check_result.report.overall_status == "pass_with_warnings":
                st.warning("Latest in-session check: passed with warnings.")
            else:
                st.success("Latest in-session check: passed.")
        else:
            st.error("Latest in-session check: failed — critical findings detected.")
        st.caption(f"Report paths: `{check_result.markdown_path}` | `{check_result.json_path}`")
    elif metrics_source == "disk":
        st.caption("Showing latest saved governance report from data/logs/. Run **Run Governance Check** to refresh in this session.")

    st.markdown("### Summary")
    st.markdown(summarize_governance_for_audience(active_report, metrics, audience))

    with st.expander("What this governance layer checks", expanded=False):
        st.markdown(get_what_governance_checks(audience))

    with st.expander("Latest findings", expanded=metrics.get("critical_count", 0) > 0):
        if active_report is None:
            st.caption("No governance report loaded yet.")
        else:
            if active_report.failures:
                st.markdown("**Critical**")
                for finding in active_report.failures:
                    st.error(f"{finding.rule_id}: {finding.message}")
            if active_report.warnings:
                st.markdown("**Warnings**")
                for finding in active_report.warnings:
                    st.warning(f"{finding.rule_id}: {finding.message}")
            if active_report.infos:
                st.markdown("**Info**")
                for finding in active_report.infos:
                    st.caption(f"{finding.rule_id}: {finding.message}")
            if not active_report.all_findings:
                st.success("No findings — repository conforms to governance policies.")

    with st.expander("Recommended remediation", expanded=False):
        for line in get_remediation_lines(active_report):
            st.markdown(f"- {line}")

    with st.expander("Known limitations", expanded=False):
        limitations = (
            active_report.known_limitations
            if active_report is not None
            else GovernanceReport.default_known_limitations()
        )
        for item in limitations:
            st.markdown(f"- {item}")

    st.subheader("Recent Governance Reports")
    recent_reports = list_governance_report_markdown_files(LOGS_DIR)
    if not recent_reports:
        st.info("No governance reports in data/logs yet. Run a governance check to create one.")
    else:
        selected_report = st.selectbox(
            "Select report",
            options=recent_reports,
            format_func=lambda path: path.name,
        )
        json_report_path = json_path_for_markdown_report(selected_report)
        st.caption(f"Markdown: `{selected_report}`")
        if json_report_path.is_file():
            st.caption(f"JSON: `{json_report_path}`")
        with st.expander("View report content", expanded=True):
            st.markdown(selected_report.read_text(encoding="utf-8"))
        with st.expander("Raw report output", expanded=False):
            st.markdown("**Markdown file**")
            st.code(selected_report.read_text(encoding="utf-8"), language="markdown")
            if json_report_path.is_file():
                st.markdown("**JSON file**")
                st.code(json_report_path.read_text(encoding="utf-8"), language="json")


def _render_pipeline_inspector_tab() -> None:
    st.subheader("How the Pipeline Works")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### Agent 1: Extraction")
        st.markdown(
            "Reads the contract from CUADv1.json. Matches the 10 playbook clause "
            "types using CUAD's pre-labeled QA pairs. Outputs ClauseExtraction objects."
        )
    with col2:
        st.markdown("### Agent 2: Risk Assessment")
        st.markdown(
            "Compares each extracted clause against the playbook standards. "
            "Assigns severity ratings: critical, high, medium, low. Flags missing clauses."
        )
    with col3:
        st.markdown("### Agent 3: Summary")
        st.markdown(
            "Synthesizes all risk flags into a plain-English executive brief. "
            "Ranks top priority actions. Produces the final report."
        )

    st.divider()

    last_result: Optional[AgentState] = st.session_state.get("last_result")
    if last_result is not None and last_result.execution_traces:
        st.subheader("Last Run — Agent Timing (Sequential)")
        timing_rows = build_pipeline_inspector_rows(last_result.execution_traces)
        st.dataframe(timing_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Agents run sequentially (Extraction → Risk → Summary). "
            "Millisecond timestamps and duration_ms show separate steps even when "
            "completed times share the same second."
        )

    st.divider()

    st.subheader("Playbook Standards")
    try:
        playbook_data = json.loads(PLAYBOOK_PATH.read_text(encoding="utf-8"))
        st.json(playbook_data)
    except Exception as exc:
        st.error(f"Unable to load playbook: {exc}")


def main() -> None:
    st.set_page_config(layout="wide", page_title="CUAD Contract Reviewer")
    _init_session_state()
    _render_sidebar()

    tab_review, tab_session, tab_governance, tab_inspector = st.tabs(
        ["Contract Review", "Session Audit", "Governance Layer", "Pipeline Inspector"]
    )

    with tab_review:
        _render_contract_review_tab()

    with tab_session:
        _render_session_log_tab()

    with tab_governance:
        _render_governance_layer_tab()

    with tab_inspector:
        _render_pipeline_inspector_tab()


if __name__ == "__main__":
    main()
