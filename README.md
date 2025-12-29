# ⚓ SkillPort

<div align="center">

**The SkillOps Toolkit for Agent Skills**

SkillOps = Validate, manage, and deliver skills at scale.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Enabled-green)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## Why SkillPort?

| When you... | SkillPort... |
|-------------|--------------|
| Use a coding agent without native skill support | Serves via MCP or CLI |
| Build your own AI agent | Provides MCP server, CLI, and Python library |
| Have 50+ skills and need the right one fast | Search-first loading ([Tool Search Tool](https://www.anthropic.com/engineering/advanced-tool-use) pattern) |
| Check skills before deployment | Validates against the spec in CI |
| Manage skill metadata programmatically | Provides `meta` commands |
| Find a skill on GitHub | Installs with `add <url>` |

Fully compatible with the [Agent Skills specification](https://agentskills.io/specification).

---

## Features

### Validate

Check skills against the [Agent Skills specification](https://agentskills.io/specification).

```bash
skillport validate                    # Validate all skills
skillport validate ./skills           # Validate specific directory
skillport validate --json             # CI-friendly JSON output
```

Catches missing fields, naming issues, and spec violations before they cause problems.

### Manage

Full lifecycle management from any source.

```bash
# Add from GitHub (shorthand)
skillport add anthropics/skills skills

# Add from GitHub (full URL)
skillport add https://github.com/anthropics/skills/tree/main/skills

# Add from local path or zip
skillport add ./my-skills
skillport add skills.zip

# Update, list, remove
skillport update                      # Update all from original sources
skillport list                        # See installed skills
skillport remove <skill-id>           # Uninstall
```

### Metadata

Update skill metadata without editing files manually. Useful for automation and keeping skills consistent across a team.

```bash
skillport meta get <skill> <key>      # Get metadata value
skillport meta set <skill> <key> <val> # Set metadata value
skillport meta unset <skill> <key>    # Remove metadata key
```

### Serve

MCP server for clients that don't natively support Agent Skills.

Inspired by Anthropic's [Tool Search Tool](https://www.anthropic.com/engineering/advanced-tool-use) pattern — search first, load on demand:

| Tool | Purpose |
|------|---------|
| `search_skills(query)` | Find skills by description (full-text search) |
| `load_skill(skill_id)` | Get full instructions + path |

**Why search matters:** With 50+ skills, loading all upfront consumes context and hurts accuracy. SkillPort loads metadata only (~100 tokens/skill), then full instructions on demand.

Works with Cursor, Copilot, Windsurf, Cline, Codex, and any MCP-compatible client.

---

## Quick Start

### Install

```bash
uv tool install skillport
# or: pip install skillport
```

### Add Skills

```bash
# Add from GitHub
skillport add anthropics/skills skills

# Or use a custom skills directory
skillport --skills-dir .claude/skills add anthropics/skills skills
```

### Validate

```bash
skillport validate
# ✓ All 5 skill(s) pass validation
```

---

## Connect to Agents

Choose how to deliver skills to your AI agents:

| Mode | Best for | Setup |
|------|----------|-------|
| [**CLI Mode**](#cli-mode) | Agents with shell access (Cursor, Windsurf, Codex, etc.) | Per-project |
| [**MCP Mode**](#mcp-mode) | MCP-compatible clients, multi-project | One-time |

### CLI Mode

For agents that can run shell commands. No MCP configuration required.

```bash
skillport init                        # Initialize project
skillport doc                         # Generate AGENTS.md with skill table
skillport show <id>                   # Load full instructions for a skill
```

How it works:
1. `skillport doc` generates a skill table in AGENTS.md
2. The agent reads AGENTS.md to discover available skills
3. When needed, the agent runs `skillport show <id>` to load full instructions

### MCP Mode

For MCP-compatible clients. Install the server:

```bash
uv tool install skillport-mcp
```

Add to your client's config:

```json
{
  "mcpServers": {
    "skillport": {
      "command": "uvx",
      "args": ["skillport-mcp"],
      "env": { "SKILLPORT_SKILLS_DIR": "~/.skillport/skills" }
    }
  }
}
```

<details>
<summary>One-click install for popular clients</summary>

**Cursor**

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillport&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJza2lsbHBvcnQtbWNwIl0sImVudiI6eyJTS0lMTFBPUlRfU0tJTExTX0RJUiI6In4vLnNraWxscG9ydC9za2lsbHMifX0=)

**VS Code / GitHub Copilot**

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_MCP_Server-007ACC?logo=visualstudiocode)](https://insiders.vscode.dev/redirect/mcp/install?name=skillport&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22skillport-mcp%22%5D%2C%22env%22%3A%7B%22SKILLPORT_SKILLS_DIR%22%3A%22~/.skillport/skills%22%7D%7D)

**Kiro**

[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillport&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22skillport-mcp%22%5D%2C%22env%22%3A%7B%22SKILLPORT_SKILLS_DIR%22%3A%22~/.skillport/skills%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D)

**CLI Agents**

```bash
# Codex
codex mcp add skillport -- uvx skillport-mcp

# Claude Code
claude mcp add skillport -- uvx skillport-mcp
```

</details>

---

## Organization

Organize skills with categories and tags. Works with both CLI and MCP modes.

### Categories & Tags

Use metadata to organize and filter skills:

```yaml
# SKILL.md frontmatter
metadata:
  skillport:
    category: development
    tags: [testing, quality]
    alwaysApply: true  # Always available (Core Skills)
```

### Per-Client Filtering

Expose different skills to different agents:

```json
{
  "mcpServers": {
    "skillport-dev": {
      "command": "uvx",
      "args": ["skillport-mcp"],
      "env": { "SKILLPORT_ENABLED_CATEGORIES": "development,testing" }
    },
    "skillport-writing": {
      "command": "uvx",
      "args": ["skillport-mcp"],
      "env": { "SKILLPORT_ENABLED_CATEGORIES": "writing,research" }
    }
  }
}
```

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_SKILLS_DIR` | Skills directory | `~/.skillport/skills` |
| `SKILLPORT_ENABLED_CATEGORIES` | Filter by category | all |
| `SKILLPORT_ENABLED_SKILLS` | Filter by skill ID | all |
| `SKILLPORT_ENABLED_NAMESPACES` | Filter by namespace | all |
| `SKILLPORT_CORE_SKILLS_MODE` | Core Skills behavior (`auto`/`explicit`/`none`) | `auto` |

---

## Creating Skills

Create a `SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill
description: What this skill does
metadata:
  skillport:
    category: development
    tags: [example]
---
# My Skill

Instructions for the AI agent.
```

See [Creating Skills Guide](guide/creating-skills.md) for best practices.

---

## Skill Sources

| Source | Features | Target | URL |
|--------|----------|--------|-----|
| Anthropic Official | Document skills (docx, pdf, pptx, xlsx), design, MCP builder | All users | [GitHub](https://github.com/anthropics/skills/tree/main/skills) |
| Awesome Claude Skills | Curated community collection, 2.5k+ stars | Discovery | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills) |
| Hugging Face Skills | Dataset creation, model evaluation, LLM training, paper publishing | ML/AI engineers | [GitHub](https://github.com/huggingface/skills) |
| Claude Scientific Skills | 128+ scientific skills (bio, chem, ML), 26+ databases | Researchers | [GitHub](https://github.com/K-Dense-AI/claude-scientific-skills) |
| ClaudeKit Skills | 30+ skills, auth, multimodal, problem-solving frameworks | Full-stack devs | [GitHub](https://github.com/mrgoonie/claudekit-skills) |
| Superpowers | TDD, debugging, parallel agents, code review workflows | Quality-focused devs | [GitHub](https://github.com/obra/superpowers) |
| Kubernetes Operations | K8s deployment, monitoring, troubleshooting | DevOps/SRE | [GitHub](https://github.com/wshobson/agents/tree/main/plugins/kubernetes-operations/skills) |

---

## Learn More

- [Configuration Guide](guide/configuration.md)
- [Creating Skills](guide/creating-skills.md)
- [CLI Reference](guide/cli.md)
- [Design Philosophy](guide/philosophy.md)

---

## Development

> **Status:** Work in progress. APIs may change.

```bash
git clone https://github.com/gotalab/skillport.git
cd skillport
uv sync

# Run MCP server
SKILLPORT_SKILLS_DIR=.skills uv run skillport-mcp

# Run CLI
uv run skillport --help

# Run tests
uv run pytest
```

---

## License

MIT
