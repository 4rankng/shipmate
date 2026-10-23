---
description: Explain a Jira ticket, merge request, or local branch in progressive layers
argument-hint: "[jira-key-or-mr-url]"
---

# Shipmate: Walkthrough

Use this command to guide the reader through a Jira ticket, GitLab merge request, or local branch in clear conceptual layers (intent, architecture, changes, and verification).

Follow the complete procedure defined in [skills/walkthrough/SKILL.md](../skills/walkthrough/SKILL.md).

## Usage
Provide the Jira ticket key or GitLab MR URL/identifier:
```
/walkthrough $ARGUMENTS
```

## Key Invariants
- Walkthrough is a learning aid, not an approval or correctness verdict.
- Purely read-only: never edits code, comments, approves, or pushes.
- Explain in layers, citing verified source revisions.
