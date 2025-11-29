# Creating Skills

This guide covers how to create and structure [Agent Skills](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills/overview) for SkillSouko.

## Quick Start

```bash
# Add the template skill
skillsouko add template

# Edit the template
# ~/.skillsouko/skills/template/SKILL.md
```

Or create from scratch:

```bash
mkdir -p ~/.skillsouko/skills/my-skill
cat > ~/.skillsouko/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: What this skill does (used for search)
---
# My Skill

Instructions for the AI agent go here.
EOF
```

## SKILL.md Format

Every skill requires a `SKILL.md` file with YAML frontmatter.

### Required Fields

```yaml
---
name: my-skill
description: Brief description of what this skill does
---
# My Skill

Detailed instructions for the AI agent.
```

| Field | Requirements |
|-------|--------------|
| `name` | Lowercase, hyphens only, max 64 chars, must match directory name |
| `description` | Non-empty, max 1024 chars, used for search |

### Optional Metadata

```yaml
---
name: code-review
description: Systematic code review checklist for pull requests
metadata:
  skillsouko:
    category: development
    tags: [code-review, pr, quality]
    alwaysApply: false
---
```

| Field | Description | Default |
|-------|-------------|---------|
| `category` | Grouping for filtering/search | none |
| `tags` | Keywords for search | `[]` |
| `alwaysApply` | Always load as Core Skill | `false` |

### Core Skills (alwaysApply)

Skills with `alwaysApply: true` are loaded into every conversation:

```yaml
---
name: team-standards
description: Our team's coding standards
metadata:
  skillsouko:
    alwaysApply: true
---
```

Use sparingly - these consume context in every conversation.

> **Tip:** Core Skills can be controlled per-client via `SKILLSOUKO_CORE_SKILLS_MODE`.
> See [Configuration](configuration.md#core-skills-control) for details.

## Directory Structure

```
my-skill/
├── SKILL.md           # Required - Agent instructions
├── scripts/           # Optional - Executable scripts
│   ├── process.py
│   └── validate.sh
├── templates/         # Optional - Templates and configs
│   ├── config.yaml
│   └── example.json
└── README.md          # Optional - Human documentation (not loaded)
```

### File Roles

| File/Directory | Purpose | Loaded by Agent? |
|----------------|---------|------------------|
| `SKILL.md` | Agent instructions | Yes (via `load_skill`) |
| `scripts/` | Executable scripts | No (executed via path) |
| `templates/` | Templates, configs | Yes (via `read_skill_file`) |
| `README.md` | Human docs, setup | No |

## Writing Effective Instructions

### Keep Instructions Concise

Target under 5,000 tokens. Use:
- Bullet points over paragraphs
- Step-by-step numbered lists
- Clear section headings

```markdown
# Code Review Skill

## When to Use
- Reviewing pull requests
- Checking code quality before merge

## Steps
1. Check for security issues
2. Verify error handling
3. Review naming conventions
4. Check test coverage

## Checklist
- [ ] No hardcoded secrets
- [ ] All errors handled
- [ ] Tests included
```

### Use Path-Based References

Reference files by path, don't inline code:

```markdown
# Good - Reference by path
Run the validation script:
```bash
python {path}/scripts/validate.py input.txt
```

# Avoid - Inline code wastes context
```python
def validate(input):
    # 50 lines of code...
```
```

The `{path}` placeholder is replaced with the skill's directory path when loaded.

### Provide Context for Scripts

Explain what scripts do without showing the code:

```markdown
## Available Scripts

### scripts/extract.py
Extracts text from PDF files.

**Usage:**
```bash
python {path}/scripts/extract.py input.pdf --output text.txt
```

**Arguments:**
- `input.pdf` - Path to PDF file
- `--output` - Output file path (default: stdout)
```

## Skill Types

### Prompt-Only Skills

Instructions and guidelines without executable code.

```
checklist-skill/
├── SKILL.md           # Instructions only
└── templates/
    └── checklist.md   # Optional template
```

**Use cases:**
- Code review checklists
- Writing guidelines
- Process documentation

### Script-Based Skills

Include executable scripts for automation.

```
pdf-processor/
├── SKILL.md
├── scripts/
│   └── extract.py     # PEP 723 for dependencies
└── templates/
    └── output.json
```

**Use cases:**
- File processing
- Data transformation
- API integrations

### PEP 723 for Dependencies

Scripts can declare dependencies inline:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pypdf>=4.0",
#   "requests",
# ]
# ///

import pypdf
import requests

def main():
    ...
```

When executed with `uv run script.py`, dependencies are automatically installed.

## Best Practices

### 1. Match Name to Directory

The `name` field must match the directory name:

```
✓ skills/code-review/SKILL.md  →  name: code-review
✗ skills/code-review/SKILL.md  →  name: review-code
```

Validate with: `skillsouko lint`

### 2. Write Searchable Descriptions

Descriptions are used for search. Include key terms:

```yaml
# Good - Searchable
description: Extract text content from PDF documents using Python

# Bad - Vague
description: PDF utility
```

### 3. Use Categories and Tags

Help users find your skill:

```yaml
metadata:
  skillsouko:
    category: data-processing
    tags: [pdf, text-extraction, documents]
```

### 4. Separate Human and Agent Docs

- `SKILL.md` - For the AI agent (loaded into context)
- `README.md` - For humans (setup, examples, troubleshooting)

### 5. Test Before Sharing

```bash
# Validate structure
skillsouko lint my-skill

# Test in real conversation
# Ask: "Search for my-skill"
# Then: "Load and use my-skill"
```

## Examples

### Minimal Skill

```yaml
---
name: git-commit-style
description: Guidelines for writing good git commit messages
---
# Git Commit Style

## Format
```
<type>: <subject>

<body>
```

## Types
- feat: New feature
- fix: Bug fix
- docs: Documentation
- refactor: Code refactoring
```

### Full-Featured Skill

```yaml
---
name: pdf-extractor
description: Extract text and metadata from PDF documents
metadata:
  skillsouko:
    category: data-processing
    tags: [pdf, text-extraction, documents]
---
# PDF Extractor

## Overview
Extract text content from PDF files with metadata preservation.

## Usage

### Basic Extraction
```bash
python {path}/scripts/extract.py document.pdf
```

### With Options
```bash
python {path}/scripts/extract.py document.pdf \
  --output text.txt \
  --include-metadata \
  --pages 1-10
```

## Output Format
See `{path}/templates/output.json` for the output schema.

## Limitations
- Scanned PDFs require OCR (not included)
- Max file size: 100MB
```

## Sharing Skills

### GitHub Repository

Structure for sharing multiple skills:

```
my-skills-repo/
├── README.md           # Human docs for the collection
├── code-review/
│   └── SKILL.md
├── testing/
│   └── SKILL.md
└── documentation/
    └── SKILL.md
```

Users install with:
```bash
skillsouko add https://github.com/user/my-skills-repo
```

### Single Skill Repository

```
pdf-extractor/
├── README.md           # Human docs
├── SKILL.md            # Agent instructions
└── scripts/
    └── extract.py
```

Users install with:
```bash
skillsouko add https://github.com/user/pdf-extractor
```

## See Also

- [CLI Reference](cli.md) — Command documentation
- [Configuration](configuration.md) — Categories, filtering, search options
- [Design Philosophy](philosophy.md) — Why skills work this way
