# SkillHub PRD

## Overview

**SkillHub** (`skillhub-mcp`) is an MCP server that provides reusable Agent Skills across different AI environments (Claude Desktop, Cursor, Windsurf, etc.).

## Problem

- Agent Skills are scattered across different environments
- Each environment has its own skill format/location
- No unified way to search, discover, and load skills
- Context efficiency: agents waste tokens re-reading skill content

## Solution

A single MCP server that:
1. **Indexes** skills from a configurable directory
2. **Searches** skills via FTS (Full-Text Search)
3. **Loads** skill instructions progressively (context-efficient)
4. **Provides paths** for local execution

## Core Tools

| Tool | Purpose |
|------|---------|
| `search_skills` | Discover skills by keyword/category/tags |
| `load_skill` | Load skill instructions + path |
| `read_skill_file` | Read files within skill directory |

## Key Design Decisions

### 1. Knowledge Provider, Not Runtime
- Skills provide **instructions**, not execution environment
- Agents execute commands in their own terminal
- `run_skill_command` is disabled by default

### 2. Path-Based Design
- `load_skill` returns skill directory path
- Agents resolve relative paths from instructions
- Minimizes `read_skill_file` usage

### 3. Progressive Loading
- `search_skills`: name + description only (discovery)
- `load_skill`: full instructions + path (execution)
- Saves context tokens

### 4. FTS-First Search
- Default: No embeddings required (`EMBEDDING_PROVIDER=none`)
- FTS via LanceDB/Tantivy
- Optional: OpenAI/Gemini embeddings for semantic search

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `SKILLS_DIR` | `.agent/skills` | Skills directory |
| `EMBEDDING_PROVIDER` | `none` | `none`, `openai`, `gemini` |
| `SEARCH_LIMIT` | `10` | Max search results |
| `SEARCH_THRESHOLD` | `0.2` | Score threshold |

## Distribution

- **PyPI**: `pip install skillhub-mcp`
- **uvx**: `uvx skillhub-mcp`
- **CLI**: `skillhub-mcp` or `skillhub`

## Target Users

1. **Skill Authors**: Create reusable skills
2. **AI Agent Users**: Use skills across environments
3. **Teams**: Share skills via Git repositories

## Success Metrics

- Skills work across Claude Desktop, Cursor, Windsurf
- Search returns relevant results within 100ms
- Context usage reduced vs. manual file reading
