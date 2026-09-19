import argparse
import asyncio
import json
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import CUAD_JSON_NAME, get_dataset_zip_path, get_logs_dir, get_project_root
from src.orchestrator.engine import run_pipeline
from src.orchestrator.state import AgentState

PROJECT_ROOT = get_project_root()
LOGS_DIR = get_logs_dir()
EXECUTION_LOG_PATH = PROJECT_ROOT / "EXECUTION_LOG.md"


def _read_first_contract_title(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path, "r") as archive:
        raw_json = archive.read(CUAD_JSON_NAME)
    dataset: Dict[str, Any] = json.loads(raw_json)
    contracts = dataset.get("data", [])
    if not contracts:
        raise ValueError("No contracts found in CUAD dataset")
    title = contracts[0].get("title")
    if not title:
        raise ValueError("First contract has no title")
    return str(title)


def _resolve_contract_title(contract: Optional[str], use_first: bool) -> str:
    if use_first:
        return _read_first_contract_title(get_dataset_zip_path())
    if contract:
        return contract
    raise ValueError("Must specify --contract or --first")


def _print_final_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("CUAD CONTRACT REVIEW — FINAL REPORT")
    print("=" * 72)
    print(f"Contract:     {report.get('contract_title', '')}")
    print(f"Session ID:   {report.get('session_id', '')}")
    print(f"Review Date:  {report.get('review_date', '')}")
    print(f"Overall Risk: {report.get('overall_risk_severity', '')}")
    print("-" * 72)
    print("\nEXECUTIVE SUMMARY")
    print(report.get("executive_summary", ""))
    print("\nCLAUSE OVERVIEW")
    print(
        f"  Clauses reviewed: {report.get('total_clauses_reviewed', 0)} | "
        f"Found: {report.get('clauses_found', 0)} | "
        f"Missing: {report.get('clauses_missing', 0)} | "
        f"Risk flags: {report.get('total_risk_flags', 0)}"
    )
    print("\nCLAUSE BY CLAUSE")
    for entry in report.get("clause_by_clause", []):
        status = entry.get("status", "")
        severity = entry.get("severity", "")
        clause_type = entry.get("clause_type", "")
        preview = entry.get("extracted_text", "")
        print(f"  [{severity.upper()}] {clause_type} ({status})")
        if preview:
            print(f"    Text: {preview}")
        print(f"    Action: {entry.get('recommendation', '')}")
    print("\nTOP PRIORITY ACTIONS")
    actions = report.get("top_priority_actions", [])
    if actions:
        for action in actions:
            print(f"  {action}")
    else:
        print("  No critical or high priority actions.")
    print("=" * 72 + "\n")


async def _save_state_log(state: AgentState) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{state.session_id}.json"

    def _write() -> None:
        log_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    await asyncio.to_thread(_write)
    return log_path


async def _run(contract_title: str) -> None:
    session_id = str(uuid.uuid4())
    state = AgentState(session_id=session_id, contract_title=contract_title)

    final_state = await run_pipeline(state)

    if final_state.errors:
        print("Pipeline completed with errors:")
        for error in final_state.errors:
            print(f"  - {error}")
    else:
        final_report = final_state.shared_data.get("final_report", {})
        if final_report:
            _print_final_report(final_report)

        # Layer 1: internal governance (repo-owned validators)
        severity = str((final_report or {}).get("overall_risk_severity", "")).lower()
        if severity == "critical" and not (final_report or {}).get("executive_summary"):
            print("Internal governance blocked: critical risk requires executive summary")
            return

        # Layer 2: governor blocking harness
        from governance_logger import require_approval
        require_approval("contractriskreviewpipeline", "Agent completed successfully", {
            "session_id": session_id,
            "contract_title": contract_title,
            "result": final_state.shared_data.get("final_report", {})
        })

    log_path = await _save_state_log(final_state)
    print(f"Execution log written to: {EXECUTION_LOG_PATH}")
    print(f"Full state saved to: {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CUAD Contract Review & Risk Flagging Pipeline"
    )
    parser.add_argument(
        "--contract",
        type=str,
        help="Contract title to review (exact match from CUAD dataset)",
    )
    parser.add_argument(
        "--first",
        action="store_true",
        help="Run pipeline on the first contract in CUADv1.json",
    )
    args = parser.parse_args()

    contract_title = _resolve_contract_title(args.contract, args.first)
    print(f"Starting pipeline for contract: {contract_title}")
    asyncio.run(_run(contract_title))


if __name__ == "__main__":
    main()
