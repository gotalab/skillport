# SkillHub MCP

<div align="center">

**Reusable Agent Skills Hub for MCP Clients**
(Cursor, Windsurf, Claude Desktop, etc.)

[![MCP](https://img.shields.io/badge/MCP-Enabled-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

**Brand:** SkillHub / **Package & CLI:** `skillhub-mcp` (alias: `skillhub`)

## Overview

**SkillHub MCP** transforms your [Agent Skills](https://github.com/anthropics/agent-skills) into a centralized, searchable, and executable hub accessible from any MCP-compliant tool.

Instead of copy-pasting prompts or scripts between projects, SkillHub acts as a local server that provides:
1.  **Semantic Discovery**: Find skills using natural language ("extract invoice number").
2.  **Safe Execution**: Run skills in an isolated environment with strict permission controls.
3.  **Universal Access**: Share one skill library across Cursor, Claude Desktop, and other agents.

## Features

*   🔍 **Hybrid Search**: Combines Vector Search (OpenAI/Ollama) and Full-Text Search (FTS) to find the right skill instantly.
*   🛡️ **Security First**: Path traversal protection, command allowlisting, and execution timeouts.
*   📂 **Standard Format**: Compatible with the `SKILL.md` structure (Markdown + YAML Frontmatter).
*   ⚡ **Fast & Lightweight**: Built on [FastMCP](https://github.com/jlowin/fastmcp) and [LanceDB](https://lancedb.com/).

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/your-org/skillhub-mcp.git
cd skillhub-mcp

# Install dependencies
uv sync
```

## Configuration

Configure the server via environment variables or `.env` file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SKILLS_DIR` | Path to your skills directory | `~/.skillhub/skills` |
| `EMBEDDING_PROVIDER` | `openai`, `ollama`, or `none` | `none` |
| `OPENAI_API_KEY` | Required if provider is openai | - |
| `ALLOWED_COMMANDS` | Comma-separated allowed commands | `python,uv,node,cat,ls,grep` |

## Usage

### 1. Run Locally

```bash
# Run with local skills directory (defaults to FTS search)
SKILLS_DIR=./my-skills uv run skillhub-mcp  # or: uv run skillhub
```

### 2. Connect to Claude Desktop / Cursor

Add the following to your MCP config (e.g., `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "skillhub": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/path/to/skillhub-mcp", 
        "skillhub-mcp"
      ],
      "env": {
        "SKILLS_DIR": "/Users/username/.agent/skills",
        "EMBEDDING_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```
*(You can swap `skillhub-mcp` for the alias `skillhub` in the args above.)*

> **⚠️ IMPORTANT: Changes require restart**
>
> If you add new skills or update `SKILL.md`, the changes **will not appear** in the MCP client (Cursor, Windsurf, Claude Desktop) until you **completely restart the application**.
>
> *   **Cursor/Windsurf**: `Command+Q` to quit, then reopen. Reloading the window is often not enough.
> *   **Claude Desktop**: Quit and restart.

## Creating Skills

Create a directory under `SKILLS_DIR` with a `SKILL.md` file:

`~/.skillhub/skills/hello-world/SKILL.md`:

```markdown
---
name: hello-world
description: Prints a greeting message.
tags: [demo, hello]
alwaysApply: true  # Optional: If true, listed in system prompt as core skill
---
# Hello World

Run the python script to say hello.
```

## Tools Available

*   `search_skills(query)`: Find relevant skills.
*   `load_skill(skill_name)`: Get skill instructions.
*   `read_file(skill_name, file_path)`: Read a file from the skill directory.
*   `execute_skill_command(skill_name, command, args)`: Run a command in the skill directory.

### Core Skills Feature

If you set `alwaysApply: true` in a skill's frontmatter, it will be listed as a **Core Skill** in the server's instructions.
This allows agents to know about and use these skills immediately without needing to search for them first.

## License

MIT
