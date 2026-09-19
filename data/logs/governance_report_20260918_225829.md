# CUAD SDD Governance Report

**Generated:** 2026-09-18T22:58:29.955310+00:00
**Overall Status:** pass
**Risk Level:** low
**Exit Code:** 0
**Exit Behavior:** Exit 0 unless critical findings exist; warnings and info do not fail validation.
**Default Enforcement Mode:** validation_only

## Severity Counts

- Critical: 0
- Warning: 0
- Info: 2

## Validation vs Enforcement

- **validation_only:** Reports conformance against specs/policies; default for all rules in this phase.
- **enforcement_ready:** Reserved for future hooks that could block merges or deployments.
- **execution_blocking:** Not used at runtime today; the CUAD pipeline is not stopped except via CI/CLI exit on critical governance failures.
- Contract **human_review_status** is recorded on high/critical findings but does not prevent summary generation.

## Validation Summary

- **repo**: PASS (critical=0, warnings=0, info=2)
- **spec**: PASS (critical=0, warnings=0, info=0)
- **policy**: PASS (critical=0, warnings=0, info=0)
- **agent**: PASS (critical=0, warnings=0, info=0)
- **pipeline**: PASS (critical=0, warnings=0, info=0)
- **audit**: PASS (critical=0, warnings=0, info=0)

## Domain Details

- Repo validation status: PASS
- Spec validation status: PASS
- Policy validation status: PASS
- Agent validation status: PASS
- Pipeline validation status: PASS
- Audit validation status: PASS

## Critical Findings

- None

## Warning Findings

- None

## Info Findings

- **[info] generated_cache_path_present** (validation_only) (`.pytest_cache`): Generated or cache path present (agent-unsafe, not a secret): .pytest_cache
  - Remediation: Safe to ignore locally; add to .gitignore; not equivalent to secrets
- **[info] generated_cache_path_present** (validation_only) (`__pycache__`): Generated or cache path present (agent-unsafe, not a secret): __pycache__
  - Remediation: Safe to ignore locally; add to .gitignore; not equivalent to secrets

## Recommended Remediation

- No remediation required for critical or warning findings.

## Evidence File Paths

- Evidence paths recorded after report write.

## Known Limitations

- AST-based agent validation checks static class patterns only.
- Dynamic agent registration or monkey-patching is not validated.
- Dataset availability is runtime configuration (CUAD_DATASET_ZIP) and not required for governance validation.
- CI branch triggers are configured for main/master; adjust .github/workflows/governance.yml for other default branches.
- Governance rules default to validation_only; they report conformance and do not stop the CUAD pipeline at runtime except via CI/CLI exit on critical failures.
- High/critical contract findings require human_review_status but do not prevent summary generation in the current pipeline.

## SDD Layers

- **Methodology (SDD):** Machine-readable specs under `governance/specs/`
- **Policy-as-code:** YAML policies enforced by Python validators with Pydantic schema checks
- **CI/CD execution:** GitHub Actions runs pytest and governance validation
- **Audit evidence:** This report and pipeline audit logs under `data/logs/`
