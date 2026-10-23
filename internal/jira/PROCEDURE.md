---
name: jira
description: Use when reading, labeling, transitioning, replacing the description of, listing or searching a Jira ticket in the SG or MY instance
---

# Jira

Derive `PAYMENT_PLUGIN_ROOT` from this procedure's installed path (the directory containing
`plugin.json`) before running bundled commands; do not assume a host-provided plugin-root variable.

Every operation goes through one CLI:

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" <command> [args] [--region sg|my]
```

## Authority

Reading, listing and searching are unattended. Idempotently labeling and transitioning your *own*
ticket as part of a delivery workflow is unattended.

Jira comments are read-only requirement evidence. Never create, edit, or delete a Jira comment,
including for specification approval, blockers, review evidence, MR links, or completion handoff.
Keep those records in the machine-local manifest and terminal chat report. Do not bypass this
boundary with direct REST calls or `jira_client` helpers.

`set-description` is **not** unattended: it overwrites the whole description and Jira keeps no
backup. Run it only on the ticket the user named in the request that asked for it to be rewritten
(this is the sanctioned path `specify` uses to write a completed spec back to that ticket),
only after reading the full existing description with
`view <KEY> --max-description 100000`, and only after echoing that original text in chat so the
user can restore it. For Specify rewrites, follow its local-backup and concise-approved-draft
procedure instead of echoing a massive original; share the backup location before writing.
Never run it on a ticket you were not asked to rewrite.

Do not transition someone else's ticket, close a ticket, bulk-move children, or overwrite someone
else's description without being asked to.

## Commands

| Intent | Command |
|--------|---------|
| View a ticket | `view TSE-1170` |
| Recent comments | `comments TSE-1170 [--limit 10]` |
| Complete comment inventory | `comments TSE-1170 --all --json` |
| Optional requirement audit export | `snapshot TSE-1170 --expected-updated <timestamp> [--decision-comment-id 12345]` |
| Add and verify a label | `add-label TSE-1170 l3-workflow` |
| Replace the description | `set-description TSE-1170 --text "..."` or `--file description.md` (destructive, no backup) |
| Transition status | `move TSE-1170 "In Development"` |
| Bulk-move children | `move-children RGPAYM-2582 "Ready for Production"` |
| My tickets | `list [--limit 20]` |
| Search | `search "payment failed"` or `search --jql '<JQL>'` |

`move` resolves multi-hop paths itself: it tries a direct transition, then BFS through
intermediate states, and supplies `resolution` only for resolving targets.

`snapshot` is an optional audit export containing the raw full summary/description, only the
explicitly selected decision comments sorted by ID, Jira's observed `updated` timestamp, and a
content digest. It is not an admission or design lock. A later Jira edit is classified semantically:
formatting-only changes continue, material clear changes receive fresh reviews, and vague or
conflicting changes block. Never build an audit digest from rendered/truncated `view` or paged
`comments` output.

Use `comments --all --json` when comments may contain current requirement decisions. It follows
every Jira comment page and rejects duplicate or incomplete pagination. The ordinary comments view
is recent and human-readable, so it is not sufficient when complete comment evidence is needed.

## Region

Auto-detected from the ticket prefix; `--region` overrides.

| Prefix | Region | Instance | Credentials |
|--------|--------|----------|-------------|
| `TSE-*`, `SHIPRM-*`, `RGPAYM-*`, `TCI-*` | SG | `gxsbank.atlassian.net` | `SG_JIRA_DOMAIN/USERNAME/API_KEY` |
| `TS-*` (no E), `CM-*` | MY | `gxbank.atlassian.net` | `MY_JIRA_DOMAIN/USERNAME/API_KEY` |

SG fallback: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`. Check with:

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/doctor.py" --group jira
```

## Workflows

Transitions available depend on issue type.

- **Story / Regional User Story:** Backlog → Ready for Dev → In Development → Code Review →
  Ready for QA → In Testing → Ready for UAT → Sign-Off → Ready for Production → Done
- **Defect:** In Backlog → In Development → Blocked → Closed (Closed needs a `resolution`)

When pathfinding fails, move to **Blocked** first — it is a hub state with many outgoing
transitions, and most targets become reachable from there.

## Specification description style

Before replacing a Jira specification description, read and apply the bundled sibling
[`unslop`](../unslop/PROCEDURE.md) procedure. For Specify-generated drafts, follow
[Specify's format and validation](../../skills/specify/SKILL.md):

- `Problem / Context`: one or two sentences.
- Optional `Definitions`: at most six verified `**Term**: meaning` bullets, only for a strong reason.
- `Objective`: one or two plain sentences on what we want to achieve.
- `Acceptance Criteria`: short Given/When/Then bullets with stable AC IDs and optional short titles.
- Optional `Out of Scope`: at most three exclusions or work owned elsewhere, with owner or ticket.
- Optional `Technical Notes`: at most three bullets for essential design constraints.

Aim for at most 1,200 characters and fewer than 150 words, including headings and links. This is
a target, not a hard cap: exceed it only for a strong reason stated beside the draft. Run
Specify's validator before presentation and publication. Preserve the
full original in a local backup, not inside the replacement. Retain human approval, concurrent-edit
reconciliation and readback. These limits do not change the generic Jira CLI or reject legacy tickets.

To replace a shorthand summary with an approved plain-language one, record the current summary
in the local backup, then run `set-summary <KEY> --summary "<approved>"`. It rejects empty,
multi-line or over-255-character values and reads back the stored summary before reporting success.

Use the fewest rows that preserve intent and observable behavior. The bundled `set-description`
renderer converts Markdown tables, bold labels, and inline code into native ADF. Read the stored
description back after every write. Never put credentials, customer identifiers, internal review
hashes, or production payloads in the description.

## Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `401` | bad credentials, or a token rotated in your rc file after this process started | `jira_client` re-reads the rc files and retries once; if it still fails run `doctor.py --group jira --live` |
| `404` | wrong key or wrong instance | verify region detection (`TS-*` → MY, `TSE-*` → SG) |
| `No transitions` | final state or no permission | check workflow permissions |
| `400` on transition | screened transition needs more fields — MY `Closed` needs `customfield_10045` (RCA); `resolution` is only valid for resolving targets | pass the extra fields explicitly |
| `Expecting value` on POST | API returned 204 No Content, which is success | already handled by `jira_client` |
| path not found | issue type's workflow has no route to the target | try `Blocked` as a hub |
