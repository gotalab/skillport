# ⚓ SkillPort

<div align="center">

🚢 **All Your Agent Skills in One Place** - *Manage once, serve anywhere* ⚓

Agent Skills → Cursor · Copilot · Codex & more - via CLI or MCP

[![MCP](https://img.shields.io/badge/MCP-Enabled-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## Why SkillPort?

Claude Agent Skills are great - but they only work in Claude. What about Cursor, Copilot, Codex? With dozens of skills loaded upfront, there's less context and agent performance suffers.

**Context Engineering for Expert Knowledge** - SkillPort brings expertise into context-only when needed.

| When you... | SkillPort helps by... | |
|-------------|----------------------|-|
| Switching to Cursor with 20+ Agent skills | Add one line to config - all skills work instantly | [MCP Server →](#deliver-mcp-server) |
| Team using Cursor, Copilot, and Codex | Share one folder, filter by category per tool | [Organize →](#organize-categories--namespaces) |
| 50+ skills, "which one was for PR reviews?" | Search by keyword - finds it in milliseconds | [Scale →](#scale-progressive-disclosure) |
| Long debugging session, context running low | Skills load on-demand - not all upfront | [Scale →](#scale-progressive-disclosure) |
| Found an awesome skill on GitHub | `skillport add <url>` - ready to use in seconds | [CLI →](#manage-cli) |
| Don't want to set up MCP | CLI works standalone - `init`, `add`, `doc` to AGENTS.md | [CLI Mode →](#cli-mode) |

<br>

🔄 **Compatible with [Claude Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview)** - Write skills once, use everywhere. Skills that work with Claude Code work with SkillPort, and vice versa.

<!-- DEMO_GIF: `skillport add` → use in Cursor -->

<!-- ```
        ┌─────────┐ ┌─────────┐ ┌─────────┐
        │  Cursor │ │ Copilot │ │  Codex  │   MCP Clients
        └────┬────┘ └────┬────┘ └────┬────┘
             │           │           │
             └───────────┼───────────┘
                         │ MCP
                ┌────────▼────────┐
                │    SkillPort    │◄──── CLI (non-MCP agents)
                │ filter per agent│
                └────────┬────────┘
                         │
                ┌────────▼────────┐
                │ Skills Library  │
                │ (single source) │
                └─────────────────┘
``` -->

## Quick Start (5 min)

Choose your setup:

| Mode | Best for | Per-project setup |
|------|----------|-------------------|
| [**MCP Mode**](#mcp-mode) | Multi-project, per-client filtering | Not required |
| [**CLI Mode**](#cli-mode) | Quick Setup, single project | Required (`skillport init`) |

> **Tip:** Start with MCP Mode for the full experience. CLI Mode is simpler but requires setup in each project.

---

### MCP Mode

### 1. Install

> **Skip this step** if you only want to serve an existing skills directory via MCP.

Install to manage skills and use them without MCP:

```bash
uv tool install skillport
# or: pip install skillport

# Update to latest version
uv tool upgrade skillport
```

Enables `add`, `update`, `remove`, `lint`, `search`, `show`, and `doc` (generate AGENTS.md for non-MCP agents).

### 2. Add Skills

> **Skip this step** if you already have skills (e.g., in `.claude/skills/`). Just point `SKILLPORT_SKILLS_DIR` to it in step 3.

```bash
# Add a sample skill
skillport add hello-world

# Or add from GitHub
skillport add https://github.com/anthropics/skills/tree/main/skills

# Or add from GitHub with custom skills directory (Claude Code, Codex)
skillport --skills-dir .claude/skills add https://github.com/anthropics/skills/tree/main/skills
skillport --skills-dir ~/.codex/skills add https://github.com/anthropics/skills/tree/main/skills/frontend-design
```

### 3. Add to Your MCP Client

> To customize environment variables, use manual configuration below instead of one-click install.

**Cursor** (one-click)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillport&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJza2lsbHBvcnQiXSwiZW52Ijp7IlNLSUxMUE9SVF9TS0lMTFNfRElSIjoifi8uc2tpbGxwb3J0L3NraWxscyJ9fQ==)

**VS Code / GitHub Copilot** (one-click)

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_MCP_Server-007ACC?logo=visualstudiocode)](https://insiders.vscode.dev/redirect/mcp/install?name=skillport&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22skillport%22%5D%2C%22env%22%3A%7B%22SKILLPORT_SKILLS_DIR%22%3A%22~/.skillport/skills%22%7D%7D)

**Kiro** (one-click)

[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillport&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22skillport%22%5D%2C%22env%22%3A%7B%22SKILLPORT_SKILLS_DIR%22%3A%22~/.skillport/skills%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D)

**CLI Agents**

```bash
# Codex
codex mcp add skillport -- uvx skillport

# With custom skills in the project directory
codex mcp add skillport --env SKILLPORT_SKILLS_DIR=./.agent/skills -- uvx skillport

# Claude Code
claude mcp add skillport -- uvx skillport

# With custom skills directory
claude mcp add skillport --env SKILLPORT_SKILLS_DIR=~/.claude/skills -- uvx skillport
```

**Other MCP Clients** (Windsurf, Cline, Roo Code, Antigravity, etc.)

Add to your client's MCP config file:

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

| Client | Config file |
|--------|-------------|
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Cline | VS Code settings or `.cline/mcp_settings.json` |
| Roo Code | `.roo/mcp.json` (project) or VS Code settings |

<details>
<summary>Claude Desktop (Not Recommended, Use the official Agent Skills)</summary>

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

</details>

### 4. Use It

Ask your AI: *"Search for hello-world and run it"*

The agent will:
1. `search_skills("hello-world")` - find matching skills
2. `load_skill("hello-world")` - get instructions + path
3. Follow the instructions using its tools

---

### CLI Mode

**For:** Coding agents with shell commands (Cursor, Windsurf, Cline, Copilot, Codex, etc.)

Skills are documented in AGENTS.md and load via `skillport show`. No MCP configuration needed.

```bash
# 1. Install
uv tool install skillport

# 2. Initialize your project (in your project directory)
skillport init
# → Select skills directory and instruction files interactively
# → Creates .skillportrc, generates skills to AGENTS.md

# 3. Add skills (uses skills_dir from .skillportrc)
skillport add hello-world
skillport add https://github.com/anthropics/skills/tree/main/skills
skillport add https://github.com/anthropics/skills/tree/main/skills/frontend-design
```

**How it works:** Your agent reads the skills table in AGENTS.md, then runs `skillport show <id>` to load full instructions.

> **Note:** CLI mode requires `skillport init` in each project. Skills are added to the directory configured in `.skillportrc`. For multi-project use, consider [MCP Mode](#mcp-mode).


## Key Features

### Deliver: MCP Server

Tools for progressive skill loading:

| Tool | Transport | Purpose |
|------|-----------|---------|
| `search_skills(query)` | stdio, HTTP | Find skills by task description |
| `load_skill(skill_id)` | stdio, HTTP | Get full instructions and filesystem path |
| `read_skill_file(skill_id, file_path)` | HTTP only | Read files (experimental) |

> **stdio (default):** The `path` from `load_skill` is accessible in the agent's execution environment-agents can read files and run scripts directly.
>
> **Streamable HTTP (experimental):** For remote agents without filesystem access. Adds `read_skill_file` but is not fully tested yet.

### Manage: CLI

**Project Setup:**

```bash
skillport init              # Initialize project (.skillportrc, AGENTS.md)
skillport doc               # Update AGENTS.md when skills change
skillport doc --all         # Update all instruction files in .skillportrc
```

**Skill Management:**

```bash
skillport add <source>      # GitHub URL, local path, zip file, or built-in name
skillport update [id]       # Update skills from original sources
skillport list              # See installed skills
skillport remove <id>       # Uninstall a skill
skillport lint [id]         # Validate skill files

# Override paths per run (CLI > env > default)
skillport --skills-dir ./skills add hello-world
# Place global flags before the subcommand (e.g., skillport --skills-dir ... add ...)
```

**Search & Load:**

```bash
skillport search <query>    # Find skills by description
skillport show <id>         # View skill details and instructions
```

**Install from GitHub:**

One command to install skills from any GitHub URL-no cloning required. Supports branches and subdirectories:

```bash
# Anthropic official skills
skillport add https://github.com/anthropics/skills/tree/main/skills

# Specific path in a repo
skillport add https://github.com/wshobson/agents/tree/main/plugins/developer-essentials/skills
```

**Discover more:**

| Skills | Features | Target | URL |
|--------|----------|--------|-----|
| Anthropic Official | Document skills (docx, pdf, pptx, xlsx), design, MCP builder | All users | [GitHub](https://github.com/anthropics/skills/tree/main/skills) |
| Awesome Claude Skills | Curated community collection, 2.5k+ stars | Discovery | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills) |
| Hugging Face Skills | Dataset creation, model evaluation, LLM training, paper publishing | ML/AI engineers | [GitHub](https://github.com/huggingface/skills) |
| Claude Scientific Skills | 128+ scientific skills (bio, chem, ML), 26+ databases | Researchers | [GitHub](https://github.com/K-Dense-AI/claude-scientific-skills) |
| ClaudeKit Skills | 30+ skills, auth, multimodal, problem-solving frameworks | Full-stack devs | [GitHub](https://github.com/mrgoonie/claudekit-skills) |
| Superpowers | TDD, debugging, parallel agents, code review workflows | Quality-focused devs | [GitHub](https://github.com/obra/superpowers) |
| Kubernetes Operations | K8s deployment, monitoring, troubleshooting | DevOps/SRE | [GitHub](https://github.com/wshobson/agents/tree/main/plugins/kubernetes-operations/skills) |
| Notion Skills | Meeting notes, research docs, knowledge capture | Notion users | [GitHub](https://github.com/gotalab/skillport/tree/main/.agent/skills/notion-skills) |

### Organize: Categories & Namespaces

Use `metadata.skillport` to:

- **Search** - `category` and `tags` improve discoverability
- **Filtering** - Control which skills each client sees
- **Core Skills** - `alwaysApply: true` for always-available skills

```yaml
# SKILL.md frontmatter
metadata:
  skillport:
    category: development
    tags: [testing, quality]
    alwaysApply: true  # Core Skills - always available
```

**Client-Based Skill Filtering:**

Expose different skills to different AI agents:

```json
{
  "mcpServers": {
    "skillport-development": {
      "command": "uvx",
      "args": ["skillport"],
      "env": { "SKILLPORT_ENABLED_CATEGORIES": "development,testing" }
    }
  }
}
```


```json
{
  "mcpServers": {
    "writing-skills": {
      "command": "uvx",
      "args": ["skillport"],
      "env": { "SKILLPORT_ENABLED_CATEGORIES": "writing,research" }
    }
  }
}
```

Filter options:
- `SKILLPORT_ENABLED_SKILLS` - Specific skill IDs
- `SKILLPORT_ENABLED_CATEGORIES` - By category
- `SKILLPORT_ENABLED_NAMESPACES` - By directory prefix
- `SKILLPORT_CORE_SKILLS_MODE` - Skills visible to agent without searching (`auto`/`explicit`/`none`)

### Scale: Progressive Disclosure

**The Problem:**

```
System Prompt (every conversation):
├── Company guidelines (2,000 tokens)
├── Coding standards (3,000 tokens)
├── Review checklist (1,500 tokens)
├── 50 more instructions...
└── Total: 30,000+ tokens before you say "hello"
```

**The Solution:** Skills load progressively - metadata first, full instructions on demand:

| Stage | Tokens | When |
|-------|--------|------|
| Metadata | ~100/skill | Always (searchable) |
| Instructions | ~5,000 | On `load_skill()` |

**100 skills = ~15K tokens** (vs 300K+ if all loaded upfront)

SkillPort enhances this with:
- **BM25 search** - Find the right skill without loading all metadata
- **Per-client filtering** - Expose only relevant skills to each agent
- **Fallback chain** - FTS → substring (always returns results)

### Design: Path-Based Execution

SkillPort provides knowledge, not a runtime. Instead of executing code, it returns filesystem paths:

```python
# load_skill returns:
{
    "instructions": "How to extract text from PDFs...",
    "path": "/Users/me/.skillport/skills/pdf-extractor"
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

This keeps SkillPort simple and secure-it's a harbor, not a runtime.

[Design Philosophy →](https://github.com/gotalab/skillport/blob/main/guide/philosophy.md)

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLPORT_SKILLS_DIR` | Skills directory | `~/.skillport/skills` |
| `SKILLPORT_ENABLED_CATEGORIES` | Filter by category (comma-separated) | all |
| `SKILLPORT_ENABLED_SKILLS` | Filter by skill ID (comma-separated) | all |
| `SKILLPORT_ENABLED_NAMESPACES` | Filter by namespace (comma-separated) | all |
| `SKILLPORT_CORE_SKILLS_MODE` | Core Skills behavior (`auto`/`explicit`/`none`) | `auto` |
| `SKILLPORT_CORE_SKILLS` | Core Skill IDs for `explicit` mode (comma-separated) | none |

[Full Configuration Guide →](https://github.com/gotalab/skillport/blob/main/guide/configuration.md)

## Creating Skills

Create a `SKILL.md` file with YAML frontmatter. `name` and `description` are required:

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

[Skill Authoring Guide →](https://github.com/gotalab/skillport/blob/main/guide/creating-skills.md)

## Learn More

- [Configuration Guide](https://github.com/gotalab/skillport/blob/main/guide/configuration.md) - Filtering, search options, multi-client setup
- [Creating Skills](https://github.com/gotalab/skillport/blob/main/guide/creating-skills.md) - SKILL.md format and best practices
- [CLI Reference](https://github.com/gotalab/skillport/blob/main/guide/cli.md) - Full command documentation
- [Design Philosophy](https://github.com/gotalab/skillport/blob/main/guide/philosophy.md) - Why skills work this way

## Development

```bash
git clone https://github.com/gotalab/skillport.git
cd skillport
uv sync
SKILLPORT_SKILLS_DIR=.agent/skills uv run skillport serve
```

## License

MIT
