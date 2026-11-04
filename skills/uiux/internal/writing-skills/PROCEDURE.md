---
name: writing-skills
description: Use when creating, adapting, reviewing, or releasing an agent skill that will guide repeatable behavior across repositories or teams
---

# Writing Skills

## Core principle

Treat skill authoring as test-driven behavior engineering. A skill is deployable control logic expressed in instructions; it needs failing scenarios, minimal corrective guidance, regression evaluation, and governed release.

## RED: establish the baseline

Before writing or changing a skill:

1. write down at least two scenarios in machine-local verification artifacts;
2. include normal use and a pressure or adversarial case;
3. run each scenario without the proposed guidance, or against the current skill;
4. record the exact omission, wrong output shape, unsafe action, or rationalization;
5. classify the failure:
   - missing required structure;
   - incorrect technique;
   - skipped discipline under pressure;
   - unsafe authority or data handling;
   - discovery failure.

Do not author guidance for a failure you cannot reproduce or explain.

## GREEN: write the smallest effective skill

Use this structure:

```markdown
---
name: lower-kebab-case
description: Use when observable trigger conditions apply
---

# Skill title

## Core principle
...
```

Requirements:

- directory and `name` match, and the name fits `^[a-z0-9]+(-[a-z0-9]+)*$` (the Agent Skills
  standard rule: 1–64 chars, no leading/trailing hyphen, no doubled hyphens);
- description starts with `Use when`, front-loads the trigger conditions, states what the skill
  does and when to use it, and ends with near-miss negatives ("Not for …") for the contexts that
  share its keywords but need something else; keep it within the standard's 1,024-character cap;
- keep SKILL.md under 500 lines and about 5,000 tokens; clients drop content beyond that after
  compaction — move heavier material to linked files and load them only at the moment they apply;
- conventional subdirectories: `scripts/` for self-contained executables with good errors,
  `references/` for on-demand documents, `assets/` for templates and data;
- guidance uses precise observable conditions;
- output contracts use positive structure and ordering;
- discipline rules state hard boundaries and common rationalizations;
- one high-quality example is better than many shallow examples;
- supporting files are used only for reusable tools or heavy reference;
- privileged actions, protected data, and untrusted content are addressed explicitly.

Validate structure with the Agent Skills reference validator when available
(`skills-ref validate <skill-dir>`); `scripts/test_skill_frontmatter.py` enforces the same
name and description rules offline.

## REFACTOR: close demonstrated loopholes

When evaluation reveals a new failure:

- add the exact case to the scenario suite;
- adjust the smallest relevant section;
- avoid broad new rules that degrade unrelated behavior;
- rerun normal and adversarial cases;
- inspect variance across fresh sessions.

For high-risk discipline wording, use multiple fresh runs. A single compliant response is weak evidence.

## Security review

A skill requires additional security review when it:

- grants or pre-approves tools;
- invokes hooks or scripts automatically;
- configures MCP or network access;
- handles credentials or protected data;
- changes authentication, authorization, cryptography, or audit behavior;
- can push, comment, merge, deploy, release, or control pipelines;
- imports third-party text or executable content.

For third-party guidance, pin an immutable repository revision, read the selected
source and every retained dependency completely, copy the exact license, record
upstream and adapted SHA-256 digests, and document reviewer and review date.
Never import executable support files, active configuration, hooks, MCP,
credentials, automatic fetch behavior, or upstream write authority.

Prefer technical enforcement in permissions, CI, branch protection, schemas, and allowlists. Skills should guide judgment, not impersonate a security boundary.

## Deployment checklist

Before release:

- structural validator passes;
- all skill scenarios pass;
- description reliably triggers discovery;
- no duplicate name is unintentionally shadowed;
- third-party licenses and notices are current;
- changelog and semantic version are updated;
- CODEOWNERS and security approve;
- rollback version is known;
- pilot results are recorded.

Do not create a batch of untested skills and validate only the catalog. Each skill needs its own evidence.
