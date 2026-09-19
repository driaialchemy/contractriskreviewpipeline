# Context Usage Report

Generated: 2026-06-19T22:08:39.166632+00:00
Chat: CUAD contract review and risk flagging pipeline
Repository: cuaddataset
Context window: 200K (200,000 tokens)
Tokens used: ~64.3K (64,277 tokens)
Window fill: 32% Full

## Category Summary

| Category | Tokens | Share of Used |
| --- | ---: | ---: |
| Conversation | 46.4K | 72.2% |
| Tool definitions | 8.3K | 12.9% |
| Rules | 2.9K | 4.6% |
| Skills | 2.8K | 4.3% |
| MCP | 2.6K | 4.0% |
| Subagent definitions | 821 | 1.3% |
| System prompt | 465 | 0.7% |

## Items by Category

### Conversation (95 items)

| Item | Est. Tokens | Source / Preview |
| --- | ---: | --- |
| Tool: Write | 5997 | {   "contents": "import asyncio\nimport json\nimport uuid\nimport zipfile\nfrom datetime import date… |
| User Message | 5756 | <user_query> Read this complete system handoff document. Switch into autonomous execution mode. Crea… |
| User Message | 3220 | <user_query> Read this complete handoff. Switch into autonomous execution mode. Create every file wi… |
| Tool: Write | 3026 | {   "contents": "import json\nfrom typing import Any, Dict\nfrom unittest.mock import MagicMock, pat… |
| Tool: Write | 2511 | {   "contents": "import json\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfro… |
| Tool: Write | 2292 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\risk.py",   "contents": "impo… |
| Tool: Write | 2111 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\README.md",   "contents": "# CUAD Contract… |
| Tool: Write | 2030 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\summary.py",   "contents": "f… |
| Tool: Write | 1765 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\extraction.py",   "contents":… |
| Tool: Write | 1692 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\nchemy\\cuad\\main.py",   "contents": "import arg… |
| Tool: Write | 1689 | {   "contents": "import argparse\nimport asyncio\nimport json\nimport uuid\nimport zipfile\nfrom pat… |
| Tool: Write | 1461 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\orchestrator\\engine.py",   "contents… |
| Tool: Write | 1056 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\data\\playbook.json",   "contents": "{\n  … |
| Tool: Write | 800 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\CLAUDE.md",   "contents": "# CUAD Contract… |
| Tool: Write | 623 | {   "contents": "\"\"\"Verification script for dashboard pipeline and report generation.\"\"\"\nimpo… |
| Agent Message | 555 | The **CUAD Contract Review & Risk Flagging Pipeline** is built at `C:\Users\msell\OneDrive\AIAlchemy… |
| Tool: Shell | 550 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; $env… |
| Agent Message | 527 | The Streamlit dashboard is added on top of the existing CUAD pipeline. No `src/` files were modified… |
| Tool: Write | 485 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\orchestrator\\state.py",   "contents"… |
| Tool: StrReplace | 319 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: StrReplace | 313 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: Shell | 310 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; python -c \"\nimport zipfile, js… |
| Tool: Write | 292 | {   "contents": "import json\nimport re\nimport zipfile\n\nz = zipfile.ZipFile(r\"C:\\Users\\msell\\… |
| Tool: Write | 287 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\base.py",   "contents": "from… |
| Tool: Shell | 274 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git add data/logs/.gitkeep; git … |
| Tool: StrReplace | 261 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: StrReplace | 251 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: StrReplace | 248 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: StrReplace | 247 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: StrReplace | 245 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Agent Message | 236 | Created `README.md` at `C:\Users\msell\OneDrive\AIAlchemy\cuad\README.md`.  It covers:  - **Project … |
| Tool: Write | 210 | {   "contents": "import argparse\nimport asyncio\nimport json\nimport uuid\nimport zipfile\nfrom pat… |
| Tool: StrReplace | 188 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: StrReplace | 182 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: Write | 177 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\.cursorrules",   "contents": "# CUAD Contr… |
| Tool: StrReplace | 163 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: Shell | 160 | {   "command": "mkdir \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\" 2>$null; mkdir \"C:\\Users\\ms… |
| Tool: Shell | 155 | {   "command": "New-Item -ItemType Directory -Force -Path \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\c… |
| Tool: Shell | 153 | {   "command": "python -c \"import zipfile, json; z=zipfile.ZipFile(r'C:\\Users\\msell\\OneDrive\\AI… |
| Tool: Shell | 145 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git … |
| Tool: Shell | 144 | {   "command": "python -c \"import zipfile, json; z=zipfile.ZipFile(r'C:\\Users\\msell\\OneDrive\\AI… |
| Tool: Shell | 141 | {   "command": "python -c \"import zipfile, json; z=zipfile.ZipFile(r'C:\\Users\\msell\\OneDrive\\AI… |
| Tool: Shell | 141 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git commit -m \"feat: streamlit … |
| Tool: Shell | 137 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git add data/logs/.gitkeep; git … |
| Tool: Shell | 137 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; pip install streamlit -q; python… |
| Tool: Shell | 127 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git rm -r --cached src/__pycache… |
| Tool: StrReplace | 114 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\test_pipeline.py",   "old_string": … |
| Tool: Write | 109 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\__init__.py",   "contents": "… |
| Tool: Write | 107 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\orchestrator\\__init__.py",   "conten… |
| Tool: Shell | 100 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git add dashboard.py report_buil… |
| Tool: Shell | 95 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; $env… |
| Tool: Shell | 93 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; $env:PYTHONPATH=\".\"; streamlit… |
| Tool: StrReplace | 89 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\extraction.py",   "old_string… |
| Tool: Shell | 88 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; git … |
| Tool: Shell | 86 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuaddataset\" && python -c \"import zipf… |
| Tool: Shell | 86 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\" && pip install pydantic pytest -q… |
| Tool: Shell | 86 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; $env… |
| Tool: Shell | 85 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; pip … |
| Tool: Shell | 83 | {   "block_until_ms": 120000,   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; $env… |
| Tool: StrReplace | 83 | {   "new_string": "            st.session_state[\"contracts_loaded\"] = True",   "old_string": "    … |
| Tool: Shell | 68 | {   "command": "cd \"C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\"; python debug_cuad.py",   "descri… |
| Tool: Write | 53 | {   "contents": "__pycache__/\n*.py[cod]\n.pytest_cache/\ndata/logs/*.json\n",   "path": "C:\\Users\… |
| User Message | 47 | <user_query> write an summary readme.md file and place it in this file folder "C:\Users\msell\OneDri… |
| Tool: Write | 44 | {   "contents": "pydantic\npytest\nstreamlit\n",   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\c… |
| Tool: Shell | 42 | {   "command": "python --version",   "description": "Check Python version",   "required_permissions"… |
| Tool: Read | 42 | {   "path": "C:\\Users\\msell\\.cursor\\projects\\c-Users-msell-OneDrive-AIAlchemy-cuaddataset/termi… |
| Tool: Write | 40 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\requirements.txt",   "contents": "pydantic… |
| Tool: Write | 39 | {   "contents": "",   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\orchestrator\\__ini… |
| Agent Message | 38 | Real CUAD data uses double quotes in questions. Updating the extraction regex to match both quote st… |
| Agent Message | 38 | Reviewing the existing pipeline structure so we can add the Streamlit dashboard without modifying `s… |
| Tool: Write | 37 | {   "contents": "",   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\src\\agents\\__init__.py… |
| Agent Message | 36 | Creating the full CUAD pipeline per the handoff. Exploring the workspace and dataset structure first… |
| Tool: Glob | 35 | {   "glob_pattern": "**/*",   "target_directory": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad" } |
| Tool: Write | 35 | {   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\tests\\__init__.py",   "contents": "" } |
| Tool: Write | 35 | {   "contents": "",   "path": "C:\\Users\\msell\\OneDrive\\AIAlchemy\\cuad\\data\\logs\\.gitkeep" } |
| … | … | 20 additional items not shown |

### Tool definitions (21 items)

| Item | Est. Tokens | Source / Preview |
| --- | ---: | --- |
| Task | 2195 | ~2.2K tokens · 8,780 chars. The full schema is sent to the model but not shown here. |
| Shell | 1215 | ~1.2K tokens · 4,861 chars. The full schema is sent to the model but not shown here. |
| SwitchMode | 837 | ~837 tokens · 3,349 chars. The full schema is sent to the model but not shown here. |
| Grep | 565 | ~565 tokens · 2,260 chars. The full schema is sent to the model but not shown here. |
| GenerateImage | 458 | ~458 tokens · 1,830 chars. The full schema is sent to the model but not shown here. |
| AskQuestion | 419 | ~419 tokens · 1,675 chars. The full schema is sent to the model but not shown here. |
| EditNotebook | 365 | ~365 tokens · 1,459 chars. The full schema is sent to the model but not shown here. |
| CallMcpTool | 295 | ~295 tokens · 1,179 chars. The full schema is sent to the model but not shown here. |
| FetchMcpResource | 294 | ~294 tokens · 1,176 chars. The full schema is sent to the model but not shown here. |
| ReadLints | 260 | ~260 tokens · 1,040 chars. The full schema is sent to the model but not shown here. |
| Glob | 258 | ~258 tokens · 1,032 chars. The full schema is sent to the model but not shown here. |
| TodoWrite | 231 | ~231 tokens · 924 chars. The full schema is sent to the model but not shown here. |
| WebFetch | 213 | ~213 tokens · 850 chars. The full schema is sent to the model but not shown here. |
| Await | 189 | ~189 tokens · 754 chars. The full schema is sent to the model but not shown here. |
| SemanticSearch | 177 | ~177 tokens · 707 chars. The full schema is sent to the model but not shown here. |
| Read | 177 | ~177 tokens · 708 chars. The full schema is sent to the model but not shown here. |
| WebSearch | 152 | ~152 tokens · 609 chars. The full schema is sent to the model but not shown here. |
| SetActiveBranch | 145 | ~145 tokens · 578 chars. The full schema is sent to the model but not shown here. |
| StrReplace | 128 | ~128 tokens · 511 chars. The full schema is sent to the model but not shown here. |
| Delete | 87 | ~87 tokens · 347 chars. The full schema is sent to the model but not shown here. |
| Write | 71 | ~71 tokens · 283 chars. The full schema is sent to the model but not shown here. |

### Rules (1 items)

| Item | Est. Tokens | Source / Preview |
| --- | ---: | --- |
| Cursor & User Rules | 2992 | Content omitted in canvas report |

### Skills (20 items)

| Item | Est. Tokens | Source / Preview |
| --- | ---: | --- |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-build\SKILL.md | 283 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-build\SKILL.md |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-connect\SKILL.md | 275 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-connect\SKILL.md |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-harden\SKILL.md | 271 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-harden\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\sdk\SKILL.md | 248 | C:\Users\msell\.cursor\skills-cursor\sdk\SKILL.md |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-debug\SKILL.md | 248 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-debug\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\canvas\SKILL.md | 222 | C:\Users\msell\.cursor\skills-cursor\canvas\SKILL.md |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-get-started\SKILL.md | 218 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-get-started\SKILL.md |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-optimize\SKILL.md | 215 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-optimize\SKILL.md |
| C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-deploy\SKILL.md | 173 | C:\Users\msell\.cursor\plugins\cache\cursor-public\aws-agents\9ad8fe7d729435ae3788a16fdbf308520ee2b78e\skills\agents-deploy\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\update-cursor-settings\SKILL.md | 83 | C:\Users\msell\.cursor\skills-cursor\update-cursor-settings\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\create-rule\SKILL.md | 82 | C:\Users\msell\.cursor\skills-cursor\create-rule\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\statusline\SKILL.md | 74 | C:\Users\msell\.cursor\skills-cursor\statusline\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\create-hook\SKILL.md | 58 | C:\Users\msell\.cursor\skills-cursor\create-hook\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\split-to-prs\SKILL.md | 53 | C:\Users\msell\.cursor\skills-cursor\split-to-prs\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\create-skill\SKILL.md | 48 | C:\Users\msell\.cursor\skills-cursor\create-skill\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\babysit\SKILL.md | 47 | C:\Users\msell\.cursor\skills-cursor\babysit\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\loop\SKILL.md | 46 | C:\Users\msell\.cursor\skills-cursor\loop\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\review-security\SKILL.md | 38 | C:\Users\msell\.cursor\skills-cursor\review-security\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\review-bugbot\SKILL.md | 35 | C:\Users\msell\.cursor\skills-cursor\review-bugbot\SKILL.md |
| C:\Users\msell\.cursor\skills-cursor\automate\SKILL.md | 34 | C:\Users\msell\.cursor\skills-cursor\automate\SKILL.md |

### MCP (3 items)

| Item | Est. Tokens | Source / Preview |
| --- | ---: | --- |
| ide-browser | 1263 | The cursor-ide-browser MCP server provides a Cursor-owned browser tab plus a raw Chrome DevTools Pro… |
| app-control | 671 | The cursor-app-control MCP allows you to control the Cursor application itself. Use it to: - Move th… |
| aws-agents-awsknowledge | 48 | Content omitted in canvas report |

### Subagent definitions (8 items)

| Item | Est. Tokens | Source / Preview |
| --- | ---: | --- |
| bugbot | 279 | - bugbot: Use only when the user *explicitly* asks for a Bugbot-like review of local code changes. W… |
| security-review | 176 | - security-review: Use only when the user *explicitly* asks for a security review of local code chan… |
| explore | 142 | - explore: Fast, readonly agent specialized for exploring codebases. Use this when you need to quick… |
| cursor-guide | 61 | - cursor-guide: Read Cursor product documentation to answer questions about how Cursor Desktop, IDE,… |
| generalPurpose | 54 | - generalPurpose: General-purpose agent for researching complex questions, searching for code, and e… |
| ci-investigator | 54 | - ci-investigator: Investigate a single failing PR CI check and return a short root-cause summary. U… |
| best-of-n-runner | 46 | - best-of-n-runner: Run a task in an isolated git worktree. Each best-of-n-runner gets its own branc… |
| shell | 35 | - shell: Command execution specialist for running bash commands. Use this for git operations, comman… |

## Recommendations

- **Conversation** is the largest category at 46.4K tokens.
- Start a new chat or summarize the conversation when context exceeds ~80%.
- Trim unused **Rules**, **Skills**, and **MCP** servers to reduce fixed overhead.
- Use targeted `@` file references instead of broad folder attachments.
- Disable subagents you are not actively using.

---

*Source: `context-usage-d9395070-8d0b-4096-a266-ce76221cf893.canvas.data.json`*
