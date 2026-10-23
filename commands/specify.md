---
description: Prepare a reviewed engineering specification and technical contract from Jira or local requirements
argument-hint: "[jira-key-or-requirement-file]"
---

# Shipmate: Specify

Use this command to turn intent, Jira tickets, or local requirement documents into an implementation-ready, reviewed engineering contract.

Follow the complete procedure defined in [skills/specify/SKILL.md](../skills/specify/SKILL.md).

## Usage
Provide the Jira ticket key (e.g. `PROJ-123`) or local requirement file path:
```
/specify $ARGUMENTS
```

## Key Invariants
- Investigate facts in the codebase first before asking questions.
- Ask one material decision question at a time using concrete scenarios.
- Cover both requirements and technical design.
- Local run records are off by default.
