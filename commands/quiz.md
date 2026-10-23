---
description: Interactive understanding quiz and report for a Jira ticket or merge request
argument-hint: "[jira-key-or-mr-url]"
---

# Shipmate: Quiz

Use this command to check comprehension of a Jira ticket, merge request, or branch through an interactive diagnostic quiz and a screenshot-ready understanding report.

Follow the complete procedure defined in [skills/quiz/SKILL.md](../skills/quiz/SKILL.md).

## Usage
Provide the Jira ticket key or GitLab MR identifier:
```
/quiz $ARGUMENTS
```

## Key Invariants
- Mirror, not judge: teaches as well as tests.
- One mode for everyone; no role assumptions.
- Concrete questions grounded in source evidence.
- Generates understanding report upon completion.
