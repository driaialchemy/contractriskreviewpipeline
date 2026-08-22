# Quorum — contract risk review pipeline

Agentic data analyst: natural-language questions to validated Snowflake SQL and structured insight reports.

Read `CLAUDE.md` and `AGENTS.md` before using an AI coding agent here.

## Run

```bash
pip install -e .
pytest tests/ -v
streamlit run app.py
```

Do not put connection strings or API keys in this file. Keep secrets in a local `.env` that is not committed.
