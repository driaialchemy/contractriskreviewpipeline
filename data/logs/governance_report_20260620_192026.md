# CUAD SDD Governance Report

**Generated:** 2026-06-20T19:20:26.674793+00:00
**Overall Status:** pass_with_warnings
**Risk Level:** medium

## Validation Summary

- **repo**: PASS (critical=0, warnings=2)
- **spec**: PASS (critical=0, warnings=0)
- **policy**: PASS (critical=0, warnings=0)
- **agent**: PASS (critical=0, warnings=0)
- **pipeline**: PASS (critical=0, warnings=0)
- **audit**: PASS (critical=0, warnings=0)

## Domain Details

- Repo validation status: PASS
- Spec validation status: PASS
- Policy validation status: PASS
- Agent validation status: PASS
- Pipeline validation status: PASS
- Audit validation status: PASS

## Critical Failures

- None

## Warnings

- **[warning] sensitive_path_present** (`.pytest_cache`): Sensitive path present (agent editing forbidden): .pytest_cache
  - Remediation: Treat matched paths as agent-unsafe; avoid autonomous edits
- **[warning] sensitive_path_present** (`__pycache__`): Sensitive path present (agent editing forbidden): __pycache__
  - Remediation: Treat matched paths as agent-unsafe; avoid autonomous edits

## Recommended Remediation

- **sensitive_path_present**: Treat matched paths as agent-unsafe; avoid autonomous edits

## Evidence File Paths

- Evidence paths recorded after report write.

## SDD Layers

- **Methodology (SDD):** Machine-readable specs under `governance/specs/`
- **Policy-as-code:** YAML policies enforced by Python validators
- **CI/CD execution:** GitHub Actions runs pytest and governance validation
- **Audit evidence:** This report and pipeline audit logs under `data/logs/`
