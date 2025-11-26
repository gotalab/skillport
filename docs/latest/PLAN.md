# Plan & Context: SkillHub (package: skillhub-mcp)

**Current Version:** v0.0.1
**Status:** Core Complete → Preparing for Public Release
**Goal:** Provide a reusable Agent Skills hub via MCP, distributed via PyPI/uvx.

## Release Roadmap

```
v0.0.x  ──→  v0.5.0  ──→  v1.0.0  ──→  v1.x+
 現在        API安定化     公開安定版     機能拡張
```

| Version | Milestone | Key Items |
|---------|-----------|-----------|
| **v0.0.x** | Core Complete | 基本機能完成、CI/CD整備 |
| **v0.5.0** | API Stability | `__all__`定義、Griffe導入、STABILITY.md |
| **v1.0.0** | Public Release | PyPI公開、破壊的変更検出必須化 |
| **v1.x+** | Feature Expansion | 追加機能、エコシステム拡大 |

## Next: v0.5.0 (API Stability)

- [ ] Define `__all__` in `src/skillhub_mcp/__init__.py` (public API明確化)
- [ ] Add Griffe to CI for breaking change detection
- [ ] Create `STABILITY.md` (Stable/Experimental API分類)
- [ ] README.md update for public users

## Next: v1.0.0 (Public Release)

- [ ] PyPI publish workflow (`publish-pypi.yml`)
- [ ] Griffe check required (PR blocking)
- [ ] Security audit (dependencies, input validation)
- [ ] User documentation (installation, quickstart, examples)

---

> このPLANは「どう作るか」のSSOTです。小粒タスクは本ファイルに1行で完結させます。

## Context
This project aims to make Claude's Agent Skills reusable across different environments (Cursor, Windsurf, Claude Desktop) by serving them through an MCP server.
- **PRD:** [PRD.md](./PRD.md)
- **Philosophy:** [SKILL_PHILOSOPHY.md](./SKILL_PHILOSOPHY.md) - Agent Skillsの本質的な位置づけと設計方針
- **Core Tech:** Python, FastMCP, LanceDB, Pydantic.
- **Environment:** `uv` for dependency management.
- **Distribution:** PyPI (`pip install skillhub-mcp`), uvx (`uvx skillhub-mcp`)

## Completed Phases

### Phase 1: Core Implementation (Completed)
- [x] **Project Structure**: `pyproject.toml`, `src/skillhub_mcp` layout.
- [x] **Configuration (`config.py`)**: Environment variable loading via Pydantic.
- [x] **Database (`db.py`)**: LanceDB integration, Indexing logic, Hybrid Search (Vector + FTS).
- [x] **Utilities (`utils.py`)**: Security checks (Path Traversal), Frontmatter parsing.
- [x] **MCP Server (`server.py`)**:
    - [x] `search_skills`: Hybrid search with server-side filtering.
    - [x] `load_skill`: Loading instruction content.
    - [x] `read_skill_file`: Safe file reading with size limits.
    - [x] `run_skill_command`: Safe command execution with allowlist & timeout.

### Phase 2: Verification & Testing (Current Focus)
- [x] **Dependency Management**: `uv sync` executed.
- [x] **Example Skills**: Created `hello-world` in `.agent/skills/`.
    - [x] `hello-world` skill
    - [ ] `file-reader` skill (Optional for now)
- [x] **Manual Verification**:
    - [x] Verify `search_skills` returns expected results.
    - [x] Verify `load_skill` strips frontmatter.
    - [x] Verify `run_skill_command` blocks disallowed commands.
    - [x] Verify Path Traversal protection in `read_skill_file`.
    - [x] Verified using `verify_server.py` script (Mock Client).
- [x] Add integration tests: embedding failure→FTS, FTS failure→substring, vector-only threshold path.
- [x] Add tests for enabled filter normalization (trim+lower for skills/categories) to keep prefilter/enforcement aligned.
- [ ] Add smoke tests for stdout discipline (JSON-RPC only) and core-skills prompt list respecting enabled settings.
- [x] Add coverage for read_skill_file non-UTF-8 rejection and run_skill_command cwd/shell=False/timeout/truncation behavior.

### Phase 3: Refinement & Enhancements
- [x] **Config Improvements**: Default `EMBEDDING_PROVIDER` to `none` for safer start.
- [x] **Core Skills (`alwaysApply`)**:
    - [x] Support `alwaysApply: true` in `SKILL.md`.
    - [x] Inject core skills description into Server Instructions (System Prompt).
- [x] **Code Refactoring**:
    - [x] Split `server.py` into phase-based modules (`tools/discovery.py`, `tools/loading.py`, `tools/execution.py`).
    - [x] Simplify `server.py` to handle only server initialization.
- [x] Add Unit Tests (`tests/`).
- [ ] Improve Error Handling & Logging.
- [x] Wrap search embedding errors to fall back to FTS.
- [x] Add scalar indexes for category/tags to speed filters.
- [x] Refactor DB/search into services (IndexStateStore, SkillSearchService, SearchResult model) to reduce coupling and ease future extensions.
- [x] Normalize enabled-skills prefilter to match runtime trimming/lowercase behavior.
- [x] Propagate settings overrides end-to-end (embeddings/utils/tools) so SkillDB(settings_override) is honored.
- [x] Drop stale index/table when SKILLS_DIR is missing to avoid serving old skills.
- [x] ~~Support `ollama` embedding integration testing.~~ (Removed from scope)
- [x] Align SEARCH_ALGORITHM.md with current defaults (threshold 0.2) and FTS fields (name/description/tags/category).
- [x] Normalize category/tags (trim+lower) before indexing and update docs.
- [x] Make SkillDB instantiation explicit (no module-import side effects; inject into tools/server).
- [ ] Add FTS boosts (field_boosts) — blocked: LanceDB create_fts_index current version lacks field_boosts support.
- [x] Add hash-based index freshness check at startup (skip rebuild when unchanged) and sidecar state file next to DB.
- [x] Provide manual `reindex` entry point (CLI/MCP tool) that forces `initialize_index()`; document in RUNBOOK.
- [x] Update PRD/SEARCH_ALGORITHM to reflect search_threshold=0.2.
- [x] Update PRD.md to reflect current search defaults/fields/normalization (limit=10, threshold=0.2, no boosts).
- [x] Establish docs versioning policy (docs/latest as SSOT; VERSIONING.md created; snapshots under docs/releases/vX.Y.Z).
- [x] Create concise English guides: AGENTS.md (core), ENGINEERING_GUIDE.md, RUNBOOK.md.
- [x] Branding alignment: Brand name is **SkillHub**; package/CLI stays `skillhub-mcp` with alias `skillhub`.
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
- [x] Document testing strategy (docs/steering/TESTING_CHARTER.md).
- [x] Document verify_server operational usage (RUNBOOK/TESTING_CHARTER).
- [x] Refactor DB module into `skillhub_mcp/db/` package (embeddings, models, search, facade).
- [x] Align README.md with current config defaults (Python version, embedding provider, search fallback, paths).
- [x] Add product-style use case stories to README.md highlighting multi-client usage and context efficiency.
- [x] Draft execution environment & setup model for `run_skill_command` (docs/latest/EXECUTION_ENV.md).
- [x] Migrate SKILL.md schema to `metadata.skillhub.*` (category/tags/runtime/setup); legacy SKILL.md schemaはサポート対象外とする。
- [x] Drop stale index/table when no skills are present after reindex to avoid serving old entries.
- [x] Skip non-mapping SKILL.md frontmatter during reindex to prevent crashes and stale state.
- [x] Revise EXECUTION_ENV.md to v2 (Approach B: setup delegated to skill authors).

### Phase 4: Execution Environment Enhancement
- [x] Add `runtime` and `requires_setup` fields to SkillRecord model (DB schema change).
- [x] Update search.py to parse and index `runtime`/`requires_setup` from SKILL.md frontmatter.
- [x] Implement Runtime Resolution (prefer skill-local .venv/bin/python over system PATH).
- [x] Implement Ready Check (path_exists verification before execution for requires_setup: true skills).
- [x] Implement Setup Detection (auto-detect from dependency files like pyproject.toml, package.json).
- [x] Add SKILL_NOT_READY structured error response.
- [x] Implement Startup Status Report (shows skill readiness at server startup).
- [x] Remove `env_version` from sample skills (hello-world, pdf, etc.).
- [x] Add `skillhub-mcp --setup-list` CLI for skill readiness overview.
- [x] Add `skillhub-mcp --setup-auto` CLI for uv/npm auto-setup.
- [x] Add `bash`, `sh` to ALLOWED_COMMANDS for shell script execution.
- [x] Fix `--setup-auto` to work when run from parent project with pyproject.toml.
  - Problem: `uv venv` and `uv pip install` were using parent project's `.venv` instead of skill-local `.venv`.
  - Solution: Use `uv venv --no-project .venv` and `uv pip install -p .venv` to isolate skill environments.
- [x] Add cross-platform guidelines to EXECUTION_ENV.md (Python recommended, bash requires WSL/Git Bash on Windows).
- [x] Fix sample skills: `skill-creator`, `webapp-testing` → `requires_setup: false` (stdlib only), `web-artifacts-builder` → `runtime: none` (bash scripts, no skill-local deps).
- [x] Create SKILL_PHILOSOPHY.md documenting Agent Skills positioning:
  - Agent Skillsは「知識を提供するもの」であり「実行環境」ではない
  - `run_skill_command` は補助的ツール、主要実行はユーザー側
  - Path-Based Design: スキルのパスを返し、ローカル実行を可能に
  - Git-Based Management: ローカル管理、GitHub共有

### Phase 5: Execution Model Simplification (Completed)

**背景**: SKILL_PHILOSOPHY.md で定義した「MCPは知識提供者、実行環境ではない」方針に基づき、
実行モデルを大幅に簡素化する。skill-local 環境管理を廃止し、`uv run` + PEP 723 による
自己完結型スクリプト実行モデルに移行する。

#### 5.1 削除対象
- [x] `requires_setup` フィールド削除 (SkillRecord model, SKILL.md schema)
- [x] `runtime: node` オプション削除 (Python のみサポート)
- [x] skill-local `.venv` サポート削除
- [x] Ready Check ロジック削除 (`check_skill_ready`, `get_ready_check_path`)
- [x] Setup Detection ロジック削除 (`detect_setup_command`, `SETUP_COMMANDS`)
- [x] `--setup-list` CLI 削除
- [x] `--setup-auto` CLI 削除
- [x] `setup.py` モジュール削除
- [x] Startup Status Report 簡素化

#### 5.2 新しい実行モデル
- [x] Python 実行: `uv run python` を優先、フォールバックで `python3`
  ```python
  def resolve_python_command() -> list[str]:
      if shutil.which("uv"):
          return ["uv", "run", "python"]
      else:
          print("[WARN] uv not found. PEP 723 dependencies won't work.", file=sys.stderr)
          return ["python3"]
  ```
- [x] PEP 723 インライン依存サポート
  ```python
  # /// script
  # requires-python = ">=3.11"
  # dependencies = ["pypdf", "pillow"]
  # ///
  ```
- [x] `runtime` フィールド: `python` | `none` のみ (node 削除)
- [x] bash/sh スクリプトは引き続きサポート

#### 5.3 フィールド変更

**Before:**
```yaml
metadata:
  skillhub:
    runtime: python | node | none
    requires_setup: true | false
```

**After:**
```yaml
metadata:
  skillhub:
    runtime: python | none  # node 削除, requires_setup 削除
```

#### 5.4 ドキュメント更新
- [x] EXECUTION_ENV.md 全面改訂 (v3.0 → v3.2)
- [x] SKILL_PHILOSOPHY.md に PEP 723 セクション追記
- [x] サンプルスキル更新 (requires_setup 削除, runtime 削除)
- [x] PRD.md 更新 (run_skill_command を DISABLED BY DEFAULT に)
- [x] SKILL_PHILOSOPHY.md 更新 (run_skill_command を DISABLED BY DEFAULT に)
- [ ] README.md 更新 (optional, can defer)

### Phase 6: Skill Validation & CLI Enhancement (Completed)

#### 6.1 Skill Validation (Agent Skills Spec)
- [x] Add `lines` field to SkillRecord model (SKILL.md line count)
- [x] Implement validation checks:
  - [x] SKILL.md line count (recommended: ≤200)
  - [x] frontmatter.name: max 64 chars, a-z/0-9/- only
  - [x] frontmatter.name: no reserved words (anthropic, claude)
  - [x] frontmatter.name: must match directory name
  - [x] frontmatter.name: required (not empty)
  - [x] frontmatter.description: max 1024 chars, no XML tags
  - [x] frontmatter.description: required (not empty)
- [x] Startup report shows validation issues (top 5, warnings first)
- [x] Trophy ASCII art when all skills pass validation

#### 6.2 CLI Enhancement
- [x] `--lint` CLI: Detailed validation report for all skills
- [x] `--lint <skill-name>`: Validate specific skill
- [x] `--list` CLI: List all skills without starting server
- [x] `--list` shows ★ marker for alwaysApply skills
- [x] Exit code 0 (pass) / 1 (fail) for CI/CD integration

#### 6.3 Code Refactoring
- [x] Extract validation logic to `validation.py`
- [x] Extract CLI modes to `cli.py`
- [x] Simplify `server.py` to server creation only

#### 5.5 移行ガイド
- `requires_setup: true` のスキル → PEP 723 形式に移行、または path-based ローカル実行
- `runtime: node` のスキル → `runtime: none` (prompt-only) に変更、path-based ローカル実行

#### 5.6 レスポンススキーマ変更 (Context Engineering)

**目的**: パスベース設計により `read_skill_file` の使用を最小化し、コンテキスト効率を向上させる。
エージェントがファイル内容を読まずにパスで直接実行できるようにする。

**search_skills レスポンス**: 発見フェーズなので `path` は不要。
```python
{"name": "pdf", "description": "...", "score": 0.85}
```

**load_skill レスポンス**: 実行フェーズなので `path` を含む。
```python
{
    "name": "pdf",
    "instructions": "... SKILL.md content ...",
    "path": "/path/to/skills/pdf"   # スキルディレクトリ (相対パス解決用)
}
```

**パス解決**: Instructions で "run script.py" と書かれていた場合、
エージェントは `path + "/script.py"` で絶対パスを構築し、直接実行する。

**実装タスク**:
- [x] `load_skill` に `path` フィールド追加
- [x] ツール description を AI エージェント向けに改善
- [x] MCP サーバー instructions を改善 (path 解決の説明追加)
- [x] `scripts` フィールド削除 (SKILL.md の instructions が SSOT)
- [x] `search_skills` から `path` 削除 (load_skill に集約)
- [x] `run_skill_command` を deprecated に変更
- [x] `run_skill_command` をデフォルトで無効化 (コメントアウト)
- [x] `runtime` フィールド削除

**Note**:
- `scripts` フィールドは削除: SKILL.md instructions が SSOT
- `search_skills` は発見用、`path` は `load_skill` でのみ提供
- `run_skill_command` はデフォルト無効: Agent は自分のターミナルで直接実行すべき
- `runtime` フィールドは削除: 全スキル同一の実行モデル

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
