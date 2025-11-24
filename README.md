# SkillHub MCP

<div align="center">

**One Agent Skills Hub for All MCP Clients**
(Cursor, Windsurf, Claude Desktop, GitHub Copilot, etc.)

[![MCP](https://img.shields.io/badge/MCP-Enabled-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

**Brand:** SkillHub / **Package & CLI:** `skillhub-mcp` (alias: `skillhub`)

## Overview

**SkillHub MCP** transforms your [Agent Skills](https://github.com/anthropics/agent-skills) into a centralized, searchable, and context-efficient execution hub accessible from any MCP-compliant tool.

Instead of copy-pasting prompts or scripts between projects, SkillHub acts as a local server that provides:
1.  **Semantic Discovery**: Find skills using natural language ("extract invoice number").
2.  **Central Management**: Keep all your skills in one SkillHub instance and share them across multiple MCP clients.
3.  **Context-Efficient Loading**: Load detailed instructions and files only when needed so prompts stay lean even as your skills grow.

## Features

*   🔍 **Hybrid Search**: Combines Vector Search (OpenAI/Gemini) and Full-Text Search (FTS) to find the right skill instantly.
*   🔁 **Multi-Client Hub**: Use the same SkillHub instance from Cursor, Claude Desktop, Windsurf, GitHub Copilot Chat, and other MCP-compatible tools.
*   🎚 **Skill Scope**: Configure filters on each SkillHub instance so connected MCP clients see either the full catalog or a focused subset using `SKILLHUB_ENABLED_SKILLS` / `SKILLHUB_ENABLED_CATEGORIES` (this is configuration, not per-user permissions).
*   🛡️ **Execution Guardrails**: Path traversal protection for file reads, command allowlisting, fixed working directory, and execution timeouts (this is not a full OS-level sandbox; only run skills you trust or isolate the server with containers/VMs/limited users).
*   📂 **Standard Format**: Compatible with the `SKILL.md` structure (Markdown + YAML Frontmatter).
*   ⚡ **Fast & Lightweight**: Built on [FastMCP](https://github.com/jlowin/fastmcp) and [LanceDB](https://lancedb.com/).

## Use Cases

### 1. One Skills Repo, Many MCP Clients

You keep the same `skills/` repository on disk, but you jump between Cursor for coding, Claude Desktop for research, and GitHub Copilot Chat for pair programming.

- Point all of these tools at a single SkillHub MCP server.
- Add or update a skill once in Git (or on disk), and every MCP client sees the same latest version.
- No more re-uploading or copy-pasting prompts for each editor or chat app.

### 2. Team-Owned Skill Library with Skill Scopes

Your team maintains a shared set of Agent Skills (infra runbooks, codegen templates, incident playbooks).

- Run one or more SkillHub instances in your shared environment and mount a team skills repository.
- For each SkillHub instance (for example per project, per environment, or per IDE setup), choose a **skill scope**: expose the full catalog, or use `SKILLHUB_ENABLED_SKILLS` / `SKILLHUB_ENABLED_CATEGORIES` to narrow which skills that instance exposes.
- Developers connect their MCP clients to the appropriate instance and see exactly the slice of the shared library that configuration allows. Skill scopes are configuration-level filters, not per-user access control.

### 3. Large Skill Catalog with Efficient Context Usage

Over time, your skills grow: dozens or hundreds of `SKILL.md` files, some with long instructions and templates.

- Let agents use `search_skills` to discover the right skill by natural language, name, or description instead of stuffing every skill’s instructions into the system prompt.
- Skills marked with `alwaysApply: true` are exposed as **Core Skills** up front so agents can use them without searching; everything else stays discoverable via `search_skills`.
- Only when a specific skill is chosen does the client call `load_skill` or `read_skill_file` to bring full instructions/templates into context, keeping prompts lean while still making the full catalog available on demand.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/your-org/skillhub-mcp.git
cd skillhub-mcp

# Install dependencies
uv sync
```

## Usage

### 1. Run Locally

```bash
# Run with local skills directory (defaults to FTS + substring search, no embeddings)
SKILLS_DIR=.agent/skills uv run skillhub-mcp  # or: uv run skillhub

# Force reindex regardless of state
uv run skillhub-mcp --reindex

# Skip auto reindex check (useful if you know the DB is fresh)
uv run skillhub-mcp --skip-auto-reindex
```

### 2. Install this MCP server

#### Cursor (official deeplink)
[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](cursor://anysphere.cursor-deeplink/mcp/install?name=skillhub&config=eyJjb21tYW5kIjogInV2IiwgImFyZ3MiOiBbInJ1biIsICJza2lsbGh1Yi1tY3AiXSwgImVudiI6IHsiU0tJTExTX0RJUiI6ICJ-Ly5za2lsbGh1Yi9za2lsbHMifX0=)

#### Kiro (official 1-click)
[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=skillhub&config=%7B%22command%22%3A%20%22uv%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22skillhub-mcp%22%5D%2C%20%22env%22%3A%20%7B%22SKILLS_DIR%22%3A%20%22~/.skillhub/skills%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D)

#### Windsurf (manual)
- Command Palette → “MCP: Add server” → Local
- command: `uv`
- args: `["run", "skillhub-mcp"]`
- env: `SKILLS_DIR=~/.skillhub/skills`
- Or edit `~/.codeium/windsurf/mcp_config.json`:
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

#### GitHub Copilot Chat (VS Code / JetBrains / Xcode) — manual
- Add a local MCP server with:
```json
{
  "servers": {
    "skillhub": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "skillhub-mcp"],
      "env": { "SKILLS_DIR": "~/.skillhub/skills" }
    }
  }
}
```
- VS Code: Command Palette → “MCP: Add server” → Local, then paste the same command/args/env.

#### Claude Code / Codex (manual CLI)
- Fastest:  
  `claude mcp add --transport stdio --env SKILLS_DIR=~/.skillhub/skills skillhub -- uv run skillhub-mcp`
  - `--` separates Claude CLI flags from the server command.
  - Add `--scope user` / `--scope project` if you want to control scope.

#### Antigravity (manual)
1. Open chat, click `[...]` → `MCP Servers`
2. `Add custom server` and enter:
   - command: `uv`
   - args: `["run", "skillhub-mcp"]`
   - env: `{"SKILLS_DIR": "~/.skillhub/skills"}`

### 3. Connect to Claude Desktop / Cursor

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

### 4. Claude Code / Codex
- Use the same command/env as above:
  - command: `uv`
  - args: `["run", "skillhub-mcp"]`
  - env: `SKILLS_DIR=~/.skillhub/skills` (override as needed)
- Add this server to your Claude Code or Codex MCP configuration per the editor’s documentation (the MCP config location differs by editor/build; use the snippet above).

> **⚠️ IMPORTANT: Reindex behavior**
>
> - On startup the server hashes all `SKILL.md` files; if anything changed it reindexes automatically.  
> - Use `--reindex` to force a rebuild immediately.  
> - If changes don’t appear in your MCP client, reconnect:
>   - Cursor / Windsurf: quit the app (`Cmd+Q`) and reopen (window reload often keeps the old session).
>   - Claude Desktop: quit (`Cmd+Q`) and reopen.
>   - Others: close the MCP session/connection and reconnect.

## Configuration

Configure the server via environment variables or `.env` file.

### Core

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SKILLS_DIR` | Path to your skills directory | `./.agent/skills` |
| `SKILLHUB_DB_PATH` | Path to LanceDB file | `~/.skillhub/skills.lancedb` |
| `ALLOWED_COMMANDS` | Comma-separated allowed commands | `python3,python,uv,node,cat,ls,grep` |

### Embedding (optional — only if you want vector search)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `EMBEDDING_PROVIDER` | `none`, `openai`, or `gemini` | `none` (FTS + substring only) |
| `OPENAI_API_KEY` | Required when provider is `openai` | — |
| `GEMINI_API_KEY` | Required when provider is `gemini` (or `GOOGLE_API_KEY`) | — |
| `EMBEDDING_MODEL` | OpenAI embedding model name | `text-embedding-3-small` |
| `GEMINI_EMBEDDING_MODEL` | Gemini embedding model name | `gemini-embedding-001` |

When `EMBEDDING_PROVIDER=none` (the default), SkillHub uses a lightweight search strategy:
- Full-Text Search (FTS) over skill name/description.
- If FTS encounters an error, it falls back to a simple substring search.
When `EMBEDDING_PROVIDER` is set to `openai` or `gemini`, vector search is added on top of FTS and substring, and missing API keys cause the server to fail fast at startup.

### Search & Filtering

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SEARCH_LIMIT` | Maximum number of results returned from `search_skills` | `10` |
| `SEARCH_THRESHOLD` | Similarity threshold for vector matches (0–1) | `0.2` |
| `SKILLHUB_ENABLED_SKILLS` | Comma-separated skill names that define the skill scope for this SkillHub process; if set, only these skills are enabled | unset (all skills enabled) |
| `SKILLHUB_ENABLED_CATEGORIES` | Comma-separated categories that define the skill scope when `SKILLHUB_ENABLED_SKILLS` is empty; only skills in these categories are enabled | unset (all categories enabled) |

### Execution Limits

| Variable | Description | Default |
| :--- | :--- | :--- |
| `EXEC_TIMEOUT_SECONDS` | Maximum time a skill command is allowed to run | `60` |
| `EXEC_MAX_OUTPUT_BYTES` | Maximum bytes captured for stdout/stderr before truncation | `65536` |
| `MAX_FILE_BYTES` | Maximum bytes read from a file via `read_skill_file` | `65536` |
| `LOG_LEVEL` | Reserved for future logging controls (currently not used) | `"INFO"` |

## Creating Skills

Create a directory under `SKILLS_DIR` with a `SKILL.md` file:

`~/.skillhub/skills/hello-world/SKILL.md`:

```markdown
---
name: hello-world
description: Prints a greeting message.
metadata:
  skillhub:
    category: demo
    tags: [demo, hello]
    runtime: python
    requires_setup: false
    env_version: 1
    alwaysApply: true  # Optional: If true, listed in system prompt as core skill
---
# Hello World

Run the python script to say hello.
```

## Tools Available

*   `search_skills(query)`: Find relevant skills.
*   `load_skill(skill_name)`: Get skill instructions.
*   `read_skill_file(skill_name, file_path)`: Read a file from the skill directory.
*   `execute_skill_command(skill_name, command, args)`: Run a command in the skill directory.

### Core Skills Feature

If you set `alwaysApply: true` under `metadata.skillhub` in a skill's frontmatter, it will be listed as a **Core Skill** in the server's instructions.
This allows agents to know about and use these skills immediately without needing to search for them first.

## Development & Debugging

- The MCP protocol uses `stdout` for JSON-RPC messages only.
- Always send logs and debug output to `stderr` (never to `stdout`), otherwise MCP clients may see corrupted responses.

### Security Model & Risks

- Skill commands run as local processes with the same user permissions as the `skillhub-mcp` server.
- The server applies guardrails (command allowlist, shell-less subprocesses, scoped working directory, path validation, timeouts, output truncation), but it does **not** provide a hard sandbox against malicious code.
- Treat skills as you would any local script: only install/run skills you trust, or run `skillhub-mcp` itself inside additional isolation (e.g., container, VM, or a dedicated low-privilege user).

## License

MIT
