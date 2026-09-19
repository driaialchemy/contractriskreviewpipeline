# CUAD Contract Review & Risk Flagging Pipeline

A production-grade, asynchronous multi-agent system for reviewing legal contracts from the [CUAD dataset](https://github.com/TheAtticusProject/cuad). The pipeline extracts key clauses, compares them against a legal playbook, flags risk deviations with severity ratings, and produces human-readable audit reports.

Built with **native Python asyncio** and **Pydantic** — no heavy agent frameworks.

**Repository:** https://github.com/driaialchemy/cuad

---

## What It Does

1. **Ingests** real CUAD contracts from a zipped JSON dataset
2. **Extracts** clause spans using CUAD's pre-labeled question–answer pairs as ground truth
3. **Assesses risk** by comparing extracted clauses against playbook standards
4. **Summarizes** findings in a plain-English executive brief with prioritized actions
5. **Audits** every run with execution traces and session-level reports

---

## Architecture

Three specialized agents share a single `AgentState` object, orchestrated sequentially:

| Agent | Step | Responsibility |
|---|---|---|
| **ExtractionAgent** | `extraction` | Reads contract from `CUADv1.json`, extracts 10 playbook clause types from Q&A pairs |
| **RiskAgent** | `risk_assessment` | Compares clauses against `data/playbook.json`, assigns severity ratings |
| **SummaryAgent** | `advisory` | Builds executive summary, clause breakdown, and top priority actions |

The orchestrator (`src/orchestrator/engine.py`) routes state through each agent, halts on errors, and writes `EXECUTION_LOG.md`.

```
CUAD Dataset (zip) → ExtractionAgent → RiskAgent → SummaryAgent → Final Report
                          ↓                ↓              ↓
                    ClauseExtractions   RiskFlags    Executive Brief
```

---

## Project Structure

```
cuad/
├── main.py                 # CLI entry point
├── dashboard.py            # Streamlit web dashboard
├── report_builder.py       # Session audit report generator
├── requirements.txt
├── data/
│   ├── playbook.json       # Legal standards for 10 clause categories
│   └── logs/               # Session logs and audit reports
├── src/
│   ├── agents/
│   │   ├── extraction.py   # Agent 1
│   │   ├── risk.py         # Agent 2
│   │   └── summary.py      # Agent 3
│   └── orchestrator/
│       ├── state.py        # Pydantic data models
│       └── engine.py       # Pipeline runner
└── tests/
    └── test_pipeline.py
```

---

## Installation

```bash
pip install -r requirements.txt
```

**Dependencies:** `pydantic`, `pytest`, `streamlit`, `pyyaml`

### Dataset configuration

The pipeline reads CUAD contracts from a zip file at runtime. Set the path via environment variable (no hardcoded local paths in source):

**PowerShell (Windows):**

```powershell
$env:CUAD_DATASET_ZIP="C:\Users\msell\OneDrive\AIAlchemy\cuaddataset\data.zip"
```

**bash:**

```bash
export CUAD_DATASET_ZIP="/path/to/cuaddataset/data.zip"
```

Copy `.env.example` for a template. Do not commit `.env`. Governance validation does **not** require the dataset; only pipeline/dashboard runs do.

---

## Usage

### Command Line

Run on a specific contract:

```bash
python main.py --contract "LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT"
```

Run on the first contract in the dataset:

```bash
python main.py --first
```

Outputs:
- Final report printed to console
- `EXECUTION_LOG.md` at project root
- Full state JSON in `data/logs/{session_id}.json`

### Streamlit Dashboard

```bash
streamlit run dashboard.py
```

The dashboard provides:
- **Contract Review** — metrics, executive summary, clause table, agent traces for the latest run
- **Session Audit** — accumulate results across multiple contract runs and generate session audit reports
- **Governance Layer** — view SDD governance architecture, run governance checks, inspect reports, and switch audience (Executive / Technical / User) for tailored explanations
- **Pipeline Inspector** — agent overview and playbook standards
- **Contract browser** — load and select from CUAD contracts (requires `CUAD_DATASET_ZIP`)

The **Governance Layer** tab does not require the CUAD dataset. Use **Run Governance Check** to invoke the same validation as `python -m governance.validate`. The **Report Audience** selector changes summary wording for executive, technical, or novice readers.

The CLI remains available:

```bash
python -m governance.validate
```

### Manual Streamlit Smoke Test

Use this checklist to verify the dashboard manually in a browser. Automated tests cover helpers and imports only.

1. Launch the dashboard:
   ```bash
   streamlit run dashboard.py
   ```
2. **Without** `CUAD_DATASET_ZIP` set (unset the variable or open a fresh shell):
   - Open the **Governance Layer** tab — it should load without error.
   - Confirm the info note: governance can be reviewed without the CUAD dataset; Contract Review requires `CUAD_DATASET_ZIP`.
   - Click **Run Governance Check** — metrics and status banners should update after rerun; report paths should appear.
   - Change **Report Audience** to Executive, Technical, and User — summary wording should change materially.
   - Open **Recent Governance Reports** and view the latest report content.
3. Open **Contract Review** — confirm a helpful dataset warning appears (not a crash).
4. In the sidebar, confirm **Load Contract List** is disabled or warns when the dataset is not configured.
5. Set the dataset path (PowerShell example):
   ```powershell
   $env:CUAD_DATASET_ZIP="C:\path\to\cuaddataset\data.zip"
   ```
   Restart or refresh Streamlit if needed.
6. **With** `CUAD_DATASET_ZIP` set:
   - Load the contract list and run the pipeline.
   - Confirm **Contract Review** shows results as before.
   - Confirm **Governance Layer** still works independently.

---

## Playbook Clause Categories

The pipeline evaluates 10 key legal clause types defined in `data/playbook.json`:

| Clause | Missing Risk | Ambiguous Risk |
|---|---|---|
| Governing Law | critical | high |
| Termination For Convenience | high | medium |
| Cap On Liability | critical | high |
| Uncapped Liability | critical (if present) | — |
| IP Ownership Assignment | critical | critical |
| Auto-Renewal | low | medium |
| Non-Compete | low | high |
| Audit Rights | medium | medium |
| Insurance | medium | low |
| Exclusivity | low | high |

---

## Dataset

- **Configure with:** `CUAD_DATASET_ZIP` environment variable pointing to `data.zip`
- **File inside zip:** `CUADv1.json` (510 contracts, SQuAD-style JSON)
- **Format:** Each contract has a `title`, full `context` text, and 41 pre-labeled Q&A pairs per clause category

The pipeline reads directly from the zip archive without extracting files to disk.

---

## Testing

```bash
pytest tests/ -v
```

10 pipeline tests cover extraction, risk assessment, summary generation, full pipeline execution, error halting, and audit log export. Additional governance tests validate SDD specs, policies, and validators.

---

## SDD Governance Layer

The CUAD pipeline remains the core product. The **governance layer** checks whether the repo, agents, pipeline outputs, and audit artifacts conform to machine-readable expectations.

### What it does

- Loads **governance specs** and **policy YAML** under `governance/` with **Pydantic schema validation**
- Runs validators for repo structure, agents, pipeline contracts, audit outputs, and CI expectations
- Classifies findings as **critical**, **warning**, or **info**
- Writes evidence to `data/logs/governance_report_{timestamp}.md` and `.json`
- Exits with code **1** only for **critical** findings; warnings and info exit **0**

### Validation-only vs enforcement

| Mode | Behavior in this repo |
|---|---|
| **validation_only** (default) | Reports conformance; does not stop the CUAD pipeline at runtime |
| **enforcement_ready** | Reserved for future merge/deploy gates |
| **execution_blocking** | Not used for pipeline runtime today |

The governance validator reports whether the repository matches specs and policies. It does **not** halt ExtractionAgent, RiskAgent, or SummaryAgent during a contract run—only CI and `python -m governance.validate` exit codes reflect critical governance failures.

Contract **human_review_status** is required on high/critical risk findings (validation + data contract) but **does not prevent** summary generation in the current pipeline.

### SDD as the methodology

**Specification-Driven Development (SDD)** captures intended design in `governance/specs/` (agents, stages, risk fields, audit artifacts, human-review rules, CI expectations). Validators compare the repository against those specs.

### Policy-as-code enforcement

`governance/policies/` define enforceable rules. Validators check required files, **critical sensitive paths** (`.env`, secrets, `*.db`) vs **generated/cache paths** (`__pycache__`, `.pytest_cache` — info only, not secrets), agent structure, risk fields, summary traceability, and audit expectations.

### CI/CD execution

GitHub Actions (`.github/workflows/governance.yml`) runs pytest and `python -m governance.validate`, uploads governance reports as artifacts, and does not deploy. Triggers assume **main/master**; adjust the workflow if your default branch differs.

### Audit reports as evidence

Pipeline runs produce `EXECUTION_LOG.md`, session logs, and session audit reports. Governance reports include severity counts, validation vs enforcement notes, remediation, evidence paths, and known limitations.

### Run the validator locally

```bash
python -m governance.validate
```

### Interpreting results

| Result | Exit code | Meaning |
|---|---|---|
| **pass** | 0 | No critical, warning, or info findings |
| **pass_with_warnings** | 0 | Warnings present; no critical failures |
| **pass** (with info only) | 0 | Info items such as local cache folders; not equivalent to secrets |
| **fail** | 1 | Critical findings — review console output and `data/logs/governance_report_*` |

---

## Output Examples

### Severity Ratings

- **critical** — immediate action required (e.g., missing liability cap)
- **high** — negotiate before signing (e.g., missing termination for convenience)
- **medium** — review and clarify (e.g., missing audit rights)
- **low** — minor concern (e.g., unclear auto-renewal terms)
- **none** — clause present and appears standard

### Generated Files

| File | Description |
|---|---|
| `EXECUTION_LOG.md` | Per-run agent trace and risk summary |
| `data/logs/{session_id}.json` | Full pipeline state snapshot |
| `data/logs/audit_report_{timestamp}.md` | Multi-contract session audit report |
| `data/logs/audit_report_{timestamp}.json` | Session log as JSON |

---

## Design Principles

- Explicit type hints on every function
- `async`/`await` throughout — blocking I/O wrapped with `asyncio.to_thread`
- Pydantic models for all inter-agent data contracts
- No global mutable state
- One contract processed at a time from the zip archive
- Errors appended to state and halt the pipeline immediately

---

## License

See the [CUAD dataset license](https://github.com/TheAtticusProject/cuad) for dataset usage terms.
