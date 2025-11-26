# Testing Charter

Audience: engineers & reviewers. Purpose: keep SkillHub MCP reliable with minimal, fast, automatable tests.

## Goals & Scope
- Protect core invariants: safe defaults (`EMBEDDING_PROVIDER=none`), normalization of `category/tags`, search fallback chain (vector → FTS → substring), stdout reserved for JSON-RPC.
- Cover changes to `server.py`, `db.py`, `config.py`, and tools (`discovery/loading/execution`) with at least one automated check.
- Keep tests hermetic: no external network; use temp directories and copy fixtures from `.agent/skills` when needed.

## Principles
- SSOT first: update `docs/latest/PLAN.md` tasks alongside test work.
- Prefer small, fast, deterministic tests; avoid sleep/time-based checks.
- Assert logging discipline: diagnostics go to stderr only.
- Fail closed: when providers/keys are missing, expect safe behaviour, not silent success.

## Test Levels & Ownership
- **Unit**: pure functions (`utils.py` normalizers, path guards), config validation, db fallback selection. Mock I/O as needed.
- **Integration**: tool flow with temp `SKILLS_DIR`; ensure discovery → loading → execution paths work and emit logs to stderr only.
- **E2E/Regression**: `uv run verify_server.py` is mandatory after touching `server.py`, `db.py`, or `config.py`. Add small golden traces for critical flows when ready.

## Coverage Expectations
- Normalization: trim+lower for tags/category everywhere (index, filters, queries).
- Fallback chain intact: embedding errors → FTS, FTS errors → substring; scores remain non-zero.
- Safety: path traversal blocks outside skills dir; command allowlist + timeout enforced.
- Config: defaults match docs (limit=10, threshold=0.3); providers require keys/models when enabled; `EMBEDDING_PROVIDER=none` boots without API keys.
- Logging: stdout contains only JSON-RPC; stderr used for diagnostics.

## Fixtures & Data
- Use `tmp_path` for writable DB/skill dirs; do not mutate repo files.
- Minimal skills copied from `.agent/skills` or generated inline; keep frontmatter consistent with PRD.
- Keep LanceDB tables isolated per test; drop/recreate in setup/teardown.

## Tooling & Commands
- Runner: `pytest` (>=9). Pluginsは必要になったら追加（例: `pytest-asyncio`, `hypothesis`）。カバレッジ計測も後回しでOK。
- Lint/format: `uv run ruff check .` だけでも可。整形は必要になったら `uv run ruff format .`。
- Static typing: 現段階では optional。安定してから `mypy` を導入。
- ローカル最短ループ: `uv run ruff check . && uv run pytest -q`.
- CI (最小構成): 単一ジョブで `uv run ruff check .` → `uv run pytest` → `uv run verify_server.py`。
- Cache: 余裕があれば `~/.cache/uv` を `uv.lock` ハッシュでキャッシュ。必須ではない。
- Gate for core files: `uv run verify_server.py`（軽量E2Eとして維持）。
- Property-Based Testing: 推奨ライブラリは `hypothesis`。EARSで書いた受入基準に対して `@given` でプロパティを実装し、テスト名/コメントに対応する EARS 文を記載してトレース容易にする。
- PBT density: `max_examples` は原則 100 以上を目安に設定し、境界条件を広く探索する。
- PBT example (Python/Hypothesis, EARS対応):
  - EARS: “WHEN query has extra whitespace THEN it is trimmed/space-compressed before search.”
  - Test: 
    ```python
    from hypothesis import given, settings, strategies as st
    @settings(max_examples=150)
    @given(st.text())
    def test_s1_query_normalization(text):
        expected = " ".join(text.strip().split())
        assert normalize_query(text) == expected
    ```

## CI/Gate Policy
- Order: ruff → pytest → verify_server.py（mypy/coverage は落ち着いてから追加）。
- Fail build on missing fixturesやネットワークアクセス試行。stdout ガードは必要になったら追加。
- Add new tests when: new feature, bug fix, schema/config change, or regression found.

## Verify Server Harness
- Location stays at repo root as a developer-friendly sanity command: `uv run verify_server.py`.
- For pytest integration, add a thin wrapper in `tests/e2e/` that shells out to the same command and asserts zero exit plus clean stdout/stderr.

## Definition of Done (tests-impacting PRs)
- Tests added/updated at the lowest sensible level.
- PLAN updated with status.
- Commands you actually ran listed in PR body (ruff/pytest/verify_server.py); add mypy later when adopted.
- No new flakiness; avoid real network calls.

## Non-Goals
- Full performance benchmarking.
- Broad golden traces for all skills (add only for critical paths when ready).
