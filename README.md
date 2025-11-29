# 📦 SkillSouko: All Your Agent Skills in One MCP Server

<div align="center">

🏭 **Your Agent Skills Warehouse** · *Skill + 倉庫 (Souko)* 📦

A centralized hub to install, organize, and distribute Agent Skills to any MCP client (Cursor, Copilot, Codex, etc.).

[![MCP](https://img.shields.io/badge/MCP-Enabled-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## What are Agent Skills?

[Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) are folders of instructions, scripts, and resources that AI agents load on demand. Instead of cramming everything into a system prompt, skills let agents search for and load only what they need.

🔄 **Compatible with Claude Agent Skills**:<br>
SkillSouko implements the [Anthropic Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) specification. Any skill that works with Claude Code works with SkillSouko—and vice versa. No changes needed.

**SkillSouko** brings Agent Skills to any MCP-compatible client (Cursor, GitHub Copilot, Codex, Claude Desktop, etc.) with full lifecycle management.

## Why SkillSouko?

| Need | SkillSouko Solution |
|------|-------------------|
| Use Agent Skills in Cursor/Copilot/Codex | MCP server or CLI delivers skills to any client |
| Easy skill installation | One command from GitHub or local |
| Manage all skills in one place | Single source, multiple clients |
| Filter skills per client | Categories, namespaces, skill IDs |
| Scale to 100+ skills | Full-text search with smart fallback |

```
┌─────────────────────────────────────────────┐
│  MCP Client (Cursor, Copilot, Codex, etc.)  │
└──────────────────────┬──────────────────────┘
                       │ MCP
              ┌────────▼────────┐
              │    SkillSouko   │
              │  search → load  │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │   Your Skills   │
              │ (GitHub, local) │
              └─────────────────┘
```

## Quick Start

### 1. Install CLI

```bash
pip install skillsouko
# or
uv tool install skillsouko
```

### 2. Add Skills

```bash
# Add a sample skill
skillsouko add hello-world

# Or add from GitHub
skillsouko add https://github.com/anthropics/skills
```

If you already have a skills directory (e.g., `.claude/skills/`), set `SKILLSOUKO_SKILLS_DIR` to point to it in step 3.

### 3. Add to Your MCP Client

> To customize environment variables, use manual configuration below instead of one-click install.

**Cursor** (one-click)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillsouko&config=eyJjb21tYW5kIjoidXYiLCJhcmdzIjpbInJ1biIsInNraWxsc291a28tbWNwIl0sImVudiI6eyJTS0lMTFNPVUtPX1NLSUxMU19ESVIiOiJ+Ly5za2lsbHNvdWtvL3NraWxscyJ9fQ==)

**VS Code / GitHub Copilot** (one-click)

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_MCP_Server-007ACC?logo=visualstudiocode)](https://insiders.vscode.dev/redirect/mcp/install?name=skillsouko&config=%7B%22command%22%3A%20%22uv%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22skillsouko-mcp%22%5D%2C%20%22env%22%3A%20%7B%22SKILLSOUKO_SKILLS_DIR%22%3A%20%22~/.skillsouko/skills%22%7D%7D)

**Kiro** (one-click)

[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillsouko&config=%7B%22command%22%3A%20%22uv%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22skillsouko-mcp%22%5D%2C%20%22env%22%3A%20%7B%22SKILLSOUKO_SKILLS_DIR%22%3A%20%22~/.skillsouko/skills%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D)


**CLI Agents**

```bash
# Claude Code
claude mcp add skillsouko -- uv run skillsouko-mcp

# Codex
codex mcp add skillsouko -- uv run skillsouko-mcp

# Gemini CLI
gemini mcp add skillsouko uv run skillsouko-mcp
```

**Other MCP Clients** (Windsurf, Cline, Roo Code, etc.)

Add to your client's MCP config file:

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

| Client | Config file |
|--------|-------------|
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Cline | VS Code settings or `.cline/mcp_settings.json` |
| Roo Code | `.roo/mcp.json` (project) or VS Code settings |

<details>
<summary>Claude Desktop</summary>

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

</details>

### 4. Use It

Ask your AI: *"Search for hello-world and run it"*

The agent will:
1. `search_skills("hello-world")` — find matching skills
2. `load_skill("hello-world")` — get instructions + path
3. Follow the instructions using its tools

## Key Features

### Deliver: MCP Server

Three tools for progressive skill loading:

| Tool | Purpose |
|------|---------|
| `search_skills(query)` | Find skills by task description |
| `load_skill(skill_id)` | Get full instructions and filesystem path |
| `read_skill_file(skill_id, path)` | Read templates and configs |

### Manage: CLI

Full lifecycle management from the command line:

```bash
skillsouko add <source>      # GitHub URL, local path, or built-in name
skillsouko list              # See installed skills
skillsouko search <query>    # Find skills by description
skillsouko show <id>         # View skill details
skillsouko lint [id]         # Validate skill files
skillsouko remove <id>       # Uninstall a skill
```

**GitHub Integration:**

```bash
# Anthropic official skills
skillsouko add https://github.com/anthropics/skills

# Developer essentials (git, code review, testing)
skillsouko add https://github.com/wshobson/agents/tree/main/plugins/developer-essentials/skills
```

**Discover more:** [Awesome Claude Skills](https://github.com/ComposioHQ/awesome-claude-skills) ・ [Kubernetes Operations](https://github.com/wshobson/agents/tree/main/plugins/kubernetes-operations/skills)

### Organize: Categories & Namespaces

Structure your skills and control what each client sees:

```yaml
# SKILL.md frontmatter
metadata:
  skillsouko:
    category: development
    tags: [testing, quality]
    alwaysApply: true  # Core Skills - always available
```

**Client-Based Skill Filtering:**

Expose different skills to different AI agents:

```json
{
  "mcpServers": {
    "skillsouko-development": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": { "SKILLSOUKO_ENABLED_CATEGORIES": "development,testing" }
    }
  }
}
```


```json
{
  "mcpServers": {
    "writing-skills": {
      "command": "uv",
      "args": ["run", "skillsouko-mcp"],
      "env": { "SKILLSOUKO_ENABLED_CATEGORIES": "writing,research" }
    }
  }
}
```

Filter options:
- `SKILLSOUKO_ENABLED_SKILLS` — Specific skill IDs
- `SKILLSOUKO_ENABLED_CATEGORIES` — By category
- `SKILLSOUKO_ENABLED_NAMESPACES` — By directory prefix
- `SKILLSOUKO_CORE_SKILLS_MODE` — Skills visible to agent without searching (`auto`/`explicit`/`none`)

### Scale: Smart Search

**Full-Text Search**

Works out of the box with no API keys. BM25-based search via Tantivy indexes skill names, descriptions, tags, and categories.

**Fallback Chain**: FTS → substring (always returns results)

### Design: Path-Based Execution

SkillSouko provides knowledge, not a runtime. Instead of executing code, it returns filesystem paths:

```python
# load_skill returns:
{
    "instructions": "How to extract text from PDFs...",
    "path": "/Users/me/.skillsouko/skills/pdf-extractor"
}
```

The agent executes scripts directly:

```bash
python {path}/scripts/extract.py input.pdf -o result.txt
```

**Context Engineering:** Executing code doesn't require reading code.

| Approach | Context Cost |
|----------|--------------|
| Read script → execute | ~2,000 tokens |
| Execute via path | ~20 tokens |

This keeps SkillSouko simple and secure—it's a warehouse, not a runtime.

[Design Philosophy →](guide/philosophy.md)

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLSOUKO_SKILLS_DIR` | Skills directory | `~/.skillsouko/skills` |

[Full Configuration Guide →](guide/configuration.md)

## Creating Skills

```markdown
---
name: my-skill
description: What this skill does
metadata:
  skillsouko:
    category: development
    tags: [example]
---
# My Skill

Instructions for the AI agent.
```

[Skill Authoring Guide →](guide/creating-skills.md)

## Learn More

- [Configuration Guide](guide/configuration.md) — Filtering, search options, multi-client setup
- [Creating Skills](guide/creating-skills.md) — SKILL.md format and best practices
- [CLI Reference](guide/cli.md) — Full command documentation
- [Design Philosophy](guide/philosophy.md) — Why skills work this way

## Development

```bash
git clone https://github.com/gotalab/skillsouko.git
cd skillsouko
uv sync
SKILLSOUKO_SKILLS_DIR=.agent/skills uv run skillsouko serve
```

## License

MIT
