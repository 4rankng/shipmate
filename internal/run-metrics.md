# Langfuse metrics and legacy local utility

Langfuse is the source for AI-session metrics. Use verified observations for timing, model,
token/cache usage and cost when available. If telemetry is missing or incomplete, report it
as unavailable; never create a local metrics file as a fallback or invent values.
Do not estimate missing costs or reconstruct official metrics from local workflow files.

Local run records are off by default. Do not create/update local run JSON/CSV, invoke
`scripts/run_metrics.py`, or show record links or capture-disabled notices during ordinary
Specify/Run/Review work. Keep workflow status, decisions, MR/check results and next actions
in the conversation. Missing metrics are never an admission, review, delivery, or resume gate.

The legacy utility remains only for compatibility with existing files and explicitly requested
local-file operations. Do not start or resume collection just because old files exist.
It is not part of the workflow's metrics collection or a replacement for Langfuse.
Existing files need not be migrated, uploaded or deleted to continue work.

## Already opted-in skill-session reporting

If the engineer explicitly requests SNS Langfuse onboarding, use the
[workstation procedure](sns-langfuse/PROCEDURE.md). Ordinary Specify/Run/Review intake does
not enable external telemetry. No local run file is required for publishing.

For an already opted-in session, at each actual public L3 entry, including nested Specify/Review,
call the helper once with that entry's name, not the list of available skills:

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/sns_skill_usage.py" --skill run
```

Use `specify` or `review` for those entries. Resolve `PAYMENT_PLUGIN_ROOT` from the installed
skill's ancestor containing `plugin.json`. The helper is inert outside explicitly opted-in
`sns-codex` sessions. It uses the host's `CODEX_THREAD_ID`, never a fabricated or local workflow
run ID; missing identity/credentials are advisory. Private receipts deduplicate each observed
session/item across phases and retries. Never enable content capture to fill missing metrics.
Do not enumerate installed skills or report internal procedures as public skills. Honor telemetry
opt-out by skipping this call. OMP/OpenCode adapters observe skill events themselves; do not
manually publish duplicates. Configuration or an upload acknowledgement alone is not ingestion
proof; verify fresh remote observations before reporting publication or usage metrics.

Langfuse session observations do not establish human effort, delivery success or L3 completion.
Use the actual GitLab/Jira evidence for delivery status and preserve unknown values as unknown.
