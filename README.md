# SkillHub MCP

<div align="center">

**One Skills Hub for All MCP Clients**
(Cursor, Windsurf, Claude Desktop, GitHub Copilot, Kiro, etc.)

[![MCP](https://img.shields.io/badge/MCP-Enabled-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## Why SkillHub?

[Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) bring **progressive disclosure** to AI agents — expert knowledge loads only when needed. SkillHub brings this concept to the MCP ecosystem, designed for scale. Your existing Agent Skills (directories with `SKILL.md`) work as-is.

| When you want to... | SkillHub provides |
|---------------------|-------------------|
| **Use skills across all MCP clients** (Cursor, Windsurf, Copilot, Claude Code, etc.) | MCP-native access — works with any compatible client |
| **Scale to 100+ skills** without bloating system prompts (same issue as too many MCP tool descriptions) | Search API — agents discover and load only what they need |
| **Manage skills in one place** (Git repo, shared folder, anywhere) | Flexible storage — point `SKILLS_DIR` to any location |
| **Expose different skills to different agents** (dev tools for IDE, writing skills for chat) | Scoped instances — filter by category or skill name per MCP connection |

<br>

```
        IDEs                    Chat                    CLI
┌─────────────────┐     ┌───────────────┐     ┌─────────────────┐
│ Cursor, Windsurf│     │Claude Desktop │     │ Claude Code     │
│ Copilot, Kiro   │     │  Claude.ai    │     │ Codex, Gemini   │
│ Cline, etc.     │     │               │     │ CLI, etc.       │
└────────┬────────┘     └───────┬───────┘     └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │ MCP
                         ┌──────▼──────┐
                         │  SkillHub   │  search → load → path
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │ SKILLS_DIR  │  Git repo, local folder,
                         │  (anywhere) │  or shared drive
                         └─────────────┘
```

**Design Philosophy**: Context-efficient by design. Skills are *knowledge*, not execution environments — search what you need, load only when needed, execute via `path` without bloating context.

→ [Deep dive: docs/latest/SKILL_PHILOSOPHY.md](docs/latest/SKILL_PHILOSOPHY.md)

## Quick Start

### 1. Install to Your MCP Client

**Cursor** (one-click)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillhub&config=eyJjb21tYW5kIjogInV2IiwgImFyZ3MiOiBbInJ1biIsICJza2lsbGh1Yi1tY3AiXSwgImVudiI6IHsiU0tJTExTX0RJUiI6ICJ-Ly5za2lsbGh1Yi9za2lsbHMifX0=)

**Kiro** (one-click)

[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillhub&config=%7B%22command%22%3A%20%22uv%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22skillhub-mcp%22%5D%2C%20%22env%22%3A%20%7B%22SKILLS_DIR%22%3A%20%22~/.skillhub/skills%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D)

**Other Clients** (manual config)

Add to your MCP config file:
```json
{
  "mcpServers": {
    "skillhub": {
      "command": "uv",
      "args": ["run", "skillhub-mcp"],
      "env": { "SKILLS_DIR": "~/.skillhub/skills" }
    }
  }
}
```

Config locations:
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windsurf**: `~/.codeium/windsurf/mcp_config.json`
- **Claude Code**: `claude mcp add --env SKILLS_DIR=~/.skillhub/skills skillhub -- uv run skillhub-mcp`

### 2. Add Your First Skill

```bash
# Add a sample skill to get started
skillhub add hello-world

# Or add a template to create your own
skillhub add template
```

This creates skills in `~/.skillhub/skills/`. Edit the template or create your own:

```markdown
---
name: my-skill
description: What this skill does (used for search)
metadata:
  skillhub:
    category: development
    tags: [example]
---
# My Skill

Instructions for the AI agent go here.
```

### 3. Use It

1. Ask your AI: *"Search for my-skill"* → calls `search_skills`
2. AI loads full instructions → calls `load_skill`
3. AI follows the instructions using its tools

## Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SKILLS_DIR` | Path to skills directory | `~/.skillhub/skills` |
| `DB_PATH` | Path to LanceDB index | `~/.skillhub/indexes/default/` |
| `EMBEDDING_PROVIDER` | `none`, `openai`, or `gemini` | `none` |
| `SEARCH_LIMIT` | Max search results | `10` |

When `EMBEDDING_PROVIDER=none` (default), search uses Full-Text Search. Set to `openai` or `gemini` with the corresponding API key for vector search.

### GitHub sources
- Downloaded via GitHub tarball API (`/repos/{owner}/{repo}/tarball/{ref}`).
- Guardrails: max 1MB per file, 10MB total extracted; symlinks/hidden files are rejected.
- Private repos / higher rate limits: set `GITHUB_TOKEN`.

<details>
<summary>All Configuration Options</summary>

### Embedding (Vector Search)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Required when provider is `openai` | — |
| `GEMINI_API_KEY` | Required when provider is `gemini` | — |
| `EMBEDDING_MODEL` | OpenAI model | `text-embedding-3-small` |
| `GEMINI_EMBEDDING_MODEL` | Gemini model | `gemini-embedding-001` |

### Skill Filtering
| Variable | Description | Default |
| :--- | :--- | :--- |
| `SKILLHUB_ENABLED_SKILLS` | Comma-separated skill names to expose | all |
| `SKILLHUB_ENABLED_CATEGORIES` | Comma-separated categories to expose | all |

### Limits
| Variable | Description | Default |
| :--- | :--- | :--- |
| `EXEC_TIMEOUT_SECONDS` | Command timeout | `60` |
| `MAX_FILE_BYTES` | Max file read size | `65536` |

</details>

## Creating Skills

A skill is a directory with a `SKILL.md` file:

```
~/.skillhub/skills/my-skill/
├── SKILL.md          # Instructions (required)
├── scripts/          # Optional scripts
└── templates/        # Optional templates
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Short description for search
metadata:
  skillhub:
    category: development
    tags: [tag1, tag2]
    alwaysApply: false   # true = show in system prompt without searching
---
# Skill Title

Instructions for the AI agent.
Reference files like `scripts/main.py` - the agent will execute them using its terminal.
```

Skills with `alwaysApply: true` appear as "Core Skills" in the agent's system prompt and can be used without searching.

## MCP Tools

| Tool | Purpose |
| :--- | :--- |
| `search_skills(query)` | Find skills by description. Use `""` or `"*"` to list all. |
| `load_skill(skill_id)` | Get full instructions and directory path (supports `group/skill` ids). |
| `read_skill_file(skill_id, file_path)` | Read templates/configs into context. |

**Workflow**: `search_skills` → `load_skill` → execute scripts via terminal

## CLI

```bash
# Add skills
skillhub add hello-world                        # Built-in sample skill
skillhub add template                           # Built-in skill template
skillhub add ./my-skill/                        # Local directory (single skill)
skillhub add ./my-collection/ --keep-structure  # Multiple skills, keep namespace
skillhub add ./my-collection/ --namespace foo   # Multiple skills, custom namespace
skillhub add https://github.com/user/repo/tree/main/skills  # From GitHub

# List skills (tree view with namespaces)
skillhub list                    # All skills
skillhub list --category dev     # Filter by category
skillhub list --id-prefix group/ # Filter by namespace
skillhub list --json             # JSON output

# Validate skills
skillhub lint                    # Lint all skills
skillhub lint my-skill           # Lint specific skill by id

# Remove skills
skillhub remove my-skill         # By id (e.g., hello-world or group/skill)
skillhub remove my-skill --force # Skip confirmation

# Server
skillhub                         # Start MCP server
skillhub --reindex               # Force reindex on startup

# All commands support --dir to specify a custom skills directory
skillhub list --dir ./my-skills
skillhub add hello-world --dir ./my-skills
```

> **Note**: `skillhub` is an alias for `skillhub-mcp`. Both work identically.

## Development

```bash
git clone https://github.com/gota/skillhub-mcp.git
cd skillhub-mcp
uv sync
SKILLS_DIR=.agent/skills uv run skillhub-mcp
```

## License

MIT
