# SNS labels at L3 handoff

Read the bundled [SNS labelling skill](../../third_party/gxs-ai-platform/sns/sns-l3-labelling/SKILL.md.txt)
and apply its eligibility, additive-update and readback rules. It comes from GXS AI Platform
[MR !269](https://gitlab.com/gx-regional/dakota/ai-platform/skills/-/merge_requests/269), pinned in
[sources.json](../../third_party/sources.json). No external installation or symlink is needed.

## Caller context

Call once as the final bookkeeping step of `run`, before its user handoff. Supply the current
run's explicit L3 execution context, concrete Jira keys, canonical GitLab project/MR references,
and evidence linking each MR to the ticket it delivers. Nested Specify/Review do not call this
procedure separately. A standalone Specify or read-only Review does not authorize tagging.

Follow the upstream scope: only `RGWEALTH`, `RGPAYM` and `RGCARDS` issues and their associated MRs
materially worked on by this L3 execution. Skip manual/L2 work, reference-only items, other
projects and runs without Jira. Do not add Jira or ask for a ticket to make local Markdown work
eligible. An uncertain execution level or association is a skipped target with a reason; do not
infer eligibility from a branch name, an old label or use of AI. A later measured L2 autonomy
classification is not corrected by tagging: if the run is known to be L2, skip SNS labels.

An eligible Run includes scoped authority to add the two tracking labels to its verified targets.
Respect an explicit opt-out or denied access. Existing `l3-workflow` labels remain unchanged.
These labels indicate participation, not successful completion, approval or telemetry coverage.

## Apply and report

Add both `sns-l3` and `l3-agent`, retaining every unrelated label. Use available authenticated
Jira/GitLab tools; prefer Jira's additive label operation and GitLab `add_labels`. If the tool
only supports replacement, re-read the labels immediately before writing their union. Avoid
writing already-labelled targets. Use a scoped label-definition operation only if the project
requires it and permissions permit it; never change project settings to make tagging work.

The bundled Jira CLI supports additive labels with its own readback:
`scripts/jira_cli.py add-label <key> sns-l3` and `scripts/jira_cli.py add-label <key> l3-agent`
(run with `python3` from the resolved plugin root). Verify the live issue contains both after
these operations; a successful first command alone is a partial update. For GitLab, update the
verified project/MR with `add_labels=sns-l3,l3-agent`, then read the live MR's labels.

Read each target back to confirm both labels. On a transient error, retry at most once after
re-reading; stop that target on an access/validation error and continue the other eligible targets.
No ticket/MR creation, Jira comment, description/status change, MR approval/merge or telemetry
upload is part of this step. If no MR exists, tag the eligible Jira only and report the absent MR.

Return each target's link, `applied`, `already present`, `skipped`, `failed` or `unverified`, and a
short reason where needed. Report partial success accurately. Keep delivery/review/CI status as
observed; tagging failure is advisory and must not delay the engineering handoff or trigger a
rerun of completed phases. On resume, read live labels and add only those still missing.
