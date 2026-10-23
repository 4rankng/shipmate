---
name: confluence
description: Use when reading, creating, updating, deleting, searching or listing a Confluence page or space
---

# Confluence

Derive `PAYMENT_PLUGIN_ROOT` from this procedure's installed path (the directory containing
`plugin.json`) before running bundled commands; do not assume a host-provided plugin-root variable.

Confluence Cloud REST API v2, using the same Atlassian credentials as the `jira` procedure.
The API path is `/wiki/api/v2/` — **not** `/rest/api/` like Jira.

## Authority

Reading, searching and listing are unattended. Creating, updating, retitling or deleting a page
changes shared team documentation — do it only when explicitly asked, and never overwrite a page
you have not first fetched and read.

## Actions

| Intent | Command |
|--------|---------|
| View a page | `get 12345 [--body-only]` |
| List child pages | `children 1835696137` |
| Search by title | `search "payment flow"` |
| List a space | `space DEV` |
| Create | `create --space DEV --title "T" --body-file body.html` |
| Update body | `update 12345 --expected-body-file baseline.html --body-file body.html --verify` |
| Retitle | `title 12345 "New Title"` |
| Delete (trash) | `delete 12345` |

Request/response shapes for each action: `references/actions.md`.

## Never hand-roll the call

Every request goes through the CLI. Do not write `curl`, do not write an inline
`python3 -c` that builds an `Authorization` header, and do not read the API token into a shell
variable. A credential on a command line is a credential in shell history, in the agent
transcript, and in any CI log that captures the command.

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" [--region sg|my] <command> [args]
```

The CLI resolves credentials from the environment inside its own process. It accepts a path and a
payload — never a header, never a token argument.

Page bodies are passed as `--body-file`, not as an argument, so large HTML stays out of the
process listing and shell history.

## Updating a page

Always fetch first, edit the returned body, then send the full new body — updates are replacements,
not patches. Version is incremented automatically. Never place credentials, customer identifiers
or production payloads into page content.

Persist the exact baseline without printing the body, then require that baseline and semantic
readback verification on the update:

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" get <page-id> \
  --body-format storage --body-output-file <baseline.html>
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" update <page-id> \
  --expected-body-file <baseline.html> --body-file <candidate.html> --verify
```

The mandatory pre-write guard tolerates trailing whitespace only and aborts if anyone changed the
stored page. Mandatory verification reads back storage and normalizes only generated wrapper IDs,
outer-markup entity/inter-tag formatting, and direct code-macro parameter order. CDATA,
plain-text, `pre`, and `code` payload bytes remain exact; any semantic difference fails.

Before publishing technical prose, read and apply the bundled sibling
[`unslop`](../unslop/PROCEDURE.md) procedure. Preserve storage markup, macro parameters, code, commands,
identifiers, links, citations, and quoted source text exactly.

## Notes

- Page IDs are numeric strings.
- Body content uses Confluence storage format (HTML-like).
- `body-format` options: `storage`, `atlas_doc_format`, `view`.
- Paginate with the `cursor` query param from `_links.next`.

## Errors

| Code | Cause | Fix |
|------|-------|-----|
| `401` | bad credentials | check `SG_JIRA_USERNAME` / `SG_JIRA_API_KEY` (or `MY_JIRA_*`) |
| `404` | not found, no permission, **or a rejected credential** — Confluence v2 returns the same opaque `NOT_FOUND` for an unauthenticated request | run `doctor.py --group jira --live`; then verify the ID and region |
| `400` | bad request body | check required fields |
| `413` | body too large | reduce page content size |

A token rotated in your shell rc file *after* the agent process started stays
stale in that process's environment. `confluence_cli.py` re-reads the rc files
and retries once on `401`/`404`, so most of these self-heal; if the retry also
fails, the page genuinely is not visible to that account on that site.
