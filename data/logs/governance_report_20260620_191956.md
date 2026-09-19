# CUAD SDD Governance Report

**Generated:** 2026-06-20T19:19:56.006585+00:00
**Overall Status:** fail
**Risk Level:** critical

## Validation Summary

- **repo**: PASS (critical=0, warnings=2)
- **spec**: PASS (critical=0, warnings=0)
- **policy**: PASS (critical=0, warnings=0)
- **agent**: FAIL (critical=3, warnings=0)
- **pipeline**: PASS (critical=0, warnings=0)
- **audit**: PASS (critical=0, warnings=0)

## Domain Details

- Repo validation status: PASS
- Spec validation status: PASS
- Policy validation status: PASS
- Agent validation status: FAIL
- Pipeline validation status: PASS
- Audit validation status: PASS

## Critical Failures

- **[critical] agent-extends-base** (`src/agents/extraction.py`): ExtractionAgent must inherit from BaseAgent
  - Remediation: Inherit from BaseAgent in src/agents/base.py
- **[critical] agent-extends-base** (`src/agents/risk.py`): RiskAgent must inherit from BaseAgent
  - Remediation: Inherit from BaseAgent in src/agents/base.py
- **[critical] agent-extends-base** (`src/agents/summary.py`): SummaryAgent must inherit from BaseAgent
  - Remediation: Inherit from BaseAgent in src/agents/base.py

## Warnings

- **[warning] sensitive_path_present** (`.pytest_cache`): Sensitive path present (agent editing forbidden): .pytest_cache
  - Remediation: Treat matched paths as agent-unsafe; avoid autonomous edits
- **[warning] sensitive_path_present** (`__pycache__`): Sensitive path present (agent editing forbidden): __pycache__
  - Remediation: Treat matched paths as agent-unsafe; avoid autonomous edits

## Recommended Remediation

- **sensitive_path_present**: Treat matched paths as agent-unsafe; avoid autonomous edits
- **agent-extends-base**: Inherit from BaseAgent in src/agents/base.py

## Evidence File Paths

- Evidence paths recorded after report write.

## SDD Layers

- **Methodology (SDD):** Machine-readable specs under `governance/specs/`
- **Policy-as-code:** YAML policies enforced by Python validators
- **CI/CD execution:** GitHub Actions runs pytest and governance validation
- **Audit evidence:** This report and pipeline audit logs under `data/logs/`
