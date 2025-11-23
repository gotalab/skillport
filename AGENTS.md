# Agent Guidelines & Context

## 1. Core Principles (10-second recall)
* **SSOT**: Keep specs/tasks in `docs/latest/PLAN.md` updated first (release snapshots to `docs/releases/vX.Y.Z/`).
* **Task tracking**: Use PLAN todo lists (`- [ ]`) and mark completion (`- [x]`) immediately.
* **Safe defaults**: Default `EMBEDDING_PROVIDER=none`; when enabling external providers, fail fast on missing keys.
* **Normalization**: Always trim+lowercase `category`/`tags` for indexing, filtering, and search.
* **Fallback chain**: Preserve vector → FTS → substring fallback; never break the chain.
* **MCP logging**: stdout is JSON-RPC only; send all logs/debug to stderr.
* **Behavioral regression tests (golden traces)**: Not required now; add for critical flows when ready.
* **Docs governance**: See `docs/AGENTS.md` for layout/roles; `docs/steering/OPERATING_MODEL.md` for doc/release ops; `docs/steering/ENGINEERING_GUIDE.md` for technical policy; `docs/steering/RUNBOOK.md` for operational steps.

## 2. Project Context
### Architecture
*   **Brand**: SkillHub
*   **Package & CLI**: `skillhub-mcp` (alias: `skillhub`)
*   **Type**: MCP Server (Model Context Protocol)
*   **Stack**:
    *   **Runtime**: Python 3.13+
    *   **Package Manager**: `uv`
    *   **MCP Lib**: `fastmcp`
    *   **Database**: `lancedb` (Vector + FTS)
    *   **Config**: `pydantic-settings`

### Directory Structure
*   `src/skillhub_mcp/`: Source code
    *   `server.py`: Server initialization
    *   `tools/`: Tool implementations (discovery, loading, execution)
    *   `db.py`: Database & Search logic
    *   `config.py`: Configuration
*   `docs/v0.0.0/`: Documentation & PLAN.md
*   `.agent/skills/`: Local skills storage for testing
*   `verify_server.py`: Verification script (Mock Client)

## 3. Operation & Verification
To act autonomously, always verify changes using these commands:

*   **Install/Sync**: `uv sync`
*   **Run Server (Manual)**:
    ```bash
    SKILLS_DIR=.agent/skills EMBEDDING_PROVIDER=none uv run skillhub-mcp  # or: uv run skillhub
    ```
*   **Verify Functionality (Critical)**:
    ```bash
    uv run verify_server.py
    ```
    *   Always run this after modifying `server.py`, `db.py`, or `config.py`.

## 4. Debugging & Logging
*   **MCP Constraints**: The server communicates via `stdout`.
    *   **NEVER** print debug info to `stdout`.
    *   **ALWAYS** use `sys.stderr` for logs/prints.
*   **Logs**: If `verify_server.py` fails, check the `stderr` output captured in the tool result.
