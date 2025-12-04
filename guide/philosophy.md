# Design Philosophy

This document explains the design principles behind SkillPort and Agent Skills.

## What are Agent Skills?

[Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) are folders of instructions, scripts, and resources that AI agents discover and load dynamically. They were introduced by Anthropic as a way to give agents expert knowledge without bloating the context window.

### The Problem with System Prompts

Traditional approach to giving AI agents knowledge:

```
System Prompt (loaded every conversation):
├── Company guidelines (2,000 tokens)
├── Coding standards (3,000 tokens)
├── Review checklist (1,500 tokens)
├── 50 more instructions...
└── Total: 30,000+ tokens before you say "hello"
```

**Problems:**
- Context window bloat
- Irrelevant knowledge in every conversation
- Hard to maintain and update
- No way to share across teams

### The Skills Solution

Skills use **progressive disclosure** — load knowledge only when relevant:

```
Conversation start:
├── Skill metadata only (~100 tokens each)
└── Full instructions loaded on demand

User: "Review this PR"
├── Agent searches: "code review"
├── Loads: code-review skill (1,500 tokens)
└── Uses only what's needed
```

## Skills vs MCP

A common question: "Isn't this what MCP does?"

| Layer | Role | Example |
|-------|------|---------|
| **MCP** | Data access | "Connect to GitHub API" |
| **Skills** | Procedural knowledge | "When reviewing PRs, check these 5 things" |

> MCP connects to data. Skills teach *how to use* that data.

**They're complementary:**
```
MCP Server: Provides GitHub API access
    ↓
Skill: "When reviewing PRs on GitHub:
        1. Check CI status first
        2. Look for security issues
        3. Verify test coverage..."
```

## Why SkillPort?

Claude Code has built-in Skills support (`.claude/skills/`), but it's Claude-specific. SkillPort brings Agent Skills to **any MCP client** with additional management capabilities:

| Feature | Claude Code Native | SkillPort |
|---------|-------------------|----------|
| Client support | Claude Code only | Any MCP client |
| Search | Basic matching | Full-text search (BM25) |
| Installation | Manual copy | CLI + GitHub integration |
| Filtering | None | By category, namespace, or skill ID |
| Scaling | Limited | 100+ skills efficiently |

### SkillPort's Four Pillars

1. **Deliver**: MCP server for any client (Cursor, Windsurf, Claude Desktop, etc.)
2. **Manage**: CLI for skill lifecycle (add, remove, lint, list)
3. **Organize**: Categories, namespaces, and Core Skills (alwaysApply)
4. **Scale**: Full-text search with smart fallback

## Progressive Disclosure

Skills load information in stages, minimizing context usage:

| Stage | When Loaded | Token Cost | Content |
|-------|-------------|------------|---------|
| **Level 1** | Server start | ~100/skill | Name + description (indexed metadata) |
| **Level 2** | `load_skill()` | < 5,000 | Full instructions (SKILL.md body) |
| **Level 3** | `read_skill_file()` | Variable | Templates, configs, references |

```
100 skills installed:
├── Level 1: 100 × ~100 = ~10,000 tokens (metadata only)
├── Level 2: Load 1-2 relevant skills = ~5,000 tokens
└── Total: ~15,000 tokens vs 300,000+ if all loaded
```

## Path-Based Design

### Skills Are Knowledge, Not Execution Environments

```
┌─────────────────────────────────────────────────────────────┐
│ User's Project (Agent's execution context)                  │
│                                                             │
│  ├── src/            ← Code generation                      │
│  ├── output/         ← Script outputs                       │
│  └── .venv/          ← Execution environment                │
│                                                             │
│  [Agent executes here]                                    │
└─────────────────────────────────────────────────────────────┘
                    ↑
          Agent uses skill knowledge
          to work in user's project
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ SkillPort MCP Server                                         │
│                                                             │
│  ├── search_skills()   → Find relevant skills               │
│  ├── load_skill()      → Get instructions + path            │
│  └── read_skill_file() → Read templates if needed           │
│                                                             │
│  [Knowledge provider, not execution environment]          │
└─────────────────────────────────────────────────────────────┘
```

### Why Return Paths Instead of Content?

```python
# load_skill returns:
{
    "name": "pdf-extractor",
    "instructions": "...",
    "path": "/Users/me/.skillport/skills/pdf-extractor"
}
```

The agent uses `path` to execute scripts:

```bash
# Agent runs in user's project:
python /Users/me/.skillport/skills/pdf-extractor/scripts/extract.py \
    ./input.pdf \
    --output ./output/extracted.txt
```

**Benefits:**

| Approach | Context Cost | Output Location | File Transfer |
|----------|--------------|-----------------|---------------|
| Return file content | High (code in context) | MCP server | Needed |
| Return path | Low (~20 tokens) | User's project | Not needed |

### Context Engineering

The key insight: **executing code doesn't require reading code**.

```
❌ Inefficient:
1. read_skill_file("pdf", "scripts/extract.py")  → 2,000 tokens
2. Look at the code
3. Execute it anyway

✅ Efficient:
1. load_skill("pdf")  → Get path
2. Execute: python {path}/scripts/extract.py  → 20 tokens
```

**When to read file content:**
- Need to understand the code
- Want to modify or adapt it
- Debugging issues

**When to use path only:**
- Just executing a working script
- Running validated tools

## Client-Based Skill Filtering

Different AI agents need different skills. SkillPort lets you control what each client sees:

```
IDE Agent (Cursor, Windsurf):
├── code-review
├── testing
├── refactoring
└── debugging

Chat Agent (Claude Desktop):
├── writing-assistant
├── summarizer
├── translator
└── research
```

Configure via environment variables:

```json
{
  "mcpServers": {
    "skillport-ide": {
      "env": { "SKILLPORT_ENABLED_CATEGORIES": "development" }
    },
    "skillport-chat": {
      "env": { "SKILLPORT_ENABLED_CATEGORIES": "writing,research" }
    }
  }
}
```

Same skill repository, different views per client.

## Search Strategy

### Full-Text Search (Default)

SkillPort uses BM25-based full-text search via Tantivy as the default:

- **No API keys required** — works out of the box
- **Privacy-preserving** — no data sent to external services
- **Fast** — indexes name, description, tags, category
- **Reliable** — always returns results

### Fallback Chain

Search always returns results through a fallback chain:

```
FTS (BM25)
    ↓ (no results)
substring match
    ↓
always something
```

### Shared Pattern with Tool Search Tool

SkillPort's `search_skills` and Anthropic's [Tool Search Tool](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/tool-search-tool) solve the same problem with the same approach:

| Problem | Solution |
|---------|----------|
| Too many items bloat context | Search first, load on demand |
| Need fast, accurate discovery | BM25 full-text search |
| Some items always needed | Core Skills / non-deferred tools |

**Tool Search Tool is for API tools. SkillPort is for procedural knowledge.**

Both patterns recognize the same truth: *loading everything upfront doesn't scale*.

| Aspect | Tool Search Tool | SkillPort |
|--------|------------------|-----------|
| Target | API tool definitions | Skills (instructions + scripts) |
| Search | BM25 or regex | BM25 with fallback |
| Deferred loading | `defer_loading: true` | `load_skill()` on demand |
| Always available | Non-deferred tools | Core Skills (`alwaysApply`) |
| Context savings | 50 tools ≈ 10-20K → search-based | 100 skills ≈ 300K → ~15K |

## Design Principles

### 1. Convention Over Configuration

```bash
# Just works with defaults
skillport add hello-world
skillport serve
```

Configuration only when you need to customize.

### 2. Progressive Complexity

| Level | User | Features |
|-------|------|----------|
| Basic | "I want to try skills" | `add`, `list`, defaults |
| Intermediate | "I have many skills" | Categories, namespaces |
| Advanced | "I need fine control" | Filtering, search tuning |

### 3. Portable Format

Skills use Anthropic's Agent Skills format:
- Works with Claude Code natively
- Works with any MCP client via SkillPort
- Plain Markdown + YAML (no lock-in)

### 4. Searchable by Default

Every skill is searchable without configuration:
- FTS works out of the box
- Fallback chain ensures results

## Trade-offs

### What We Chose

| Decision | Trade-off | Rationale |
|----------|-----------|-----------|
| FTS default | Less semantic matching | No API keys, privacy, speed |
| Path-based | Agent needs shell access | Context efficiency, direct output |
| 2-level nesting | Limited hierarchy | Simplicity, covers 95% of cases |
| No version lock | Manual updates | Simplicity, skills are usually small |

### What We Avoided

- **Central registry**: Added complexity, governance overhead
- **Dependency resolution**: Skills should be self-contained
- **Hot reload**: Complexity for rare use case
- **Deep nesting**: Diminishing returns after 2 levels

## See Also

- [Creating Skills](creating-skills.md) — Practical skill authoring
- [Configuration](configuration.md) — Filtering and search options
- [CLI Reference](cli.md) — Command documentation
