# Understanding report

This is screenshot-ready evidence of a quiz session, not approval, independent review evidence,
verified identity or proof of general understanding. Nothing leaves the chat automatically.

## Score and completeness

Freeze the answer key and each question's topic before question one. Score only explicit human
responses to neutral questions. Invalidate and replace any question whose answer was hinted or
recommended before submission; never credit a default selection or leaked answer. Record the
number of replaced questions in the report when any were replaced. If a contaminated question
cannot be replaced, report Not assessed and explain the issue without a scored final result. Count each question's first submitted answer; later
corrections after explanations do not replace it. Correct, wrong and skipped are disjoint.
Unanswered questions after `stop` remain unanswered. Score = correct / total planned questions,
rounded with `Math.round(correct / total * 100)`. Skips earn no credit and stay in the denominator.
Never average attempt scores or present a partial quiz as completed.

Use the bundled `python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/quiz_report.py"` with private JSON on
stdin to calculate counts, topic
results and levels. Each question has `id`, `topic`,
`correct` (A–D index 0–3) and `answer` (first submitted index, `"skip"`, or `null` if unanswered).
Project only those four fields from each frozen question record; do not pass the full record
with question text, options and explanation, because the helper rejects extra fields. Pass
`freshness` as `current`, `unverified` or `stale`. Pass `integrity: "compromised"` when a hinted
question was not replaced; the helper then suppresses the score and level. Include only the
neutral replacement question in place of a discarded hinted record, keeping the planned count
unchanged; never score both. Pass `integrity: "neutral"` only for an uncompromised final set.
Do not print the input or save the private
key merely to run the helper. Its output contains aggregates only; render those in the report.
The helper calculates results; the agent must still verify sources, answer-key validity and scope.

For a completed quiz (every planned question answered or explicitly skipped), show:
- **90–100%: Strong** understanding demonstrated across the sampled topics.
- **70–89%: Developing**; name the missed topics.
- **Below 70%: Needs review**; name the concepts to revisit.

Keep sphinx-ci's **70% passing score** wording: `Quiz passed!` at 70% or above, otherwise
`Not yet...`. This is a self-check only; it unlocks and blocks nothing. Skipped topics remain
untested even if the overall score is high. A topic with any wrong answer needs review; one with
only skips/unanswered questions is not assessed. A mix of correct and skipped/unanswered
questions is partly assessed. Do not infer a topic score from unasked questions.

If stopped early, use **Incomplete**, include provisional correct/total, and omit a pass or final
understanding level. With no submitted answers (including an all-skipped quiz), show **Not assessed**. With insufficient source context or
an unresolved material source change, show **Not assessed** or **Stale**, not a scored final result.

## Source and screenshot context

Before the report, recheck the source as described in
[target context](../../walkthrough/references/target-context.md). If unavailable, mark freshness
unverified and qualify that the score covers the earlier snapshot only. A material change makes
the final result stale; refresh affected questions before issuing a report for the new version.

Include the actual date/time and timezone from the host (never invent a timestamp), attempt number,
and participant name only if supplied or established in the chat; otherwise say `Chat participant`.
Track the attempt during the session; if history is unavailable, say `Attempt not known` rather
than guessing a number. Do not offer another retry if the remaining attempt allowance is unknown.
Do not look up personal identity or imply identity verification. Record walkthrough use as
`Provided in this chat`, `None in this chat`, or `Not known`; do not claim this detects other help.

## Render the dashboard

Run `python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/quiz_report.py" --format dashboard` with the same private
scoring input on stdin. Add a `report` object for observed session context:

- `target`: branch, pull request IID or diff reference and a short title.
- `source`: full PR source SHA and inspected revision.
- `session`: actual date/time and timezone; `participant` defaults to `Chat participant`.
- `attempt`: known integer 1–3, or `null` when unknown. Remaining attempts are derived, not guessed.
- `walkthrough`: `Provided in this chat`, `None in this chat`, or `Not known`.
- `coverage`: a short scope statement including important exclusions.
- `replaced`: number of discarded/replaced questions, only when known.
- `revisit`: up to eight objects with `detail` (one concise correction) and `source` (verified
  code location).. Group related misses where useful, preserving the
  frozen topic results. Do not invent code snippets or explanations to fill the panel.
- `focus`: optional, one short pattern supported by the misses; omit when no pattern is evidenced.

The helper derives the score, level, status, answer counts and grouped topic outcomes from the
questions. Metadata cannot override those results. It wraps long paths and identifiers without
truncating them and strips terminal control sequences. Default width is 76 columns;
`--width 64` is available for a narrow client (supported range 64–120). It uses plain Unicode,
not ANSI colour escapes. The original JSON output remains available with no format flag.

Show the helper's dashboard verbatim in one fenced `text` block so its columns stay aligned.
Do not replace it with a long label/value list, a Markdown table or an oversized ASCII logo.
Put real target/source links immediately below the block; links inside a code fence are not
clickable. Keep the full source identity inside the panel as well. Use the smallest set of
links needed for the target and revisit pointers. Never print the private input or answer key.

Completed results show a score bar, pass wording and level. Incomplete results show a
provisional score with no pass or final level. Stale, compromised and not-assessed results
show no score bar, pass wording or demonstrated-topic claims. An unverified source carries
an earlier-snapshot warning inside the panel. Do not hide these states to make the card look better.
For stale results, revisit pointers describe the earlier snapshot only.

Keep corrections brief, coverage explicit and the initial panel roughly one screen when the
source permits. Never drop topics, counts, provenance or integrity qualifiers to force a fixed
height. If references are long, use a wider supported panel or allow extra rows; do not shorten
paths or silently crop content. Do not add a second essay repeating the report. Do not save,
export, upload or post anything automatically; this renderer writes only to stdout.
