# Scoring Rubric Reference

Complete scoring rubric with detailed criteria for each score level.

## Table of Contents

1. [Scoring Methodology](#scoring-methodology)
2. [Naming Rubric](#naming-rubric)
3. [Description Rubric](#description-rubric)
4. [Content Quality Rubric](#content-quality-rubric)
5. [Structure Rubric](#structure-rubric)
6. [Degrees of Freedom Rubric](#degrees-of-freedom-rubric)
7. [Anti-Pattern Scoring](#anti-pattern-scoring)
8. [Edge Cases](#edge-cases)
9. [Score Calculation](#score-calculation)

---

## Scoring Methodology

### Weighted Average Formula

```
Final Score = (N × 0.10) + (D × 0.20) + (C × 0.30) + (S × 0.25) + (F × 0.10) + (A × 0.05)

Where:
N = Naming score (1-5)
D = Description score (1-5)
C = Content Quality score (1-5)
S = Structure score (1-5)
F = Degrees of Freedom score (1-5)
A = Anti-Pattern score (1-5)
```

### Weight Rationale

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Content Quality | 30% | Most impactful for skill effectiveness |
| Structure | 25% | Critical for context management |
| Description | 20% | Primary trigger mechanism |
| Naming | 10% | Important but less impactful |
| Freedom | 10% | Affects reliability |
| Anti-Patterns | 5% | Deduction-based |

---

## Naming Rubric

### Score 5: Excellent

All criteria met:
- [x] Gerund form (verb + -ing)
- [x] Clear, memorable, descriptive
- [x] Under 64 characters
- [x] Only lowercase, numbers, hyphens
- [x] No reserved words
- [x] Immediately suggests purpose

**Examples**: `processing-pdfs`, `analyzing-code`, `building-dashboards`

### Score 4: Good

Most criteria met:
- [x] Follows conventions
- [x] Descriptive
- [ ] Not gerund form or slightly unclear

**Examples**: `pdf-processor`, `code-analysis`, `dashboard-builder`

### Score 3: Acceptable

Basic criteria met:
- [x] Valid format
- [ ] Vague or could be clearer
- [ ] Missing action indication

**Examples**: `pdf-tool`, `code-helper`, `data-skill`

### Score 2: Needs Improvement

Issues present:
- [ ] Somewhat misleading or confusing
- [ ] Too generic
- [ ] Awkward naming

**Examples**: `my-skill`, `tool-v2`, `helper`

### Score 1: Fails Requirements

Critical violations:
- [ ] Exceeds 64 characters
- [ ] Invalid characters (uppercase, spaces, underscores)
- [ ] Contains reserved words
- [ ] Contains XML patterns

**Examples**: `ClaudeHelper`, `anthropic-tool`, `my_skill`, `<skill>`

---

## Description Rubric

### Score 5: Excellent

All criteria met:
- [x] Under 1024 characters
- [x] Third person perspective
- [x] Clear functionality statement
- [x] Specific activation triggers (when to use)
- [x] Scope is clear
- [x] No XML tags

**Example**:
```
Transforms PDF documents into editable formats. Extracts text, tables, and
images while preserving structure. Use when: (1) converting PDFs to text/markdown,
(2) extracting tabular data, (3) parsing form fields, or (4) analyzing document
structure.
```

### Score 4: Good

Most criteria met:
- [x] Proper format
- [x] Clear functionality
- [ ] Triggers present but could be more specific
- [ ] Scope implied but not explicit

**Example**:
```
Extracts content from PDF documents including text, tables, and images.
Use for PDF processing and conversion tasks.
```

### Score 3: Acceptable

Basic criteria met:
- [x] Valid description
- [ ] Missing specific triggers
- [ ] Generic functionality statement
- [ ] Third person but vague

**Example**:
```
Processes PDF documents. Handles text extraction and format conversion.
```

### Score 2: Needs Improvement

Issues present:
- [ ] Too brief
- [ ] Wrong perspective
- [ ] No activation triggers
- [ ] Unclear purpose

**Example**:
```
Use this to work with PDFs.
```

### Score 1: Fails Requirements

Critical violations:
- [ ] Empty or near-empty
- [ ] Over 1024 characters
- [ ] Contains XML tags
- [ ] Completely unhelpful

**Example**:
```
PDF skill.
```

---

## Content Quality Rubric

### Score 5: Excellent

All criteria met:
- [x] Highly concise, no wasted tokens
- [x] Assumes Claude's intelligence
- [x] Actionable instructions
- [x] Specific examples (not generic)
- [x] High information density
- [x] No filler phrases

**Indicators**:
- Every sentence adds value
- Code examples are copy-paste ready
- No explanations of basic concepts

### Score 4: Good

Most criteria met:
- [x] Generally concise
- [x] Mostly actionable
- [ ] Minor verbosity in places
- [ ] Some examples could be more specific

### Score 3: Acceptable

Basic criteria met:
- [x] Functional content
- [ ] Some unnecessary explanations
- [ ] Moderate redundancy
- [ ] Mix of good and verbose sections

### Score 2: Needs Improvement

Issues present:
- [ ] Overly verbose
- [ ] Explains basic concepts
- [ ] Low information density
- [ ] Generic examples

### Score 1: Fails Requirements

Critical violations:
- [ ] Extremely bloated
- [ ] Explains what Claude already knows
- [ ] Copy-pasted documentation without curation
- [ ] Mostly filler content

---

## Structure Rubric

### Score 5: Excellent

All criteria met:
- [x] SKILL.md under 500 lines
- [x] Clear progressive disclosure
- [x] One-level-deep references
- [x] Long files have TOC
- [x] Forward slashes only
- [x] Logical file organization
- [x] No orphan files

### Score 4: Good

Most criteria met:
- [x] Under 500 lines
- [x] References used appropriately
- [ ] Organization could be slightly better
- [ ] One or two files without TOC

### Score 3: Acceptable

Basic criteria met:
- [x] Valid structure
- [ ] Approaching 500 lines
- [ ] Some unnecessary content in SKILL.md
- [ ] References could be better organized

### Score 2: Needs Improvement

Issues present:
- [ ] Over 500 lines
- [ ] Poor reference organization
- [ ] Nested references (2+ levels)
- [ ] Missing logical splits

### Score 1: Fails Requirements

Critical violations:
- [ ] Massively over limit
- [ ] No progressive disclosure
- [ ] Deeply nested references
- [ ] Chaotic organization

---

## Degrees of Freedom Rubric

### Score 5: Excellent

Perfect calibration:
- [x] High freedom for flexible tasks
- [x] Medium freedom for pattern-based tasks
- [x] Low freedom for fragile operations
- [x] Clear rationale for freedom level

### Score 4: Good

Generally appropriate:
- [x] Freedom levels mostly match task types
- [ ] One or two slight mismatches
- [ ] Could be more explicit about rationale

### Score 3: Acceptable

Functional:
- [x] Works in most cases
- [ ] Some mismatched freedom levels
- [ ] Scripts where text would suffice (or vice versa)

### Score 2: Needs Improvement

Problematic:
- [ ] Too rigid for flexible tasks
- [ ] Too loose for fragile operations
- [ ] Inconsistent approach

### Score 1: Fails Requirements

Critical mismatch:
- [ ] Completely wrong freedom level
- [ ] Dangerous for fragile operations
- [ ] Overly constrained for creative tasks

---

## Anti-Pattern Scoring

### Calculation Method

Start with base score of 5, deduct for each anti-pattern:

| Anti-Pattern | Deduction |
|--------------|-----------|
| Too many options without recommendation | -1 |
| Time-sensitive information | -1 |
| Inconsistent terminology | -1 |
| Windows-style paths | -1 |
| Deeply nested references | -2 |
| Scripts punt error handling | -1 |
| Magic numbers without justification | -1 |

**Formula**: `Anti-Pattern Score = max(1, 5 - total_deductions)`

### Examples

**No anti-patterns**: 5 - 0 = 5
**Minor issues**: 5 - 2 = 3
**Multiple issues**: 5 - 4 = 1 (minimum)

---

## Edge Cases

### Minimal Skill

A skill with only SKILL.md and no references:

- If appropriate for scope: No penalty
- If content is cramped: Deduct from Structure

### New Domain

For skills introducing new concepts to Claude:

- Explanatory content IS necessary
- Judge conciseness relative to what's truly needed
- Domain-specific terms should be defined

### Script-Heavy Skills

Skills that are primarily scripts:

- SKILL.md can be shorter
- Focus evaluation on script quality
- Error handling especially important

### Reference-Heavy Skills

Skills with extensive reference material:

- SKILL.md should be navigation-focused
- References must be well-organized
- Progressive disclosure more critical

---

## Score Calculation

### Example Calculation

```
Skill: pdf-processor

Scores:
- Naming: 4 (good but not gerund)
- Description: 5 (excellent)
- Content Quality: 4 (minor verbosity)
- Structure: 5 (excellent)
- Freedom: 4 (appropriate)
- Anti-Patterns: 4 (one minor issue)

Calculation:
(4 × 0.10) + (5 × 0.20) + (4 × 0.30) + (5 × 0.25) + (4 × 0.10) + (4 × 0.05)
= 0.40 + 1.00 + 1.20 + 1.25 + 0.40 + 0.20
= 4.45

Final Score: 4.45/5.0 (Good - Minor improvements recommended)
```

### Quick Reference

| Final Score | Rating | Action |
|-------------|--------|--------|
| 4.5 - 5.0 | Excellent | Ready for publication |
| 4.0 - 4.4 | Good | Minor improvements |
| 3.0 - 3.9 | Acceptable | Several improvements |
| 2.0 - 2.9 | Needs Work | Major revision |
| 1.0 - 1.9 | Poor | Redesign needed |
