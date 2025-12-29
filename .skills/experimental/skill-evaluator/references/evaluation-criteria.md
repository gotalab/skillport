# Evaluation Criteria Reference

Detailed evaluation criteria based on Anthropic's official best practices for agent skill authoring.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Naming Requirements](#naming-requirements)
3. [Description Requirements](#description-requirements)
4. [Content Quality](#content-quality)
5. [Structure Requirements](#structure-requirements)
6. [Degrees of Freedom](#degrees-of-freedom)
7. [Anti-Patterns](#anti-patterns)
8. [Script Requirements](#script-requirements)
9. [Testing Requirements](#testing-requirements)

---

## Core Principles

### Conciseness is Essential

Skills share Claude's context window with system prompts, conversation history, and other skills. Challenge each piece of information:

- "Does Claude really need this explanation?"
- "Does this paragraph justify its token cost?"

**Test**: A concise 50-token explanation beats a verbose 150-token version when both convey the same information.

### Assume Claude is Intelligent

Avoid over-explaining concepts Claude already understands:

- Don't explain what Python is
- Don't explain basic programming concepts
- Don't explain how APIs work in general
- Don't explain what JSON/YAML/Markdown is

**Include**: Domain-specific knowledge, company-specific patterns, non-obvious workflows, fragile sequences.

---

## Naming Requirements

### Rules

| Rule | Requirement |
|------|-------------|
| Length | Maximum 64 characters |
| Characters | Lowercase letters, numbers, hyphens only |
| Reserved words | No "anthropic" or "claude" |
| XML tags | No XML-like patterns |
| Format | Gerund form preferred (verb + -ing) |

### Good Examples

```
processing-pdfs
analyzing-spreadsheets
building-dashboards
deploying-applications
managing-databases
```

### Bad Examples

```
pdf                     # Too vague
my-skill               # Not descriptive
ClaudeHelper           # Wrong case, reserved word
anthropic-tools        # Reserved word
<xml-skill>            # XML pattern
very-long-skill-name-that-exceeds-the-maximum-character-limit-allowed  # Too long
```

### Gerund Form Guidance

| Instead of | Use |
|------------|-----|
| `pdf-tool` | `processing-pdfs` |
| `image-editor` | `editing-images` |
| `data-analysis` | `analyzing-data` |
| `code-review` | `reviewing-code` |

---

## Description Requirements

### Rules

| Rule | Requirement |
|------|-------------|
| Length | Maximum 1024 characters, non-empty |
| Perspective | Third person |
| Content | Functionality AND activation triggers |
| Format | No XML tags |

### Components of Good Description

1. **What it does**: Clear functionality statement
2. **When to use**: Specific activation triggers
3. **Scope**: What's included (and optionally what's not)

### Good Example

```
Extracts text and data from PDF documents, including form fields, tables,
and embedded images. Use when working with PDF files for: (1) text extraction,
(2) form data parsing, (3) table extraction, (4) converting PDFs to other formats,
or (5) analyzing document structure.
```

### Bad Examples

```
# Too vague
A skill for PDFs.

# Missing triggers
Processes PDF documents and extracts text content.

# Second person (wrong perspective)
Use this skill when you need to work with PDFs.

# Too long (over 1024 chars)
[Extremely long description that goes on and on...]
```

### Third Person Test

- Good: "Extracts text from PDFs"
- Bad: "Use this skill to extract text from PDFs"
- Bad: "I can extract text from PDFs"
- Bad: "You can extract text from PDFs"

---

## Content Quality

### Verbosity Check

Rate each section:

| Rating | Description |
|--------|-------------|
| Essential | Cannot remove without losing critical info |
| Helpful | Adds value but could be condensed |
| Redundant | Repeats information already covered |
| Unnecessary | Claude already knows this |

**Action**: Remove Unnecessary, condense Redundant, review Helpful.

### Example Comparison

**Verbose (150 tokens)**:
```markdown
## How to Extract Text from a PDF

PDF documents are a common format for sharing documents. They can contain
text, images, and other content. To extract text from a PDF, you need to
use a library that can parse PDF files. There are several libraries
available in Python for this purpose. One popular library is pdfplumber,
which provides a simple API for extracting text...
```

**Concise (50 tokens)**:
```markdown
## Text Extraction

Use pdfplumber for text extraction:
```python
import pdfplumber
with pdfplumber.open("doc.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

### Information Density Test

Good skills have high information density:
- Each sentence adds new, actionable information
- Examples are specific and usable
- No filler phrases ("It's worth noting that...", "In general...")

---

## Structure Requirements

### SKILL.md Limits

| Metric | Limit |
|--------|-------|
| Body length | Under 500 lines |
| Reference depth | One level deep |
| Long file TOC | Required for >100 lines |

### Progressive Disclosure Pattern

```
Level 1: Metadata (always loaded)
├── name: ~5-10 words
└── description: ~100-200 words

Level 2: SKILL.md body (loaded on trigger)
├── Quick Start: ~50-100 lines
├── Core Workflow: ~100-200 lines
└── References: links to Level 3

Level 3: Reference files (loaded on demand)
├── Detailed guides
├── API references
└── Examples
```

### File Organization Patterns

**Pattern 1: Domain-specific**
```
skill/
├── SKILL.md
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

**Pattern 2: Feature-specific**
```
skill/
├── SKILL.md
└── references/
    ├── basic-usage.md
    ├── advanced-features.md
    └── troubleshooting.md
```

**Pattern 3: Content-type specific**
```
skill/
├── SKILL.md
├── references/
├── scripts/
├── assets/
└── examples/
```

### Path Requirements

Always use forward slashes:
- Good: `references/api-guide.md`
- Bad: `references\api-guide.md`

---

## Degrees of Freedom

### Freedom Level Selection

| Task Type | Freedom | Implementation |
|-----------|---------|----------------|
| Multi-approach valid | High | Text instructions |
| Preferred pattern | Medium | Parameterized scripts |
| Fragile/exact sequence | Low | Specific scripts |

### High Freedom Example

```markdown
## Data Visualization

Choose visualization based on data type:
- Time series: Line charts or area charts
- Comparisons: Bar charts or grouped bars
- Distributions: Histograms or box plots
- Relationships: Scatter plots or heatmaps

Consider audience and message when selecting.
```

### Medium Freedom Example

```markdown
## API Request Pattern

```python
def make_request(endpoint, method="GET", data=None):
    response = requests.request(
        method=method,
        url=f"{BASE_URL}/{endpoint}",
        json=data,
        headers=get_auth_headers()
    )
    response.raise_for_status()
    return response.json()
```

Customize BASE_URL and auth headers for your environment.
```

### Low Freedom Example

```markdown
## Database Migration

Execute exactly in this order:

1. `python manage.py makemigrations`
2. Review generated migration file
3. `python manage.py migrate --plan` (verify)
4. `python manage.py migrate` (execute)
5. `python manage.py check` (validate)

Do not skip steps or change order.
```

---

## Anti-Patterns

### Too Many Options

**Bad**: Presenting multiple alternatives without recommendation
```markdown
You can use:
- Option A: Does X
- Option B: Does Y
- Option C: Does Z
- Option D: Does W

Choose based on your needs.
```

**Good**: One recommendation with escape hatches
```markdown
Use Option A (recommended for most cases).

Alternative: Use Option B if you need feature X.
```

### Time-Sensitive Information

**Bad**: Date-based conditionals
```markdown
If using version 3.0 (released after Jan 2024), use new_api().
Otherwise, use legacy_api().
```

**Good**: Version-based or "old patterns" sections
```markdown
## Current Approach
Use new_api() for all API calls.

## Legacy Patterns (deprecated)
<details>
<summary>For versions before 3.0</summary>
Use legacy_api() instead.
</details>
```

### Inconsistent Terminology

**Bad**: Mixed terms
```markdown
Use the field property to set the attribute value on the column.
```

**Good**: Consistent terms
```markdown
Use the field property to set the field value.
```

### Deeply Nested References

**Bad**: Chain of references
```
SKILL.md → guide.md → advanced.md → details.md
```

**Good**: Flat structure
```
SKILL.md → guide.md
SKILL.md → advanced.md
SKILL.md → details.md
```

---

## Script Requirements

### Error Handling

**Bad**: Punt to Claude
```python
def process_file(path):
    data = open(path).read()  # May fail
    return parse(data)  # May fail
```

**Good**: Explicit handling
```python
def process_file(path):
    try:
        with open(path) as f:
            data = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}

    try:
        return {"success": True, "data": parse(data)}
    except ParseError as e:
        return {"error": f"Parse failed: {e}"}
```

### Execution Intent

**Clear execution intent**:
```markdown
Run `scripts/analyze.py input.csv` to generate the report.
```

**Clear reference intent**:
```markdown
See `scripts/analyze.py` for the algorithm details.
```

### Dependencies

Always list required packages:
```markdown
## Dependencies

- pdfplumber>=0.9.0
- pandas>=2.0.0
- requests>=2.28.0
```

---

## Testing Requirements

### Cross-Model Testing

Test skills with:
- Haiku (may need more detail)
- Sonnet (typical use)
- Opus (can handle more abstraction)

### Evaluation Scenarios

Create at least 3 evaluation scenarios:

```json
{
  "query": "Extract text from invoice.pdf",
  "expected_behavior": [
    "Opens PDF using appropriate library",
    "Extracts all text content",
    "Preserves table structure",
    "Returns formatted output"
  ]
}
```

### Pre-Publication Checklist

- [ ] Description has activation triggers
- [ ] SKILL.md under 500 lines
- [ ] One-level-deep references
- [ ] Forward slashes in paths
- [ ] No time-sensitive info
- [ ] Consistent terminology
- [ ] Concrete examples
- [ ] Scripts handle errors
- [ ] Config values justified
- [ ] Dependencies listed
- [ ] Multi-model tested
- [ ] 3+ evaluation scenarios
