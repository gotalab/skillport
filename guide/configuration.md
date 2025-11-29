# Configuration

This guide covers all configuration options for SkillSouko.

## Environment Variables

All environment variables are prefixed with `SKILLSOUKO_`. The prefix is optional for common variables like `SKILLS_DIR`.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLSOUKO_SKILLS_DIR` | Path to skills directory | `~/.skillsouko/skills` |
| `SKILLSOUKO_DB_PATH` | Path to LanceDB index | `~/.skillsouko/indexes/default/` |

### Search

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLSOUKO_SEARCH_LIMIT` | Maximum search results | `10` |
| `SKILLSOUKO_SEARCH_THRESHOLD` | Minimum score threshold (0-1) | `0.2` |

#### Full-Text Search

SkillSouko uses BM25-based full-text search via Tantivy:

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
| `SKILLSOUKO_EXEC_TIMEOUT_SECONDS` | Command execution timeout | `60` |
| `SKILLSOUKO_MAX_FILE_BYTES` | Max file read size | `65536` |

## Client-Based Skill Filtering

Expose different skills to different AI agents by configuring filter environment variables.

### Skill Filters

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLSOUKO_ENABLED_SKILLS` | Comma-separated skill IDs | all |
| `SKILLSOUKO_ENABLED_CATEGORIES` | Comma-separated categories | all |
| `SKILLSOUKO_ENABLED_NAMESPACES` | Comma-separated namespaces | all |

### Core Skills Control

Control which skills appear as "Core Skills" (always available without searching) per client.

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLSOUKO_CORE_SKILLS_MODE` | `auto`, `explicit`, or `none` | `auto` |
| `SKILLSOUKO_CORE_SKILLS` | Comma-separated skill IDs (for `explicit` mode) | none |

**Modes:**

| Mode | Behavior |
|------|----------|
| `auto` | Skills with `alwaysApply: true` become Core Skills (default) |
| `explicit` | Only skills in `SKILLSOUKO_CORE_SKILLS` become Core Skills |
| `none` | Disable Core Skills entirely |

**Examples:**

```bash
# Use only specific skills as Core Skills (ignore alwaysApply in SKILL.md)
export SKILLSOUKO_CORE_SKILLS_MODE=explicit
export SKILLSOUKO_CORE_SKILLS=team-standards,code-style

# Disable Core Skills entirely (lighter context)
export SKILLSOUKO_CORE_SKILLS_MODE=none
```

### Filter Priority

Filters are evaluated in order of specificity:

1. If `SKILLSOUKO_ENABLED_SKILLS` is set → only those exact skill IDs
2. Otherwise, if `SKILLSOUKO_ENABLED_NAMESPACES` is set → only matching prefixes
3. Otherwise, if `SKILLSOUKO_ENABLED_CATEGORIES` is set → only matching categories
4. If none are set → all skills available

### Examples

**Filter by category:**
```bash
export SKILLSOUKO_ENABLED_CATEGORIES=development,testing
```

**Filter by specific skills:**
```bash
export SKILLSOUKO_ENABLED_SKILLS=hello-world,code-review,my-namespace/my-skill
```

**Filter by namespace:**
```bash
export SKILLSOUKO_ENABLED_NAMESPACES=my-tools,team-skills
```

## Per-Client Setup

Run different SkillSouko configurations for different AI agents.

### Using Existing Claude Code Skills

If you already have skills in `.claude/skills/`, point SkillSouko to that directory:

```json
{
  "mcpServers": {
    "skillsouko": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": {
        "SKILLSOUKO_SKILLS_DIR": "/absolute/path/to/project/.claude/skills"
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
    "skillsouko-dev": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": {
        "SKILLSOUKO_SKILLS_DIR": "~/.skillsouko/skills",
        "SKILLSOUKO_ENABLED_CATEGORIES": "development,testing"
      }
    },
    "skillsouko-writing": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": {
        "SKILLSOUKO_SKILLS_DIR": "~/.skillsouko/skills",
        "SKILLSOUKO_ENABLED_CATEGORIES": "writing,research"
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
skillsouko add https://github.com/user/repo

# Specific directory (branch/tag)
skillsouko add https://github.com/user/repo/tree/main/skills/my-skill

# Specific directory (commit)
skillsouko add https://github.com/user/repo/tree/abc123/path/to/skill
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

SkillSouko automatically reindexes when:
- Skills directory content changes (hash-based detection)
- Schema version changes
- Embedding provider changes

### Manual Reindexing

```bash
# Force reindex on server start
skillsouko serve --reindex

# Skip auto-reindex check
skillsouko serve --skip-auto-reindex
```

### Index Location

| SKILLS_DIR | Index Location |
|------------|----------------|
| Default (`~/.skillsouko/skills`) | `~/.skillsouko/indexes/default/` |
| Custom path | `~/.skillsouko/indexes/{hash}/` |

## MCP Client Configuration

### Cursor

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillsouko&config=eyJjb21tYW5kIjoidXYiLCJhcmdzIjpbInJ1biIsInNraWxscG9kLW1jcCJdLCJlbnYiOnsiU0tJTExQT0RfU0tJTExTX0RJUiI6In4vLnNraWxscG9kL3NraWxscyJ9fQ==)

Or manually add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "skillsouko": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": { "SKILLSOUKO_SKILLS_DIR": "~/.skillsouko/skills" }
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skillsouko": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": { "SKILLSOUKO_SKILLS_DIR": "~/.skillsouko/skills" }
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "skillsouko": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": { "SKILLSOUKO_SKILLS_DIR": "~/.skillsouko/skills" }
    }
  }
}
```

### Claude Code

```bash
claude mcp add skillsouko -- uv run skillsouko-mcp
# With custom skills directory:
claude mcp add --env SKILLSOUKO_SKILLS_DIR=~/.skillsouko/skills skillsouko -- uv run skillsouko-mcp
```

### Kiro

[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillsouko&config=%7B%22command%22%3A%20%22uv%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22skillsouko-mcp%22%5D%2C%20%22env%22%3A%20%7B%22SKILLSOUKO_SKILLS_DIR%22%3A%20%22~/.skillsouko/skills%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D)

## See Also

- [CLI Reference](cli.md) — Command documentation
- [Creating Skills](creating-skills.md) — SKILL.md format
- [Design Philosophy](philosophy.md) — Why things work this way
