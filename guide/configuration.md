# Configuration

This guide covers all configuration options for SkillPort.

## Table of Contents

- [Project Configuration](#project-configuration) - `.skillportrc`, `pyproject.toml`
- [Environment Variables](#environment-variables) - Core, Search, Embeddings, Execution
- [Client-Based Skill Filtering](#client-based-skill-filtering) - Filter skills per agent
- [Per-Client Setup](#per-client-setup) - Different configs for different agents
- [GitHub Integration](#github-integration) - Authentication, URL formats
- [Index Management](#index-management) - Reindexing, index location
- [MCP Client Configuration](#mcp-client-configuration) - Cursor, Claude Desktop, Windsurf, etc.

## Project Configuration

For CLI mode, create a `.skillportrc` file (or use `skillport init`) to configure project-specific settings.

### .skillportrc

```yaml
# SkillPort Configuration
# See: https://github.com/gotalab/skillport

skills_dir: .agent/skills
instructions:
  - AGENTS.md
  - GEMINI.md
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skills_dir` | path | Yes | Skills directory (relative to project root or absolute) |
| `instructions` | path[] | No | Instruction files to update with `skillport sync --all` |

### pyproject.toml (Alternative)

For Python projects, you can use `pyproject.toml` instead:

```toml
[tool.skillport]
skills_dir = ".agent/skills"
instructions = ["AGENTS.md", "GEMINI.md"]
```

### Resolution Order (CLI)

CLI commands resolve `skills_dir` / `db_path` in this order:

| Priority | Source | Description |
|----------|--------|-------------|
| 1 | CLI flags | `--skills-dir`, `--db-path` |
| 2 | Environment variables | `SKILLPORT_SKILLS_DIR`, `SKILLPORT_DB_PATH` |
| 3 | `.skillportrc` | Project config (YAML) |
| 4 | `pyproject.toml` | `[tool.skillport]` section |
| 5 | Default | `~/.skillport/skills`, `~/.skillport/indexes/default/skills.lancedb` |

> **Note:** MCP server does not read project config files. Use environment variables in MCP client configuration instead.

## Environment Variables

All environment variables are prefixed with `SKILLPORT_`.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_SKILLS_DIR` | Path to skills directory | `~/.skillport/skills` |
| `SKILLPORT_DB_PATH` | Path to LanceDB index | `~/.skillport/indexes/default/skills.lancedb` |
| `SKILLPORT_META_DIR` | Directory for metadata (origins, etc.) | Auto-derived from `DB_PATH` |
| `SKILLPORT_AUTO_REINDEX` | Enable/disable automatic reindexing | `true` (accepts `0`, `false`, `no`, `off` to disable) |
| `SKILLPORT_LOG_LEVEL` | Log level (DEBUG/INFO/WARN/ERROR) | none |

### Search

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_SEARCH_LIMIT` | Maximum search results | `10` |
| `SKILLPORT_SEARCH_THRESHOLD` | Minimum score threshold (0-1) | `0.2` |

### Embeddings (Optional)

Vector search is optional. By default, SkillPort uses full-text search only.

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_EMBEDDING_PROVIDER` | Embedding provider (`none` or `openai`) | `none` |
| `OPENAI_API_KEY` | OpenAI API key (required when provider is `openai`) | none |
| `OPENAI_EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |

#### Full-Text Search

SkillPort uses BM25-based full-text search via Tantivy:

- **Fast** — no external API calls
- **Private** — all data stays local
- **Reliable** — no API keys needed

#### Fallback Chain

Search always returns results through a fallback chain:

1. **FTS (BM25)** — keyword matching
2. **Substring match** — last resort

### Execution Limits

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_EXEC_TIMEOUT_SECONDS` | Command execution timeout | `60` |
| `SKILLPORT_MAX_FILE_BYTES` | Max file read size | `65536` |
| `SKILLPORT_ALLOWED_COMMANDS` | Allowlist for executable commands | `python3,python,uv,node,bash,sh,cat,ls,grep` |

## Client-Based Skill Filtering

Expose different skills to different AI agents by configuring filter environment variables.

### Skill Filters

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_ENABLED_SKILLS` | Comma-separated skill IDs | all |
| `SKILLPORT_ENABLED_CATEGORIES` | Comma-separated categories | all |
| `SKILLPORT_ENABLED_NAMESPACES` | Comma-separated namespaces | all |

### Core Skills Control

Control which skills appear as "Core Skills" (always available without searching) per client.

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_CORE_SKILLS_MODE` | `auto`, `explicit`, or `none` | `auto` |
| `SKILLPORT_CORE_SKILLS` | Comma-separated skill IDs (for `explicit` mode) | none |

**Modes:**

| Mode | Behavior |
|------|----------|
| `auto` | Skills with `alwaysApply: true` become Core Skills (default) |
| `explicit` | Only skills in `SKILLPORT_CORE_SKILLS` become Core Skills |
| `none` | Disable Core Skills entirely |

**Examples:**

```bash
# Use only specific skills as Core Skills (ignore alwaysApply in SKILL.md)
export SKILLPORT_CORE_SKILLS_MODE=explicit
export SKILLPORT_CORE_SKILLS=team-standards,code-style

# Disable Core Skills entirely (lighter context)
export SKILLPORT_CORE_SKILLS_MODE=none
```

### Filter Priority

Filters are evaluated in order of specificity:

1. If `SKILLPORT_ENABLED_SKILLS` is set → only those exact skill IDs
2. Otherwise, if `SKILLPORT_ENABLED_NAMESPACES` is set → only matching prefixes
3. Otherwise, if `SKILLPORT_ENABLED_CATEGORIES` is set → only matching categories
4. If none are set → all skills available

### Examples

**Filter by category:**
```bash
export SKILLPORT_ENABLED_CATEGORIES=development,testing
```

**Filter by specific skills:**
```bash
export SKILLPORT_ENABLED_SKILLS=hello-world,code-review,my-namespace/my-skill
```

**Filter by namespace:**
```bash
export SKILLPORT_ENABLED_NAMESPACES=my-tools,team-skills
```

## Per-Client Setup

Run different SkillPort configurations for different AI agents.

### Using Existing Claude Code Skills

If you already have skills in `.claude/skills/`, point SkillPort to that directory:

```json
{
  "mcpServers": {
    "skillport": {
      "command": "uvx",
      "args": ["skillport"],
      "env": {
        "SKILLPORT_SKILLS_DIR": "/absolute/path/to/project/.claude/skills"
      }
    }
  }
}
```

> **Note:** Use absolute paths for reliability across different MCP clients.

This lets you use the same skills across Claude Code, Cursor, Copilot, and other MCP clients.

### Different Skills for Different Agents

Give each AI agent a different view of the same skill repository:

```json
{
  "mcpServers": {
    "skillport-dev": {
      "command": "uvx",
      "args": ["skillport"],
      "env": {
        "SKILLPORT_SKILLS_DIR": "~/.skillport/skills",
        "SKILLPORT_ENABLED_CATEGORIES": "development,testing"
      }
    },
    "skillport-writing": {
      "command": "uvx",
      "args": ["skillport"],
      "env": {
        "SKILLPORT_SKILLS_DIR": "~/.skillport/skills",
        "SKILLPORT_ENABLED_CATEGORIES": "writing,research"
      }
    }
  }
}
```

## GitHub Integration

### Authentication

Set `GITHUB_TOKEN` for:
- Private repository access
- Higher rate limits (5,000 req/hour vs 60 req/hour)

```bash
export GITHUB_TOKEN=ghp_xxxxx
```

### Supported URL Formats

```bash
# Repository root
skillport add https://github.com/user/repo

# Specific directory (branch/tag)
skillport add https://github.com/user/repo/tree/main/skills/my-skill

# Specific directory (commit)
skillport add https://github.com/user/repo/tree/abc123/path/to/skill
```

### Security Limits

| Limit | Value |
|-------|-------|
| Max file size | 1 MB |
| Max total extracted | 10 MB |
| Symlinks | Rejected |
| Hidden files | Rejected |

## Index Management

### Automatic Reindexing

SkillPort automatically reindexes when:
- Skills directory content changes (hash-based detection)
- Schema version changes
- Embedding provider changes

### Manual Reindexing

```bash
# Force reindex on server start
skillport serve --reindex

# Skip auto-reindex check
skillport serve --skip-auto-reindex
```

### Index Location

| SKILLS_DIR | Index Location |
|------------|----------------|
| Default (`~/.skillport/skills`) | `~/.skillport/indexes/default/skills.lancedb` |
| Custom path | `~/.skillport/indexes/{hash}/skills.lancedb` |

The `{hash}` is the first 10 characters of the SHA1 hash of the custom skills directory path.

## MCP Client Configuration

### Cursor

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillport&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJza2lsbHBvcnQiXSwiZW52Ijp7IlNLSUxMUE9SVF9TS0lMTFNfRElSIjoifi8uc2tpbGxwb3J0L3NraWxscyJ9fQ==)

Or manually add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "skillport": {
      "command": "uvx",
      "args": ["skillport"],
      "env": { "SKILLPORT_SKILLS_DIR": "~/.skillport/skills" }
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skillport": {
      "command": "uvx",
      "args": ["skillport"],
      "env": { "SKILLPORT_SKILLS_DIR": "~/.skillport/skills" }
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "skillport": {
      "command": "uvx",
      "args": ["skillport"],
      "env": { "SKILLPORT_SKILLS_DIR": "~/.skillport/skills" }
    }
  }
}
```

### Claude Code

```bash
claude mcp add skillport -- uvx skillport

# With custom skills directory:
claude mcp add skillport --env SKILLPORT_SKILLS_DIR=~/.skillport/skills -- uvx skillport
```

### Kiro

[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillport&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22skillport%22%5D%2C%22env%22%3A%7B%22SKILLPORT_SKILLS_DIR%22%3A%22~/.skillport/skills%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D)

## See Also

- [CLI Reference](cli.md) — Command documentation
- [Creating Skills](creating-skills.md) — SKILL.md format
- [Design Philosophy](philosophy.md) — Why things work this way
