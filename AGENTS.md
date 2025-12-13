# Agent Guidelines & Context

## 1. Core Principles (10-second recall)
* **PLAN.md**: SSOT for「どう作るか」(how to build); keep tasks in `docs/latest/PLAN.md`, update continuously, snapshot at release.
* **Task tracking**: Use checkbox lists (`- [ ]`/`- [x]`); include Task ID for larger work.
* **Safe defaults**: Default `EMBEDDING_PROVIDER=none`; when enabling external providers, fail fast on missing keys.
* **Normalization**: Always trim+lowercase `category`/`tags` for indexing, filtering, and search.
* **Fallback chain**: Preserve vector → FTS → substring fallback; never break the chain.
* **MCP logging**: stdout is JSON-RPC only; send all logs/debug to stderr.
* **Behavioral regression tests (golden traces)**: Not required now; add for critical flows when ready.
* **Refactoring style**: Prefer function-based design with dict dispatch over class-based Strategy/ABC patterns. Keep helpers small; share common logic via helper functions, not inheritance.
* **Docs governance**: See `docs/AGENTS.md` for layout/roles; `docs/steering/OPERATING_MODEL.md` for doc/release ops; `docs/steering/ENGINEERING_GUIDE.md` for technical policy; `docs/steering/RUNBOOK.md` for operational steps.

## 2. Project Context
### Architecture
*   **Brand**: SkillPort
*   **Package & CLI**: `skillport` (legacy alias: `skillport-mcp`)
*   **Type**: MCP Server (Model Context Protocol)
*   **Stack**:
    *   **Runtime**: Python 3.10+
    *   **Package Manager**: `uv`
    *   **MCP Lib**: `fastmcp`
    *   **Database**: `lancedb` (Vector + FTS)
    *   **Config**: `pydantic-settings`

### Directory Structure
*   `src/skillport/`: Source code (modular monolith)
    *   `interfaces/cli/`: Typer CLI adapter
    *   `interfaces/mcp/`: FastMCP server adapter
    *   `modules/skills/`: Skill management public/internal APIs
    *   `modules/indexing/`: Index build/query logic
    *   `shared/`: Config, types, utils, exceptions
*   `docs/latest/`: Living documentation (SSOT)
*   `docs/releases/vX.Y.Z/`: Release snapshots (frozen)
*   `docs/steering/`: Governance & guides
*   `.agent/skills/`: Local skills storage for testing
*   `verify_server.py`: Verification script (Mock Client)

## 3. Operation & Verification
To act autonomously, always verify changes using these commands:

*   **Install/Sync**: `uv sync`
*   **Run Server (Manual)**:
    ```bash
    SKILLPORT_SKILLS_DIR=.agent/skills SKILLPORT_EMBEDDING_PROVIDER=none uv run skillport
    ```
*   **Verify Functionality (Critical)**:
    ```bash
    uv run verify_server.py
    ```
    *   Always run this after modifying `server.py`, `db/`, or `config.py`.

## 4. Debugging & Logging
*   **MCP Constraints**: The server communicates via `stdout`.
    *   **NEVER** print debug info to `stdout`.
    *   **ALWAYS** use `sys.stderr` for logs/prints.
*   **Logs**: If `verify_server.py` fails, check the `stderr` output captured in the tool result.
