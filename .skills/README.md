# Skills

Local skills for skillops.

## Structure

```
.skills/
└── experimental/              # Work-in-progress and experimental skills
    ├── git-branch-cleanup/    # Clean up local git branches
    ├── opus-4-5-migration/    # Claude model migration guide
    └── skill-evaluator/       # Evaluate skills against best practices
```

## Maturity Levels

| Directory | Status | Description |
|-----------|--------|-------------|
| `experimental/` | WIP | Under development, may change significantly |
| (root) | Stable | Ready for production use |

## Usage

```bash
# Use with SkillPort CLI
skillport --skills-dir .skills list

# Or set environment variable
export SKILLPORT_SKILLS_DIR=.skills
skillport list
```

## Adding New Skills

1. Choose the appropriate directory based on maturity
2. Create `<skill-name>/SKILL.md` with YAML frontmatter
3. Run `skillport validate <skill-name>` to check
