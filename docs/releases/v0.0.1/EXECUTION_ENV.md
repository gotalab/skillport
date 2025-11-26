# Execution Environment & Setup Model (run_skill_command)

**Status:** Design v3.2 (run_skill_command disabled by default)
**Scope:** How SkillHub executes scripts with simplified execution model.

> **前提**: このドキュメントを読む前に [SKILL_PHILOSOPHY.md](./SKILL_PHILOSOPHY.md) を参照してください。
> Agent Skillsは「知識を提供するもの」であり、「実行環境」ではありません。
>
> ⚠️ **`run_skill_command` はデフォルトで無効です。**
> `load_skill` で取得した `path` を使って、エージェント自身のターミナルで直接実行してください。
> このツールは server.py でコメントアウトされており、必要な場合のみ有効化できます。

---

## 1. What Changed in v3.2

### Disabled by Default

- `run_skill_command` tool - disabled in server.py (commented out)

### Removed Fields

- `runtime` field (SKILL.md metadata) - all skills use same execution model
- `requires_setup` field (removed in v3.0)

### Simplified Model

- **Direct execution**: Agent uses `path` from `load_skill` to execute scripts directly
- **PEP 723 support**: Scripts declare dependencies inline, `uv run` handles them
- **Path-based design**: `load_skill` returns `path` for file resolution

---

## 2. Goals & Non-Goals

**Goals**

- Simple, deterministic execution: `uv run python` or `python3`
- Support PEP 723 inline script dependencies
- Path-based design for context efficiency
- Security first: allowlist commands, no shell expansion

**Non-Goals**

- Managing skill-local environments (removed in v3.0)
- Node.js execution (removed in v3.0)
- Auto-setup features (removed in v3.0)

---

## 3. Execution Model

### 3.1 Python Execution

When `command` is `python` or `python3`:

```python
def _resolve_python_command() -> List[str]:
    """
    Phase 5 model:
    - If uv available: ["uv", "run", "python"] (supports PEP 723 inline deps)
    - Else: ["python3"] (fallback, no PEP 723 support)
    """
    if shutil.which("uv"):
        return ["uv", "run", "python"]
    else:
        print("[WARN] uv not found. PEP 723 inline dependencies won't work.", file=sys.stderr)
        return ["python3"]
```

### 3.2 PEP 723 Inline Dependencies

Skills can use PEP 723 inline script metadata:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "pillow"]
# ///

from pypdf import PdfReader
# ... script code ...
```

When executed via `uv run python script.py`, uv automatically:
1. Creates a temporary virtual environment
2. Installs declared dependencies
3. Runs the script
4. Cleans up

### 3.3 Other Commands

| Command | Execution |
|---------|-----------|
| `uv` | Direct execution (for `uv run script.py`) |
| `bash`, `sh` | Direct execution from PATH |
| `cat`, `ls`, `grep` | Direct execution from PATH |

### 3.4 Execution Contract

- **CWD**: Always `skill_dir = SKILLS_DIR / skill_name`
- **Shell**: Always `shell=False` (no exceptions)
- **Allowlist**: Only commands in `ALLOWED_COMMANDS` permitted
  - Default: `python3, python, uv, bash, sh, cat, ls, grep`
- **Timeout**: `EXEC_TIMEOUT_SECONDS` enforced
- **Output Limit**: Truncate at `EXEC_MAX_OUTPUT_BYTES` (byte-level)

---

## 4. SKILL.md Metadata

### 4.1 Schema (v3.1)

```yaml
---
name: pdf-extractor
description: Extract data from PDFs using PEP 723 inline dependencies.
metadata:
  skillhub:
    category: documents
    tags: [pdf, extraction]
---
```

### 4.2 Default Values

| Field | Default |
|-------|---------|
| `category` | (none) |
| `tags` | `[]` |
| `alwaysApply` | `false` |

**Note**: `runtime` field was removed in v3.1. All skills use the same execution model.

---

## 5. API Response (Path-Based Design)

`load_skill` returns `path` to enable direct file access and execution.

### 5.1 search_skills Response

```json
{
  "skills": [
    {
      "name": "pdf-extractor",
      "description": "Extract data from PDFs",
      "score": 0.85
    }
  ]
}
```

Note: `path` is not included in search results. Call `load_skill` to get the path.

### 5.2 load_skill Response

```json
{
  "name": "pdf-extractor",
  "instructions": "... SKILL.md content ...",
  "path": "/path/to/skills/pdf-extractor"
}
```

### 5.3 Path Resolution

Instructions in SKILL.md reference files with relative paths (e.g., "run script.py").
Agents resolve these using: `path + "/" + relative_file`

Example:
- `path`: `/home/user/.skillhub/skills/pdf-extractor`
- Instruction says: "run scripts/extract.py input.pdf"
- Full path: `/home/user/.skillhub/skills/pdf-extractor/scripts/extract.py`

---

## 6. Skill Patterns

### 6.1 Prompt-Only Skill

```yaml
---
name: code-review-guide
description: Best practices for code review.
metadata:
  skillhub:
    category: development
    tags: [code-review]
---
```

No execution needed. Agent uses `load_skill` and `read_skill_file`.

### 6.2 Python Skill with PEP 723

```yaml
---
name: pdf-extractor
description: Extract text from PDFs.
metadata:
  skillhub:
    category: documents
    tags: [pdf]
---
```

**scripts/extract.py:**
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf>=4.0"]
# ///

import sys
from pypdf import PdfReader

def main():
    reader = PdfReader(sys.argv[1])
    for page in reader.pages:
        print(page.extract_text())

if __name__ == "__main__":
    main()
```

**Execution (recommended - direct):**
```bash
# Agent uses path from load_skill and executes directly
python /path/to/skills/pdf-extractor/scripts/extract.py doc.pdf
# or with uv for PEP 723 deps:
uv run python /path/to/skills/pdf-extractor/scripts/extract.py doc.pdf
```

### 6.3 Python Skill (stdlib only)

```yaml
---
name: json-formatter
description: Format JSON files.
metadata:
  skillhub:
    category: utility
---
```

**format.py:**
```python
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)
print(json.dumps(data, indent=2))
```

No PEP 723 header needed for stdlib-only scripts.

### 6.4 Bash Script Skill

```yaml
---
name: file-stats
description: Get file statistics.
metadata:
  skillhub:
    category: utility
---
```

**stats.sh:**
```bash
#!/bin/bash
wc -l "$1"
```

**Execution (recommended - direct):**
```bash
bash /path/to/skills/file-stats/stats.sh file.txt
```

**Note**: Bash scripts require WSL or Git Bash on Windows.

---

## 7. Cross-Platform Guidelines

**Recommended: Python scripts**

| Language | Cross-Platform | Notes |
|----------|----------------|-------|
| Python | Recommended | Works on Mac/Linux/Windows |
| Bash/Shell | Caution | Requires WSL or Git Bash on Windows |

For maximum compatibility, prefer Python scripts with PEP 723 dependencies.

---

## 8. Security Considerations

### 8.1 Allowlist Commands

Only commands in `ALLOWED_COMMANDS` are permitted:
- `python3`, `python`, `uv`
- `bash`, `sh`
- `cat`, `ls`, `grep`

Package managers (`npm`, `pnpm`, `yarn`) are **not** in the default allowlist.

### 8.2 No Shell Expansion

`shell=False` is always used. No exceptions.

### 8.3 Timeout and Output Limits

- Commands are killed after `EXEC_TIMEOUT_SECONDS` (default: 60)
- Output is truncated at `EXEC_MAX_OUTPUT_BYTES` (default: 1MB)

---

## 9. Migration Guide

### 9.1 From v2.x (with `requires_setup` or `runtime`)

**Before:**
```yaml
metadata:
  skillhub:
    runtime: python
    requires_setup: true
```

**After (v3.1):**
```yaml
metadata:
  skillhub:
    category: your-category
    tags: [your-tags]
```

- `runtime` field removed (all skills use same execution model)
- `requires_setup` field removed (use PEP 723 for dependencies)
- Use direct execution via `load_skill` path

---

## 10. Implementation Status

| Component | Status |
|-----------|--------|
| Direct execution via path | Recommended |
| `run_skill_command` | Disabled by default (v3.2) |
| PEP 723 support (via uv) | Implemented |
| `path` in load_skill | Implemented |
| Removed `runtime` field | Implemented (v3.1) |
| Removed `requires_setup` | Implemented |
| Removed `setup.py` module | Implemented |
| Removed CLI flags | Implemented |
