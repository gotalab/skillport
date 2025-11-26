# Test Plan (v0.0.0) — SkillHub MCP

目的: 現行PRD/SEARCH仕様に対する受入基準をEARS形式で明文化し、テスト設計・実装の起点とする。  
対象: `docs/latest/PRD.md`, `docs/latest/SEARCH_ALGORITHM.md`, コードベース (server/db/tools/config)。

## テスト方針
- 手段: pytest + Hypothesis（Property-Based Testing）。必要に応じて(基本はPBT)通常の例示テストを併用。
- レベル: ユニット → インテグレーション（tmp skills/DB）→ スモーク（verify_server.pyラップ）。
- hermetic: ネットワークなし、tmpディレクトリでDB/skillsを生成。
- トレース: テスト名やコメントに EARS ID を含め、PRD/SEARCHへのパス参照を残す。
- PBT実行数: `max_examples` は原則100以上（デフォルト上書き可）。境界条件を含めカバレッジを確保する。

### PBTでカバーする領域（例示不要）
- S1, S2: 文字列正規化は純粋関数。空白・Unicode・長文をHypothesisで網羅。
- S4b: enabledフィルタ入力のtrim+lower整合性を純粋関数レベルで検証。
- S5a: `_score` 付き結果の動的閾値ロジック（ヒット数境界や0スコア含む）。
- C1: provider/keyの組み合わせによるfail-fast（環境変数生成をstrategy化）。

### PBTが難しく例示/統合で担保する領域
- S3a/S3b: 埋め込み失敗・FTS失敗の例外経路はモックDB/例外を仕込む統合テストで確認。
- S4a: enabled skills/categories フィルタは実データ行を持つテーブル/一時DBで検証。
- S5b: `_distance` のみ返るベクトル結果は擬似テーブルを用いた例示テストで期待挙動を固定。
- S6: instructionsをFTS対象外にするには実インデックスを作る統合テストが必要。
- L1/F1/X1: ファイル存在・サイズ・エンコード、cwd固定やshell=False、timeout/出力トランケートはプロセス/FS操作を伴うため例示・統合。
- A1: `alwaysApply` + enabled設定の組み合わせがサーバ指示文へ反映されることをサーバ起動スモークで確認。
- O1: stdout汚染検知は `uv run verify_server.py` をラップし、stderrのみでログされることを確認するスモーク。

## 受入基準 (EARS)
- **S1 Search normalization** — WHEN query has extra whitespace THEN it is trimmed/space-compressed before search (PRD §3.2, SEARCH_ALGORITHM).  
- **S2 Category/tags normalization** — WHEN category/tags include mixed case/whitespace THEN they are lowercase-trimmed before indexing/filtering (PRD §4.1).  
- **S3a Embedding fallback to FTS** — WHEN embedding fetch raises THEN FTS path is used without failing (PRD §3.2, §6.3).  
- **S3b FTS fallback to substring** — WHEN FTS search raises THEN substring search over name/description runs with low fixed score (PRD §3.2, §6.3).  
- **S4a Enable filters** — WHEN enabled skills/categories are set THEN results include only allowed skills while index retains all skills (PRD §3.1, §4.2).  
- **S4b Filter normalization parity** — WHEN enabled_skills/enabled_categories include mixed case/whitespace THEN server treats them trim+lower so prefilter and enforcement agree (PRD §3.1, §4.2).  
- **S5a Dynamic threshold (FTS scores)** — WHEN hits >5 and `_score` exists THEN drop score/top_score < threshold; results ≤ limit sorted by score (PRD §3.2, SEARCH_ALGORITHM).  
- **S5b Vector-only results** — WHEN only `_distance` is present (no `_score`) THEN dynamic threshold is skipped and results are capped to `limit` without error; tool-level score is derived as `1 - _distance` (current behavior).  
- **S6 Instructions excluded from FTS** — WHEN searching a token only in instructions THEN no FTS hit (PRD §4.1).
- **S7 Empty/wildcard query lists all** — WHEN query is empty string, whitespace-only, or "*" THEN `search_skills` returns all enabled skills up to `SEARCH_LIMIT` without search scoring (PRD §3.2).  
- **L1 load_skill** — WHEN skill is disabled/missing THEN error; WHEN present THEN frontmatter is stripped and body returned unchanged (PRD §3.3).  
- **F1 read_skill_file traversal/size/encoding** — WHEN absolute/escaping path THEN reject; WHEN file exceeds MAX_FILE_BYTES THEN truncated flag is set; WHEN file is non-UTF-8 THEN error (PRD §3.4, §6.1).  
- **X1 run_skill_command** — WHEN command not in allowlist THEN reject; WHEN runtime exceeds timeout THEN timeout flag; WHEN output exceeds EXEC_MAX_OUTPUT_BYTES THEN truncated flags; execution runs with `cwd` = skill dir and `shell=False` (PRD §3.5, §6.2).  
- **C1 Init fail-fast** — WHEN embedding provider is set but required key is missing THEN initialization fails (PRD §4.2).  
- **A1 Core skills in instructions** — WHEN `alwaysApply=true` AND skill is enabled THEN server instructions list it; disabled core skills must not appear (PRD §4.2, server prompt contract).  
- **O1 Stdout discipline** — WHEN server/tools run THEN stdout is JSON-RPC only; diagnostics go to stderr (AGENTS, MCP constraint).

## テスト設計メモ (優先順)
1. ユニット: S1, S2, S4b, S5a, C1（正規化・フィルタ整合・閾値・設定フェイルファスト）。
2. インテグレーション: S3a/S3b（例外誘発でフォールバック確認）, S4a, S5b（_distance のみパス）, S6, S7（空クエリ/ワイルドカード）, L1, F1, X1, A1（tmp skills/DB＋スタブ/フィクスチャ）。
3. スモーク: O1（pytest から `uv run verify_server.py` を呼ぶ薄いラッパ、stdout 汚染を検知）。  

## 実行コマンド（推奨）
- `uv run ruff check .`
- `uv run pytest -q`
- `uv run verify_server.py`

## Traceabilityルール
- テスト関数名に EARS ID を含める（例: `test_s1_query_normalization`）。
- コメントやdocstringに対応する PRD/SEARCH パスを記載。
- PBT では `@given` 直前に EARS ID をコメントで示す。
