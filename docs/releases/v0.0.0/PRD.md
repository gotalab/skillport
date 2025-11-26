# PRD: SkillHub (package: skillhub-mcp)

**Version:** 0.0.0
**Status:** Ready for Implementation
**Target Runtime:** Python 3.10+ / FastMCP / LanceDB / uv

---

## 1. プロダクト概要

* **ブランド:** SkillHub
* **パッケージ/CLI:** `skillhub-mcp`（alias: `skillhub`）
* **目的:**

  * Claude の Agent Skills（`SKILL.md` 構造のスキル） を、Cursor / Windsurf / Claude Desktop / 任意の MCP クライアントから再利用できるようにする。
  * 1つの **スキルハブ (Skill Hub)** として、複数の Agent / IDE から共通のスキルセットにアクセスさせる。
* **コアコンセプト:**

  * **Progressive Disclosure**:

    * まずメタデータだけ検索 (`search_skills`)
    * 必要なスキルだけ instructions をロード (`load_skill`)
    * さらに必要な補助ファイルだけ読む (`read_skill_file`)
  * **Hybrid Search (可変)**:

    * Embedding 有効時: まずベクトル検索（query embedding）。失敗時は FTS にフォールバック。
    * Embedding 無効時 (`EMBEDDING_PROVIDER=none`): FTS のみで検索。
    * 現行実装ではベクトルと FTS のスコア融合は行わない（vector→FTS順のフォールバックのみ）。

---

## 2. ユーザー体験フロー (Agent’s Journey)

すべて **Tool ベース**で実装し、Resource 機能は使わない。

1. **Discovery（発見）**

   * ユーザー:「Python で請求書 PDF からインボイス番号を取って」と依頼。
   * Agent: `search_skills(query="extract invoice number from PDF")` を呼び出し。
   * サーバ:

     * LanceDB に対して、ベクトル検索（埋め込み有効時）＋ FTS を実行。
     * Server 設定で許可されたスキルのみ結果に含める。
   * 戻り値: 関連度が高いスキルの `name / description / score / category` のリスト。

2. **Loading（スキルの装填）**

   * Agent: 最も適切な `skill_name` を選び、`load_skill(skill_name="pdf-invoice-extractor")` を呼び出し。
   * サーバ:

     * 対応する `SKILL.md` を読み、Frontmatter を除いた **本文 (instructions)** のみを返す。
   * Agent: instructions をコンテキストに取り込み、手順に従って思考・実行を進める。

3. **Execution（補助ファイル参照 & コマンド実行）**

   * Agent:

     * `read_skill_file(skill_name="pdf-invoice-extractor", file_path="templates/invoice_template.txt")` でテンプレート読み込み。
     * `run_skill_command(skill_name="pdf-invoice-extractor", command="uv", args=["run", "scripts/extract.py", "..."])` で処理実行。
   * サーバ:

     * Path traversal / symlink escape を防ぎつつファイルを読む。
     * Allowlist されたコマンドだけを、スキルディレクトリを CWD にして実行。
     * stdout / stderr / exit_code / timeout 情報を返す。

---

## 3. MCP Tools 仕様 (v0.0.0)

### 3.1 共通ルール

* **skill_name の定義**

  * `SKILL.md` の Frontmatter `name` を Canonical ID とする。
  * SKILLS_DIR 直下のディレクトリ名も、原則同じ文字列とする（`<SKILLS_DIR>/<skill_name>/SKILL.md`）。
* **スキルの有効/無効**

  * 環境変数で「このサーバから利用して良いスキル / カテゴリ」を指定できる。
  * Tool は、**index 上に存在してもサーバ設定で disable されている skill は操作不可**とする。
* **エラーの扱い**

  * MCP の JSON-RPC 2.0 error として返す。
  * エラーコード例:

    * `SKILL_NOT_FOUND`
    * `SKILL_DISABLED`
    * `FILE_NOT_FOUND`
    * `COMMAND_NOT_ALLOWED`
    * `EXECUTION_TIMEOUT` など。

---

### 3.2 Tool: `search_skills`

**目的:**
自然文クエリから、関連性の高いスキル候補を返す。

#### 引数

```json
{
  "query": "string (必須)"
}
```

* `query`:

  * ユーザーの意図・問題・目的を表す自然文。
  * そのまま embedding / FTS にかける。

#### ふるまい

1. `query` を正規化（trim & 連続空白圧縮）。
2. **検索パス:**

   * Embedding 有効時: クエリをベクトル化 → ベクトル検索。埋め込み失敗時は FTS へフォールバック。
   * Embedding 無効時: 直接 FTS へ。
   * FTS 対象フィールド: `name`, `description`, `tags_text`（tags を空白連結・小文字化したもの）, `category`（小文字化）。
3. サーバ設定でのプリフィルタを適用:

   * `SKILLHUB_ENABLED_SKILLS` / `SKILLHUB_ENABLED_CATEGORIES`（カテゴリも小文字化して一致）で絞り込み。
4. 動的フィルタ:

   * 取得候補は `limit*4` 件。`_score` 降順。
   * ヒット数 ≤ 5 の場合はそのまま上位 `limit` を返す。
   * ヒット数 > 5 の場合、`score / top_score >= search_threshold`（デフォルト 0.2）だけ残し、上位 `limit` を返す。
5. デフォルト `limit` は `SEARCH_LIMIT`（デフォルト 10）。

> 🔁 **Index は常に「全スキル」を保持**し、
> **search_skills は「サーバ設定で有効な subset」にフィルタ**するだけ。
> 設定によって LanceDB の index から行が消えたりはしない。

#### 戻り値スキーマ

```json
{
  "skills": [
    {
      "name": "pdf-invoice-extractor",
      "description": "Extract invoice numbers and key fields from invoice PDFs.",
      "score": 0.87                // 0〜1 の類似度など
    }
  ]
}
```

* `skills` はスコア降順。
* `score` の具体的な値レンジは実装依存だが、0〜1 想定（高いほど関連度が高い）。

---

### 3.3 Tool: `load_skill`

**目的:**
特定スキルの instructions 本文を、Frontmatter を除いた形で取得する。

#### 引数

```json
{
  "skill_name": "string (必須)"
}
```

#### ふるまい

1. `skill_name` が LanceDB index 上に存在するか確認。
2. サーバ設定上、その `skill_name` が有効か確認。
3. 対応する `SKILL.md` を読み込む。
4. YAML Frontmatter 部分をパースし除去し、Markdown 本文だけを取り出す。
5. 本文をそのまま返す（改行・Markdown 構造は保持）。

#### 戻り値スキーマ

```json
{
  "name": "pdf-invoice-extractor",
  "instructions": "### Overview\nThis skill extracts invoice numbers...\n...",
  "path": "/path/to/skills/pdf-invoice-extractor"
}
```

* `path`: スキルディレクトリの絶対パス。instructions 内の相対パス参照を解決するために使用。

---

### 3.4 Tool: `read_skill_file`

**目的:**
スキルフォルダ内の補助ファイル（テンプレート / サンプル / 辞書等）の中身を読む。

#### 引数

```json
{
  "skill_name": "string (必須)",
  "file_path": "string (必須)"  // skill ディレクトリからの相対パスのみ
}
```

* `file_path` の例:

  * `"templates/invoice.txt"`
  * `"examples/sample.json"`
* 絶対パス (`/...` や `C:\...`) は **エラー**。

#### ふるまい

1. `skill_name` が有効か確認。
2. スキルディレクトリ: `skill_dir = SKILLS_DIR / skill_name`
3. `target = (skill_dir / file_path).resolve()` とし、

   * `target` が `SKILLS_DIR.resolve()` 配下かを `startswith` で確認。
   * これにより `../..` や symlink 経由で外に出るのを防止。
4. ファイルサイズが `MAX_FILE_BYTES` （例: 64KB）を超える場合:

   * 読み込みを途中で切り、`truncated: true` として返すか、
   * またはエラーにする（PRD としては「切って返す」推奨）。

#### 戻り値スキーマ

```json
{
  "content": ".... file content ....",
  "encoding": "utf-8",
  "truncated": false
}
```

---

### 3.5 Tool: `run_skill_command` [DISABLED BY DEFAULT]

> ⚠️ **デフォルト無効**: このツールは `server.py` でコメントアウトされています。
> `load_skill` で取得した `path` を使って、エージェント自身のターミナルで直接実行してください。
> 詳細は `SKILL_PHILOSOPHY.md` を参照。

**目的:**
スキルディレクトリを CWD として、安全に CLI コマンドを実行する（補助的用途）。

**有効化が必要なケース:**
- シェルアクセスがないクライアント（例: Claude Desktop）
- スキルの動作確認・デモ

**有効化方法:**
`server.py` の以下の行のコメントを解除:
```python
# mcp.tool()(execution_tools.run_skill_command)
```

#### 引数

```json
{
  "skill_name": "string (必須)",
  "command": "string (必須)",    // 例: "python", "python3", "uv", "bash", "sh"
  "args": ["string", "..."]      // オプション
}
```

#### ふるまい

1. `skill_name` が有効か確認。
2. `command` を `ALLOWED_COMMANDS` の中にあるかチェック。
   * 含まれていなければ `COMMAND_NOT_ALLOWED` エラー。
3. Python 実行 (`python` / `python3`):
   * `uv` がある場合: `uv run python` で実行（PEP 723 インライン依存対応）
   * `uv` がない場合: `python3` で実行
4. 実行:
   * `cwd = SKILLS_DIR / skill_name`
   * `subprocess.run([resolved_command, *args], cwd=cwd, shell=False, timeout=EXEC_TIMEOUT_SECONDS, capture_output=True)`
5. 標準出力 / エラーのサイズが `EXEC_MAX_OUTPUT_BYTES` を超える場合:
   * 途中で切り捨て、`truncated: { stdout: true/false, stderr: true/false }` を立てる。
6. timeout 発生時:
   * プロセスを kill し、`timeout: true` として返す。

#### 戻り値スキーマ

```json
{
  "stdout": "....",
  "stderr": "....",
  "exit_code": 0,
  "timeout": false,
  "truncated": {
    "stdout": false,
    "stderr": false
  }
}
```

#### 推奨パターン: 直接実行

```python
# 非推奨: run_skill_command 経由
run_skill_command("pdf", "python", ["extract.py", "input.pdf"])
# → 出力はスキルディレクトリに作成される

# 推奨: load_skill で path を取得し、直接実行
skill = load_skill("pdf")
# → path = "/path/to/skills/pdf"
# エージェントが直接実行:
# python /path/to/skills/pdf/extract.py input.pdf -o /user/project/output.txt
# → 出力はユーザープロジェクトに直接作成される
```

---

## 4. データモデル & LanceDB

### 4.1 スキーマ

LanceDB のテーブル（例：`skills`）は以下のフィールドを持つ：

| フィールド          | 型                | 出典                                     | 用途                                   |
| -------------- | ---------------- | -------------------------------------- | ------------------------------------ |
| `name`         | str              | SKILL.md frontmatter `name`            | Primary key / 検索                     |
| `description`  | str              | frontmatter `description`              | search_skills 出力 / FTS               |
| `category`     | Optional[str]    | frontmatter `metadata.skillhub.category` (任意, 正規化済み小文字) | フィルタ / FTS                          |
| `tags`         | List[str]        | frontmatter `metadata.skillhub.tags` (任意, 正規化済み小文字)    | フィルタ / FTS 補助                     |
| `tags_text`    | str              | `tags` を空白連結した文字列（内部生成）            | FTS 用フィールド                        |
| `instructions` | str              | SKILL.md 本文                            | load_skill 返却用（現状 FTS 対象外）         |
| `path`         | str              | スキルディレクトリ絶対パス                          | 内部用のみ                              |
| `metadata`     | JSON             | frontmatter `metadata` 全体               | 拡張用                                  |
| `vector`       | Optional[Vector] | `name+description+tags+category` の埋め込み | ベクトル検索（provider=none なら列省略）       |

* FTS インデックス: `name`, `description`, `tags_text`, `category`（全て小文字正規化）。`instructions` は除外。

### 4.2 インデックスライフサイクル

> 🔑 ポイント: **LanceDB の index はつねに「SKILLS_DIR の全スキル」を表現**し、
> 「サーバ設定による有効/無効」は **検索時にフィルタ** する。

* **起動時:**

  1. `SKILLS_DIR` 以下の `*/SKILL.md` の「相対パス + mtime + size + 内容ハッシュ」をソートしてハッシュ化し、`index_state.json`（DB と同じディレクトリ、デフォルト `~/.skillhub/`）で前回値と比較。
  2. **差分あり / state なし / スキーマ or embedding provider 変更** の場合のみ `initialize_index()` を実行。差分なしならスキップ。
  3. 再構築時は従来どおりテーブルをドロップして再作成し、FTS（name/description/tags_text/category）とスカラーインデックス（category BITMAP, tags LABEL_LIST）を張る。

* **実行中の変更:**

  * ホットリロードはスコープ外。
  * 明示的な再インデックス手段: CLI フラグ `--reindex`（または今後追加する管理ツール）で強制再構築できる。
  * 自動チェックを抑止したい場合は `--skip-auto-reindex` フラグまたは `SKILLHUB_SKIP_AUTO_REINDEX=1` を指定。

* **サーバ設定でのサブセット化:**

  * `SKILLHUB_ENABLED_SKILLS` / `SKILLHUB_ENABLED_CATEGORIES` は、

    * index から行を消すのではなく、
    * Tool 実行時 (`search_skills`, `load_skill`, `read_skill_file`, `run_skill_command`) に
      「有効なものだけ通すフィルタ」として使う。

---

## 5. ディレクトリレイアウト & SKILL.md

### 5.1 ディレクトリ構造

デフォルト:

* **Skills ルート:** `SKILLS_DIR`（デフォルト: `~/.skillhub/skills`）
* 各スキル:

```text
~/.skillhub/skills/
  ├── pdf-invoice-extractor/
  │   ├── SKILL.md
  │   ├── templates/
  │   │   └── invoice.txt
  │   └── scripts/
  │       └── extract.py
  └── ...
```

* プロジェクトローカルにまとめたい場合は、例えば:

  * `SKILLS_DIR=./.agent/skills` といった形で、環境変数で上書き可能。

### 5.2 SKILL.md Frontmatter

Agent Skills の仕様（厳格バリデータ）に合わせ、トップレベルの YAML フロントマターは以下のキーのみを許可する:

- `name` (必須)
- `description` (必須)
- `license` (任意)
- `allowed-tools` (任意)
- `metadata` (任意, 任意構造の辞書)

SkillHub では、検索・分類・実行環境に関する情報を `metadata` フィールドの下にまとめる。

#### スキルタイプ

スキルは3種類に分類される。**すべて SkillHub でファーストクラスサポート**:

| タイプ | 説明 | `run_skill_command` | セットアップ |
|-------|------|------------------------|------------|
| **Prompt-only** | 指示・テンプレートのみ | 使用しない | 不要 |
| **Native execution** | stdlib のみ使用 | 使用する | 不要 |
| **Dependency execution** | 外部パッケージ必要 | 使用する | 必要 |

#### Frontmatter 例

```yaml
---
name: code-review-checklist
description: Checklist for reviewing pull requests.
metadata:
  skillhub:
    category: development
    tags: [code-review, pr]
---
```

#### フィールド説明

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | ✅ | スキル識別子（小文字+ハイフン） |
| `description` | ✅ | スキルの機能とトリガー条件 |
| `license` | ❌ | ライセンス |
| `allowed-tools` | ❌ | 実行許可ツールのリスト（Claude Code 用） |
| `metadata` | ❌ | 拡張メタデータ |

**metadata.skillhub 配下:**

| フィールド | デフォルト | 省略 | 説明 |
|-----------|----------|------|------|
| `category` | - | ✅ | フィルタ・検索用カテゴリ（推奨） |
| `tags` | `[]` | ✅ | 検索用タグ（推奨） |
| `alwaysApply` | `false` | ✅ | `true` で Core Skill として列挙 |

> Note: `runtime` と `requires_setup` は v3.1 で削除されました。

**SKILL.md の内容:**
- AI Agent が実行時に参照する指示のみを記載する。
- 人間向けのセットアップ手順は、スキルディレクトリ内の `README.md` に記載する。

詳細は `EXECUTION_ENV.md` を参照。

---

## 6. セキュリティ & 実行環境

### 6.1 ファイルシステム

* **Path Traversal 防止**

  * `read_skill_file` / `run_skill_command` は、

    * `skill_dir = SKILLS_DIR/skill_name`
    * `target = (skill_dir / rel_path).resolve()`
    * `target` が `SKILLS_DIR.resolve()` の配下でない場合は即エラー。
  * symlink 経由の脱出も `resolve()` + `startswith` で検知。

### 6.2 コマンド実行

* `subprocess.run(..., shell=False)` を**必須ルール**とする（`shell=True` 禁止）。
* Allowlist:

  * `ALLOWED_COMMANDS` 環境変数で定義されたコマンド名のみ実行可能。
  * デフォルト例:

    * `python,uv,node,cat,ls,grep`
* Timeout:

  * `EXEC_TIMEOUT_SECONDS`（例: 60）で上限。
* 出力サイズ:

  * `EXEC_MAX_OUTPUT_BYTES`（例: 65536）を超えた分は切り捨て。

### 6.3 プライバシー / Embedding

* `EMBEDDING_PROVIDER=openai`:

  * `name / description / tags / category / query` が OpenAI API に送信される。
    （`tags` / `category` は frontmatter `metadata.skillhub.tags` / `metadata.skillhub.category` から派生した値）
* `EMBEDDING_PROVIDER=gemini`:

  * `name / description / tags / category / query` が Google Gemini API に送信される。
* `EMBEDDING_PROVIDER=none`:

  * ベクトルを一切計算せず、`search_skills` は FTS のみで検索する。
  * スキルメタデータや検索クエリは **ローカルプロセスから外部へ送信されない**。

---

## 7. トランスポート (MCP)

### 7.1 Stdio モード

* 起動例: `skillhub-mcp --transport stdio`（`skillhub` でも可）
* 用途:

  * Cursor / Windsurf / Claude Desktop など、ローカル MCP クライアント。
* 実装:

  * FastMCP の stdio transport を利用。
  * JSON-RPC 2.0 メッセージは stdin/stdout 経由。

### 7.2 HTTP モード（Streamable HTTP 準拠）

* 起動例: `skillhub-mcp --transport http --port 8000`（`skillhub` でも可）
* エンドポイント:

  * `POST /mcp`（必須）
  * `GET /mcp`（SSE ストリーム用、必要なら）
* 仕様:

  * Model Context Protocol の **Streamable HTTP transport** に準拠。

    * クライアント → サーバ: JSON-RPC 2.0 を POST。
    * サーバ → クライアント:

      * 単発レスポンスは JSON。
      * 複数メッセージ / ストリーミングは `text/event-stream` として送信。
* 補助エンドポイント（任意）:

  * `GET /healthz` : 200 を返すだけのヘルスチェック。

---

## 8. Configuration (環境変数)

### 8.1 必須 / デフォルト

| 変数名                  | 必須?         | デフォルト                        | 説明                           |
| -------------------- | ----------- | ---------------------------- | ---------------------------- |
| `SKILLS_DIR`         | 任意          | `~/.skillhub/skills`         | スキルフォルダのルート                  |
| `DB_PATH`            | 任意          | `~/.skillhub/skills.lancedb` | LanceDB ファイルパス               |
| `EMBEDDING_PROVIDER` | 任意          | `none`                      | `openai` / `gemini` / `none` |
| `OPENAI_API_KEY`     | `openai`時必須 | -                            | OpenAI 埋め込み用 API Key         |

### 8.2 検索 / 実行 / ログ系

| 変数名                     | デフォルト                        | 説明                                    |
| ----------------------- | ---------------------------- | ------------------------------------- |
| `EMBEDDING_MODEL`       | プロバイダ依存                      | 使用する embedding モデル名                   |
| `SEARCH_LIMIT`          | `10`                         | search_skills の上限件数（内部では limit*4 を候補取得） |
| `SEARCH_THRESHOLD`      | `0.2`                        | `_score/top_score` での足切り閾値               |
| `ALLOWED_COMMANDS`      | `python,uv,node,cat,ls,grep` | 実行許可コマンド                              |
| `EXEC_TIMEOUT_SECONDS`  | `60`                         | run_skill_command の timeout       |
| `EXEC_MAX_OUTPUT_BYTES` | `65536`                      | stdout/stderr の最大バイト数                 |
| `MAX_FILE_BYTES`        | `65536`                      | read_skill_file で読む最大ファイルサイズ |
| `LOG_LEVEL`             | `INFO`                       | ログレベル (`DEBUG`/`INFO`/`WARN`/`ERROR`) |

### 8.3 スキルフィルタ（サーバごとのサブセット）

| 変数名                           | デフォルト | 説明                                                 |
| ----------------------------- | ----- | -------------------------------------------------- |
| `SKILLHUB_ENABLED_SKILLS`     | 空     | カンマ区切りの skill_name リスト。指定があれば、この中だけ有効。             |
| `SKILLHUB_ENABLED_CATEGORIES` | 空     | カンマ区切りの category。skill の category がいずれかに含まれる場合に有効。 |

* 有効判定の優先度例：

  1. `SKILLHUB_ENABLED_SKILLS` が指定されていれば **その名前に含まれるものだけ** 有効。
  2. 無指定なら `SKILLHUB_ENABLED_CATEGORIES` のいずれかに一致する skill を有効。
  3. 両方空なら **全 skill が有効**。

> これにより、「index は全スキル」＋「サーバ単位で有効スキルを絞る」が両立する。

---

## 9. バージョニングポリシー (skillhub-mcp)

* **現在バージョン:** `0.0.0`
* **serverInfo.version**（MCP initialize で返す）はこの semver を使う。

### 9.1 0.x 系の扱い

* 0.0.z / 0.1.z の間も、**Tool の引数/戻り値スキーマは原則として後方互換を維持**する。

  * 追加してよい変更:

    * Tool 戻り値に **optional フィールドを追加**。
    * 引数に **optional 引数**（デフォルト付き）を追加。
  * 禁止する変更:

    * 既存フィールドの削除 / 型変更。
    * 既存フィールドの意味を変える変更。
* 重大なスキーマ変更が必要になった場合は、`1.0.0` へのメジャーバンプで行う。

---

ここまでが **`skillhub-mcp v0.0.0` としての「実装に直行できるレベルのPRD」** です。

このまま PRD 本体として扱ってもらって大丈夫ですし、

* この仕様に沿って `server.py` の骨組み（設定ローダー / LanceDB インデクサ / 4つの MCP ツール実装 / stdio & HTTP 起動）
* あるいは `pyproject.toml` の `project.name = "skillhub-mcp"` やエントリポイント

を切っていけば、ほぼ迷いなく実装に落とせると思います。

もし次にやるなら、

* この PRD どおりの `src/skillhub_mcp/server.py` のスケルトンコード
* もしくは `search_skills` の実装サンプル（埋め込みあり / none 時 FTS の分岐）

まで一気に書ききる、でもいけます。
