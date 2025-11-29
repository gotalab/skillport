# Agent Guidelines & Context

## 1. Core Principles (10-second recall)
* **PLAN.md**: SSOT for「どう作るか」(how to build); keep tasks in `docs/latest/PLAN.md`, update continuously, snapshot at release.
* **Task tracking**: Use checkbox lists (`- [ ]`/`- [x]`); include Task ID for larger work.
* **Safe defaults**: Default `EMBEDDING_PROVIDER=none`; when enabling external providers, fail fast on missing keys.
* **Normalization**: Always trim+lowercase `category`/`tags` for indexing, filtering, and search.
* **Fallback chain**: Preserve vector → FTS → substring fallback; never break the chain.
* **MCP logging**: stdout is JSON-RPC only; send all logs/debug to stderr.
* **Behavioral regression tests (golden traces)**: Not required now; add for critical flows when ready.
* **Docs governance**: See `docs/AGENTS.md` for layout/roles; `docs/steering/OPERATING_MODEL.md` for doc/release ops; `docs/steering/ENGINEERING_GUIDE.md` for technical policy; `docs/steering/RUNBOOK.md` for operational steps.

## 2. Project Context
### Architecture
*   **Brand**: SkillSouko
*   **Package & CLI**: `skillsouko` (legacy alias: `skillsouko-mcp`)
*   **Type**: MCP Server (Model Context Protocol)
*   **Stack**:
    *   **Runtime**: Python 3.10+
    *   **Package Manager**: `uv`
    *   **MCP Lib**: `fastmcp`
    *   **Database**: `lancedb` (Vector + FTS)
    *   **Config**: `pydantic-settings`

### Directory Structure
*   `src/skillsouko/`: Source code (modular monolith)
    *   `interfaces/cli/`: Typer CLI adapter
    *   `interfaces/mcp/`: FastMCP server adapter
    *   `modules/skills/`: Skill management public/internal APIs
    *   `modules/indexing/`: Index build/query logic
    *   `shared/`: Config, types, utils, exceptions
*   `docs/latest/`: Living documentation (SSOT)
*   `docs/releases/vX.Y.Z/`: Release snapshots (frozen)
*   `docs/steering/`: Governance & guides
*   `.agent/skills/`: Local skills storage for testing
*   `verify_server.py`: Verification script (Mock Client)

## 3. Operation & Verification
To act autonomously, always verify changes using these commands:

*   **Install/Sync**: `uv sync`
*   **Run Server (Manual)**:
    ```bash
    SKILLSOUKO_SKILLS_DIR=.agent/skills SKILLSOUKO_EMBEDDING_PROVIDER=none uv run skillsouko
    ```
*   **Verify Functionality (Critical)**:
    ```bash
    uv run verify_server.py
    ```
    *   Always run this after modifying `server.py`, `db/`, or `config.py`.

## 4. Debugging & Logging
*   **MCP Constraints**: The server communicates via `stdout`.
    *   **NEVER** print debug info to `stdout`.
    *   **ALWAYS** use `sys.stderr` for logs/prints.
*   **Logs**: If `verify_server.py` fails, check the `stderr` output captured in the tool result.

<!-- SKILLSOUKO_START -->
<available_skills>

## SkillSouko Skills

Skills are reusable expert knowledge that help you complete tasks effectively.
Each skill contains step-by-step instructions, templates, and scripts.

### Workflow

1. **Find a skill** - Check the table below for a skill matching your task
2. **Get instructions** - Run `skillsouko show <skill-id>` to load full instructions
3. **Follow the instructions** - Execute the steps using your available tools

### Tips

- Skills may include scripts - execute them via the skill's path, don't read them into context
- If instructions reference `{path}`, replace it with the skill's directory path
- When uncertain, check the skill's description to confirm it matches your task

### Available Skills

| ID | Description | Category |
|----|-------------|----------|
| anthropics-skills/template-skill | Replace with description of the skill and when Claude should use it. | - |
| anthropics-skills/theme-factory | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly. | - |
| anthropics-skills/algorithmic-art | Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. Create original algorithmic art rather than copying existing artists' work to avoid copyright violations. | - |
| anthropics-skills/internal-comms | A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.). | - |
| anthropics-skills/skill-creator | Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations. | - |
| anthropics-skills/canvas-design | Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster, piece of art, design, or other static piece. Create original visual designs, never copying existing artists' work to avoid copyright violations. | - |
| anthropics-skills/slack-gif-creator | Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack." | - |
| anthropics-skills/webapp-testing | Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs. | - |
| anthropics-skills/frontend-design | Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics. | - |
| anthropics-skills/mcp-builder | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK). | - |
| anthropics-skills/brand-guidelines | Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply. | - |
| anthropics-skills/web-artifacts-builder | Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts. | - |

</available_skills>
<!-- SKILLSOUKO_END -->
