# Opt-in SNS Langfuse onboarding

Use only when the engineer requests workstation tracking. Read the current
[SNS onboarding guide](https://gxsbank.atlassian.net/wiki/spaces/RGDEP/pages/2258862265/SNS+Langfuse+onboarding+Codex+and+GitHub+Copilot)
first; this procedure was checked against version 11 (18 October 2026). If inaccessible,
ask for its contents. Do not guess setup, install collectors during ordinary L3 work,
or make telemetry a delivery gate. Local run observations and SNS labels remain separate.

## Client and private setup

Inspect OS, terminal CLI and desktop-bundled CLI versions separately. Confirm CLI,
desktop or IDE scope. A bundled binary launched in a terminal is still a CLI test,
not desktop verification. The guide verifies Codex/Copilot CLI and describes a desktop pilot. The maintained
opt-in hooks below support Codex desktop/CLI and Claude Code; each runtime still needs
its own fresh-session verification.
Do not claim desktop success from CLI evidence or enable tracking on existing conversations.

Check for Peter's `~/.local/bin/sns-langfuse` or the guide's fallback script. If absent,
use documented manual setup, not an assumed installation or unpublished helper.
The bundled [native CLI launcher](../../scripts/sns_langfuse_codex.py) implements the
guide's native-span boundary using [official Codex OTel settings](https://developers.openai.com/codex/config-reference/).
It is not Peter's helper. The L3 entry helper below adds normalized action/plugin usage
without reading conversations; native spans alone do not establish skill usage.
For OMP or OpenCode, use the client adapters below, not the Codex launcher.

Preserve existing settings, hooks and telemetry destinations. Never display keys,
authentication headers or complete environments. If another exporter exists, retain it;
do not silently replace it to onboard SNS. This launcher declines conflicting configuration.

Create `~/.config/langfuse/sns.env` only if absent, outside Git, with directory mode 0700
and file mode 0600. Preserve an existing file. Ask the engineer to fill keys locally
from SNS project Settings → API Keys; never request them in chat.

```dotenv
LANGFUSE_BASE_URL=https://langfuse.stg.dakota.com.sg
LANGFUSE_HOST=https://langfuse.stg.dakota.com.sg
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_TRACING_ENVIRONMENT=development
```

Inspect `codex --help` for separate profile-file support. From the plugin root, run
`python3 scripts/sns_langfuse_codex.py profile` and save that non-secret template as a
new `sns-langfuse-native.config.toml` in the actual Codex home. Do not overwrite a profile.
The launcher reads keys as data, not shell code, and passes authentication only through
the child environment, with the exporter header cleared for model-launched shell commands.
No global config, shell profile or hook-trust records are edited.

Use Python 3.11+ (or Python 3.9+ with `tomli`). Install the self-contained launcher
outside worktrees/caches so branch cleanup cannot break tracking:

```bash
python3 scripts/sns_langfuse_codex.py install
~/.local/bin/sns-codex check
~/.local/bin/sns-codex test --user-id <your-username>
# Start the next fresh CLI session; OS username is the default user ID:
~/.local/bin/sns-codex
```

Installation replaces only the managed launcher/helper, preserving credentials and
profiles. Rerun `install` from an updated plugin to upgrade. It does not start tracking.
The launcher sets `langfuse.user.id` on native spans, not just a developer metadata label.
Verify the fresh trace's `userId` and its entry in the project's Users view; configuration
alone is not proof. Do not upload historical sessions to populate that view.
All adapters send `langfuse.environment=development` explicitly. Codex's `[otel]`
environment alone is not Langfuse attribution. Verify the first-class environment
on the new observation; existing `default` records are not rewritten or deleted.
Saved UI/hook state may remain in the native profile; privacy/exporter changes require review.

```bash
python3 scripts/sns_langfuse_codex.py check
python3 scripts/sns_langfuse_codex.py test
python3 scripts/sns_langfuse_codex.py run
```

`--codex-bin /absolute/path/to/codex` selects a CLI explicitly. On macOS the launcher
prefers the app-bundled CLI when present; this does not connect the desktop. Tests use
a fresh temporary directory and a harmless read-only session. A model rejection is
not exporter success; check client compatibility without changing normal model settings.

## Capture, verify and stop

Start with conversation-content capture disabled where supported. Native Codex uses
`log_user_prompt = false`, a trace exporter and a disabled transcript plugin; it does
not enable OTel log export. Check metadata as well as input/output for unwanted content.
Native spans can contain operation names, client/model identifiers, timing, errors,
local paths and raw counters. Do not promise complete redaction or cost coverage.

SNS tracking is metadata-only. Do not use `--full-content`, enable the transcript plugin,
or follow older guide examples that upload prompts, responses or tool bodies.
The bundled publisher rejects full-content before reading credentials or launching a client;
upstream archived examples are not an exception to this policy.
Never bypass hook approval.
Use a brand-new, non-forked session only; never export existing conversations or archives.
Copilot's documented manual setup starts with both content flags false.

Authenticate to SNS project `cmuwb2zds08uksx07mxkho9ov`, then read back the fresh
test's actual observations. For Langfuse v4 use bounded `GET /api/public/v2/observations`
queries, not the removed legacy traces endpoint; see [the official API](https://langfuse.com/docs/api-and-data-platform/features/public-api).
Match the new native session ID, client version and timestamps; check parent/child links,
capture level, keys/encoded authentication absent, and errors. Save the verified trace URL.
Configuration, health checks, transport-only spans or failed model calls alone are not success.

Native model-tagged internal spans are not all model calls. Missing normalized tokens,
cost or skill attribution stay unknown. Arbitrary variables do not prove SNS/Jira/MR mapping.
Do not present pilot traces as this workstation's verification evidence.

Handoff: configured clients, captured data, actual trace link, exact next command,
disable steps and remaining blockers. Ask only for the next manual step. Close the
opted-in CLI and launch normal `codex` without the SNS profile to stop this launcher;
its variables are process-local. Desktop verification remains pending until its native hooks are trusted and a fresh
chat produces the expected observations. Stopping does not delete uploads. No app/deployment changes.

## Codex desktop/CLI and Claude Code native hooks

Install from the installed Shipmate plugin root on macOS/Linux with Python 3.9+:

```bash
python3 scripts/sns_langfuse_hooks.py install --client codex --user-id firstname.lastname
python3 scripts/sns_langfuse_hooks.py install --client claude --user-id firstname.lastname
```

The helper copies regular files to `~/.local/share/sns-langfuse/hooks`, preserving
credentials and unrelated hooks/settings. It appends managed lifecycle handlers to
`$CODEX_HOME/hooks.json` (default `~/.codex`) or `$CLAUDE_CONFIG_DIR/settings.json`
(default `~/.claude`). The owner-only opt-in file is `~/.config/langfuse/hooks.json`;
each client has its own enabled flag and user ID. Installation does not edit native
hook trust records. Review the command and trust it through the client's normal hook
UI (Codex `/hooks`); never use a trust bypass. Start a new non-forked session afterward.
An existing desktop conversation is not a verification session.

SessionStart startup arms capture at the transcript's current end. Resume/fork/clear
are excluded; compaction preserves the armed session. Stop reads only new bounded
records from that same owned file. Claude creates its transcript after the prompt hook:
only the exact session-named path observed absent at startup can bind from its beginning,
and accepted Claude records must match that session ID and exclude sidechains.
Replacement, truncation or oversized segments
stop coverage. Recognized Codex numeric cumulative counters become turn deltas;
Claude assistant message usage is grouped by message ID. Transcript schemas are not
stable APIs: missing/unrecognized counters remain unknown. This is a turn aggregate,
not provider-call latency. Mixed models omit model attribution. Paired pre/post tool
hooks provide only tool names and timing; unsupported or unmatched events are omitted.
Input, output, reasoning, tool arguments/results and paths are never serialized.
The helpers do not compute prices; Langfuse may price a recognized model and usage.
Uploads use the fixed SNS endpoint, private credentials, a three-second timeout and
no redirects. Failures warn without blocking the client; observations are not replayed.
Local owner-only state prevents duplicate turns. Abrupt exit can lose a turn.

Verify a fresh CLI session separately from a fresh desktop chat. Read back GENERATION
rows for the new session with timing, user ID, model and actual token/cache fields;
confirm Input/Output are empty. Tool rows require a real supported tool invocation.
A successful HTTP response alone is not ingestion proof. Native internal spans from
`sns-codex` do not establish normalized generation coverage. Existing external exporters
remain independent and may duplicate observations; review them before enabling both.

Disable the selected client without removing unrelated settings:

```bash
python3 ~/.local/share/sns-langfuse/hooks/sns_langfuse_hooks.py disable --client codex
python3 ~/.local/share/sns-langfuse/hooks/sns_langfuse_hooks.py disable --client claude
```

Disable writes the opt-in false before removing managed handlers. Reinstall to upgrade;
start a fresh session after enabling or changing identity. Config writes preserve
unrelated fields and fail on observed concurrent edits; noncooperating writers cannot
be locked. Stopping capture does not delete existing uploads.

For reproducible HTTP failure checks, run `postman simulation run
postman/simulations/langfuse.sim.yaml --port 4917` from the marketplace root, then run
`SNS_SIMULATION_URL=http://127.0.0.1:4917/langfuse python3 -m unittest discover -s
plugins/shipmate/scripts -p test_sns_langfuse_hooks.py`. These local mocks use fake keys
and cover success, partial rejection, server errors and redirect refusal.

## OMP and OpenCode CLI

The existing plugin bundles a shared metadata-only exporter with OMP extension and
OpenCode **v2** event adapters. Local hook-loading probes passed with OMP 18.11.0 and
OpenCode 2.0.29. Upstream Pi, OpenCode v1, desktop and remote-server modes are not covered.
OMP also supports native OTel, but this adapter does not enable its exporters: constructing
an allowlisted payload avoids forwarding arbitrary native attributes or error bodies.

On macOS/Linux, explicitly install once from the plugin root (Python 3.9+, Node 22/Bun client runtime):

```bash
python3 scripts/sns_langfuse_clients.py --install
~/.local/bin/sns-omp --check
~/.local/bin/sns-opencode --check
~/.local/bin/sns-omp --user-id firstname.lastname
~/.local/bin/sns-opencode --user-id firstname.lastname
# Optional client arguments follow --; no resume/import/remote-server modes:
~/.local/bin/sns-opencode --user-id firstname.lastname -- run "Reply OK without tools"
```

Both wrappers default to the OS username and reuse the private `sns.env` above.
They install regular files under `~/.local/share/sns-langfuse/clients`, not disposable
worktrees/cache paths. Rerun installation to upgrade. Keys are read privately inside
the adapter, never injected into child environment variables or client config.
OMP loads an explicit extension and a process-local `autoResume: false` overlay.
OpenCode uses `--standalone` and appends a private adapter path to its process-local
`OPENCODE_CONFIG_CONTENT`, retaining existing inline options/plugins. No global hook,
config, model, permission or telemetry destination is replaced. Existing exporters
cause a request to review the conflict, not silent rerouting. Other installed plugins
remain independent; this adapter does not certify their capture policies.

Capture: user/client/session IDs, generation/tool counts, timestamps, tool/model/provider
identifiers, numeric token/cache counts and positive client-reported USD cost when available.
No prompts, responses, reasoning, tool arguments/results, files, paths, titles or error
text are serialized. Missing usage/cost stays absent, never guessed as zero; ambiguous zero
cost is omitted. Token counts retain each client's semantics, not a cross-client normalization. OMP generation
timing follows the message timestamp, not a claim of exact provider request latency.
Uploads are bounded, best-effort and deduplicated in memory; failures warn once without
blocking delivery or changing the client exit status. Abrupt termination or overflow can
lose observations. No transcript scan, historical backfill or retry archive is created.

Coverage is fresh top-level sessions and their directly observed events; resumed/forked
sessions and separate subagent processes are not established coverage. OpenCode v2 reports
`session.skill.activated`; OMP reports successful `read` of `skill://name[/SKILL.md]` instruction
URIs (including namespaced skills). OMP file-path/shell reads, user-command expansion and
unobserved loading methods remain uncovered. Skill text/results and paths are not uploaded.
Plugin ownership is not inferred from names for these clients. Do not infer engineer effort,
rework or delivery success from these counts.
Check fresh GENERATION/TOOL rows and `userId` in Langfuse before claiming full integration;
hook-loading tests and empty-session spans alone do not prove those rows are published.
Stop the wrapper and launch ordinary `omp`/`opencode` to disable this integration.
Installation alone does not capture anything, and stopping does not delete existing uploads.

Interface references: [OpenCode v2 plugins](https://opencode.ai/v2/docs/build/plugins/)
and the installed OMP ExtensionAPI `session_start`, `message_end`, `tool_execution_end`
contracts. Validate the installed client rather than assuming a version or API is unchanged.

## Publish observed skill/plugin sessions

Read the bundled [SNS skill](../../third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/SKILL.md.txt)
and [usage guide](../../third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/USAGE.md.txt).
All runtime modules and tests ship as regular files pinned in
[sources.json](../../third_party/sources.json). Use this bundled publisher rather than assuming
Peter's helper is installed. Archived references to his local installation, missing dashboard
scripts or unpublished distribution are provenance, not steps to execute. No external symlinks.

Only configure/launch when tracking is requested or an applicable explicit opt-in is recorded.
Normal Specify/Run/Review never installs hooks, changes telemetry routing or restarts clients.
Existing opted-in sessions may continue; missing capture is advisory. Keep labels, local run
metrics and remote session usage separate.

| Mode | Publishing coverage |
|---|---|
| Copilot CLI, content off | Explicit skill events; plugin owner only when emitted by client |
| Codex CLI via updated `sns-codex` | Actual L3 public entries via `sns_skill_usage.py`; known `shipmate` owner; other skills unknown |
| OMP adapter | Successful instruction URI reads; no inferred plugin owner |
| OpenCode v2 adapter | Explicit skill activation events; no inferred plugin owner |
| Codex desktop / unverified clients | No claimed usage coverage; CLI evidence does not verify desktop |

For requested onboarding, from the installed plugin root:

```bash
python3 third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/scripts/sns_langfuse.py doctor
python3 third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/scripts/sns_langfuse.py check
# Setup only with workstation-change authority; preserves normal config and existing keys:
python3 third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/scripts/sns_langfuse.py init
# Content-off example; use actual bounded run ID and SNS ticket, or omit Jira when absent:
python3 third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/scripts/sns_langfuse.py run copilot --run-id <run-id> --jira <actual-SNS-key>
```

For Codex use the native metadata-only launcher above, not the bundled legacy publisher's
full-content mode. Archived upstream instructions do not override this capture policy.
At L3 intake, follow the public-entry helper step in [run observations](../run-metrics.md)
only for an already opted-in session; it does not require or create a local run file.
The updated launcher supplies process-local opt-in and user identity; reinstall it after updating.
No installation or full-content mode is required during an L3 task. Other Codex skill usage stays
unknown, and this helper does not retrofit desktop tracking.
Never enable content capture just to populate widgets. Inspect existing exporters/settings first;
stop on conflicts rather than replacing destinations. Do not print keys or complete environments.

Use the native client session identity at fresh launch; do not create a local run record for correlation.
Nested phases/agents never start more collectors. Launching cannot retrofit this desktop session;
it is a next-session step, not a reason to restart completed work. Do not infer L3 from telemetry tags.

The legacy Copilot wrapper publishes normalized records on normal CLI exit. Codex L3 entries publish
at intake, and OMP/OpenCode publish on observed live events. Stable IDs and private
SQLite receipts support retry; widgets must count distinct sessions, not raw observation rows.
Forced termination, missing evidence and upload warnings mean incomplete/unknown coverage, not zero.
The wrapper preserves child exit status. No historical session scans or local run JSON uploads.

At L3 handoff report the result and apply eligible labels; legacy exit-time publishers remain pending
until exit. Do not replay records to improve counts. Verify fresh normalized
records, item/session/source IDs, capture level and the distinct-session dashboard query before
claiming publication. Retain the verified trace link and result in the conversation. An upload
acknowledgement alone is not readback. Never replay archives, invent usage or provision dashboards.

Widgets measure sessions with observed usage, not all invocations, delivery success, human effort,
cost or L3 adoption. Local JSON/CSV statistics remain separate. Superset Jira/GitLab ingestion is
platform-owned; labels do not prove payment-project coverage in that dashboard.
