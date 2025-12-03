# Evaluation Scenarios

Example scenarios for testing the skill-evaluator skill.

## Scenario Format

Each scenario is a JSON file with:

```json
{
  "name": "Scenario name",
  "skills": ["skill-evaluator"],
  "query": "User request that triggers evaluation",
  "context": "Additional context about the skill being evaluated",
  "expected_behavior": [
    "Expected action 1",
    "Expected action 2"
  ],
  "success_criteria": [
    "Success criterion 1",
    "Success criterion 2"
  ]
}
```

## Available Scenarios

- `basic-skill-evaluation.json` - Basic skill evaluation workflow
- `problematic-skill-evaluation.json` - Evaluating a skill with multiple issues
