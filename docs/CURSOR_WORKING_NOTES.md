# CUAD — Cursor Working Notes

## Core (10 bullets)

1. **Pipeline:** `main.py` / `dashboard.py` → `run_pipeline` → ExtractionAgent → RiskAgent → SummaryAgent → `EXECUTION_LOG.md` + `data/logs/{session_id}.json`.
2. **State:** Pydantic in `src/orchestrator/state.py`; `RiskFlag` has `severity`, `deviation`, `human_review_status`.
3. **Config:** `src/config.py` — `CUAD_DATASET_ZIP` env var (no hardcoded dataset paths); `get_logs_dir()` for audit logs.
4. **Governance:** `python -m governance.validate` — specs/policies in `governance/`, Pydantic schema validation, findings: critical/warning/info.
5. **Sensitive paths:** Critical (`.env`, secrets, `*.db`) → critical; generated/cache (`__pycache__`, `.pytest_cache`) → info only.
6. **Enforcement:** Default `validation_only` — reports conformance; exit 1 on critical only; does not block pipeline runtime (CI/CLI only).
7. **Human review:** High/critical contract flags set `human_review_status=required`; summary still generates (not execution-blocking).
8. **Tests:** `tests/test_pipeline.py` (10), `tests/test_governance.py`, `tests/test_config.py`.
9. **CI:** `.github/workflows/governance.yml` — pytest, governance validate, upload `data/logs/governance_report_*` artifacts.
10. **Rules:** async-only, type hints, preserve existing agents/CLI/dashboard.

## Dashboard governance tab

- Tab: **Governance Layer** — helpers in `governance/dashboard_view.py`; no dataset required.
- Audience selector: Executive / Technical / User; `summarize_governance_for_audience()`.
- Run check via `run_governance_check_sync()` (internal, not subprocess).
- Dataset: Governance tab works without `CUAD_DATASET_ZIP`; Contract Review shows warnings when unset.
