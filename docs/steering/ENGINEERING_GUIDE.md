# Engineering Guide

Audience: senior/staff engineers. Purpose: capture project-wide technical policies concisely.

## Search & Indexing
- Defaults: `search_limit=10`, `search_threshold=0.2`.
- Normalization: trim + lowercase `category`/`tags` everywhere (index, filters, queries).
- FTS fields: `name`, `description`, `tags_text` (tags joined with spaces), `category` (normalized). `instructions` is excluded from FTS.
- Scalar indexes: `category` BITMAP, `tags` LABEL_LIST for fast prefiltering.
- Reindex policy: drop-and-recreate table; rebuild FTS and scalar indexes; log failures to stderr (never stdout).
- Fallbacks: embedding failure → FTS; FTS failure → substring match with low score; keep this chain intact.
- Unsupported: LanceDB `field_boosts` not available in current SDK; do not attempt until supported.

## Configuration
- Default to `EMBEDDING_PROVIDER=none`; require keys/models and fail fast when provider is enabled.
- Keep code/PRD/PLAN aligned on defaults (limit 10, threshold 0.2, FTS fields).

## Tooling
- Package manager & runner: `uv sync`, `uv run <cmd>`, `uv run pytest`, `uv run ruff check`, `uv build`/`uv publish`. Prefer `UV_CACHE_DIR=.uv-cache` in locked-down environments.

## Data Modeling
- Pydantic (LanceModel/BaseModel) is used for any data that crosses process boundaries or hits storage (e.g., `SkillRecord`, request/response models); it gives validation and schema stability.
- `dataclass` はサービス内部の一時・軽量オブジェクトに限定（例: `SearchResult` のような中間表現）。外部公開する場合は `.to_dict()` で整形して返す。
- 混在は可だが、どちらを使うかの判断基準を上記に揃えること。

## Logging & MCP Constraints
- stdout must carry JSON-RPC only; all diagnostics go to stderr.

## Security & Safety
- Preserve path traversal protections and command allowlist/timeout caps.
- When changing schema or search behavior, update PRD + PLAN before implementation.

## Execution Model (run_skill_command)

### Responsibility Separation
| Responsibility | Owner |
|----------------|-------|
| Command execution with security guards | SkillHub |
| Ready Check (verify execution readiness) | SkillHub |
| Runtime Resolution (prefer skill-local env) | SkillHub |
| **Environment Setup (venv, dependencies)** | **Skill Author** |

### Why Skill Authors Own Setup
Package managers are diverse (uv, poetry, pip, npm, yarn, pnpm, bun, conda...). Supporting all natively would:
- Explode complexity and maintenance burden
- Require constant updates as tools evolve
- Blur SkillHub's core responsibility (discovery, loading, execution)

SkillHub focuses on **execution** and **readiness verification**; skill authors choose their tools and document setup in `README.md`.

### Runtime Resolution
- `python`/`python3`: `skill_dir/.venv/bin/python` preferred, fallback to PATH
- `node`: Always use PATH `node` (Node.js is not installed in node_modules)
- `uv`: PATH `uv` with `UV_PROJECT_ENVIRONMENT=skill_dir/.venv` auto-set

### Ready Check
- `requires_setup: true` triggers readiness verification before execution
- Default: `runtime=python` → check `.venv/bin/python` exists
- Default: `runtime=node` → check `node_modules` exists
- Failure returns `SKILL_NOT_READY` error with hint to check skill's README.md

### SKILL.md vs README.md
- **SKILL.md**: AI Agent instructions only (no setup steps)
- **README.md**: Human-readable setup instructions (in skill directory)

See `docs/latest/EXECUTION_ENV.md` for full specification.

## Specification & Acceptance Guidance
- For PRD/SPEC/API docs, express acceptance criteria in EARS form (WHEN/IF … THEN …) and place them adjacent to the feature/endpoint description.
- Reference source-of-truth paths (PRD, SEARCH_ALGORITHM, code modules) rather than vague prose so tasks/tests can be traced.
- Derive tests (unit/integration/PBT) directly from those EARS statements; keep names/comments aligned for reviewability.
