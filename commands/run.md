---
description: Deliver requirements through TDD into a verified draft merge request
argument-hint: "[jira-key-or-requirement-file]"
---

# Shipmate: Run

Use this command to execute engineering work from Jira or local requirements, delivering verified code through Test-Driven Development and risk-proportional review to a draft MR.

Follow the complete procedure defined in [skills/run/SKILL.md](../skills/run/SKILL.md).

## Usage
Provide the Jira ticket key or local specification file:
```
/run $ARGUMENTS
```

## Key Invariants
- Read workflow policy and coding guidelines first.
- Strict TDD: Write failing test first, see it fail, then implement minimal code.
- Run multi-persona reviews on specification, plan, and candidate diff.
- Keep commits atomic and finish the development branch cleanly.
