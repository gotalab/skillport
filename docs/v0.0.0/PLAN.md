# Plan & Context: skillhub-mcp v0.0.0

**Status:** Implementation Complete (v0.0.0-alpha)
**Goal:** Provide a reusable Agent Skills hub via MCP.

## Context
This project aims to make Claude's Agent Skills reusable across different environments (Cursor, Windsurf, Claude Desktop) by serving them through an MCP server.
- **PRD:** [PRD.md](./PRD.md)
- **Core Tech:** Python, FastMCP, LanceDB, Pydantic.
- **Environment:** `uv` for dependency management.

## Roadmap & Tasks

### Phase 1: Core Implementation (Completed)
- [x] **Project Structure**: `pyproject.toml`, `src/skillhub_mcp` layout.
- [x] **Configuration (`config.py`)**: Environment variable loading via Pydantic.
- [x] **Database (`db.py`)**: LanceDB integration, Indexing logic, Hybrid Search (Vector + FTS).
- [x] **Utilities (`utils.py`)**: Security checks (Path Traversal), Frontmatter parsing.
- [x] **MCP Server (`server.py`)**:
    - [x] `search_skills`: Hybrid search with server-side filtering.
    - [x] `load_skill`: Loading instruction content.
    - [x] `read_file`: Safe file reading with size limits.
    - [x] `execute_skill_command`: Safe command execution with allowlist & timeout.

### Phase 2: Verification & Testing (Current Focus)
- [x] **Dependency Management**: `uv sync` executed.
- [x] **Example Skills**: Created `hello-world` in `.agent/skills/`.
    - [x] `hello-world` skill
    - [ ] `file-reader` skill (Optional for now)
- [x] **Manual Verification**:
    - [x] Verify `search_skills` returns expected results.
    - [x] Verify `load_skill` strips frontmatter.
    - [x] Verify `execute_skill_command` blocks disallowed commands.
    - [x] Verify Path Traversal protection in `read_file`.
    - [x] Verified using `verify_server.py` script (Mock Client).

### Phase 3: Refinement & Enhancements
- [x] **Config Improvements**: Default `EMBEDDING_PROVIDER` to `none` for safer start.
- [x] **Core Skills (`alwaysApply`)**:
    - [x] Support `alwaysApply: true` in `SKILL.md`.
    - [x] Inject core skills description into Server Instructions (System Prompt).
- [x] **Code Refactoring**:
    - [x] Split `server.py` into phase-based modules (`tools/discovery.py`, `tools/loading.py`, `tools/execution.py`).
    - [x] Simplify `server.py` to handle only server initialization.
- [ ] Add Unit Tests (`tests/`).
- [ ] Improve Error Handling & Logging.
- [x] Wrap search embedding errors to fall back to FTS.
- [x] Add scalar indexes for category/tags to speed filters.
- [ ] Support `ollama` embedding integration testing.
- [x] Align SEARCH_ALGORITHM.md with current defaults (threshold 0.3) and FTS fields (name/description/tags/category).
- [x] Normalize category/tags (trim+lower) before indexing and update docs.
- [ ] Add FTS boosts (field_boosts) — blocked: LanceDB create_fts_index current version lacks field_boosts support.
- [x] Update PRD/SEARCH_ALGORITHM to reflect search_threshold=0.3.
- [x] Update PRD.md to reflect current search defaults/fields/normalization (limit=10, threshold=0.3, no boosts).
- [x] Establish docs versioning policy (docs/latest as SSOT; VERSIONING.md created; snapshots under docs/releases/vX.Y.Z).
- [x] Create concise English guides: AGENTS.md (core), ENGINEERING_GUIDE.md, RUNBOOK.md.
- [x] Code review (2025-11-22).
- [x] Fix path traversal guard to restrict to skill directory.
- [x] Sanitize skill lookup to avoid filter injection.
- [x] Handle missing OpenAI key and vectorless schema safely.
- [x] Truncate command output by byte length, not characters.
- [x] Add Gemini embedding provider support (config + embeddings).
- [ ] (Removed) Cohere embedding provider support.
- [ ] (Removed) Mistral embedding provider support.
- [x] Simplify provider validation (fail-fast on missing key/model; ignore extras).
- [x] Ensure FTS (_score) is used for ranking/score when embeddings are disabled.
- [x] Implement full SEARCH_ALGORITHM.md logic (Pre-filtering, Dynamic Thresholding).
- [x] Verify SQL injection protection for search filters.

## Usage Context for Droid
To run the server for testing:

1.  **Environment**:
    - Tool: `uv`
    - Skills Directory: `.agent/skills`
    - DB Path: `~/.skillhub/skills.lancedb` (default)
    - Embedding Provider: Defaults to `none` (no API key required).

2.  **Run Command**:
    ```bash
    SKILLS_DIR=.agent/skills uv run skillhub-mcp
    ```
    *(No need to set EMBEDDING_PROVIDER=none explicitly anymore)*

3.  **Testing**:
    - Run `uv run verify_server.py` to verify all tools.

## Current State
- **Verified Working**: Core functionality verified.
- **New Features**: `alwaysApply: true` skills are auto-listed in system prompt.
- **Fixes Applied**: 
    - Config defaults to safe mode (`none`).
    - Fixed `index out of bounds` for `none` embedding provider.
    - Fixed `create_fts_index` arguments.
    - Fixed `print` to `stderr` to avoid JSON-RPC corruption.
- Ready for release/usage.

## Search Strategy (no-embedding, lightweight, multilingual-friendly)
- **Index (Tantivy FTS)**: Fields `name` (high boost), `description` (medium), `instructions` (low or excluded). No n-gram, no synonym, no stop-words, no stemming (keeps non-Latin languages intact and reduces cost).
- **Tokenizer**: Default Unicode + lowercase. Minimal normalization only.
- **Query Preprocess**: Trim + compress spaces only. No language detection, no stemming.
- **Ranking**: Use BM25 `_score` directly; optionally normalize client-side as `score/top_score`. Fetch `limit*3~4` then apply enabled-skill filtering.
- **Fallback**: If FTS errors, do a simple substring match over `name`/`description` with fixed low score (e.g., 0.1) to avoid zero results.
- **Rationale**: Zero embeddings -> minimal CPU/Memory; small index; resilient to multilingual input without heavy analyzers.

### Status
- [x] Index limited to `name` and `description` with BM25.
- [x] Query normalization (trim + whitespace compression).
- [x] Fallback substring match for FTS failures.
- [x] Server instructions clarified (Agent Skills concept, English).
- [x] Dynamic Filtering (Max-Ratio Normalization).
- [x] Pre-filtering based on enabled skills/categories (SQL Injection protected).
