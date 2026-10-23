---
description: Challenge a specification, plan, or candidate code diff with independent reviewer personas
argument-hint: "[spec-plan-or-diff]"
---

# Shipmate: Review

Use this command to perform independent, evidence-bound review of a specification, plan, or immutable code candidate before progressing.

Follow the complete procedure defined in [skills/review/SKILL.md](../skills/review/SKILL.md).

## Usage
Provide the target file, plan, or diff to review:
```
/review $ARGUMENTS
```

## Key Invariants
- Review is challenging and adversarial: find real edge cases, security issues, contract violations.
- Findings must include concrete evidence, triggering scenarios, and viable alternatives.
- Does not modify code, tickets, MRs, or pipeline state.
