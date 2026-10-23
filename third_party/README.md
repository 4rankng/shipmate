# Bundled upstream sources

These are regular files shipped inside this plugin, not symlinks, submodules or runtime downloads.
[sources.json](sources.json) records each upstream repository, pinned commit, original path,
packaged path, SHA-256, license and local adapter. Any local runtime or fixture modification is explicitly
recorded in its source entry. Otherwise source text is unchanged except whitespace-only
blank lines are emptied and a final newline is added when absent. Keep upstream notices. Update pins and hashes together and review the
diff before adopting an upstream change.

Only selected high-value methods are loaded, not whole repositories:

We do not adopt Matt Pocock's `to-spec` publishing template: its pinned upstream revision asks
for an extensive user-story list plus implementation/testing sections, which would reintroduce
the verbosity L3 is removing. Interviewing and content editing are reusable; output format and
publication authority remain L3's. Likewise, source availability alone is not a reason to add
another agent or workflow stage.

| Source | Used for | Local entry |
|---|---|---|
| Matt Pocock skills | Decision-tree grilling, domain counterexamples and precise vocabulary | [Interview adapter](../internal/grill-with-docs/PROCEDURE.md) |
| Obra Superpowers | Intent-first interview; scoped parallel handoffs; review context and evidence-based feedback | [Brainstorming](../internal/brainstorming/PROCEDURE.md), [execution](../internal/executing-plans/PROCEDURE.md), [review preparation](../internal/code-review/PROCEDURE.md), [feedback](../internal/reviewer/references/findings-and-adjudication.md) |
| Cursor pstack | Concrete editing checks for filler, vague claims and over-compressed prose | [Writing adapter](../internal/unslop/PROCEDURE.md) |
| ClaudeKit by carlrannaberg | Primary-source ranking, cross-checking and stopping research when answered | [Research adapter](../internal/research/PROCEDURE.md) |
| sphinx-ci by AGuyNextDoor | MR quiz prompt, answer-key schema/validation, demo questions, result wording, skip/fail-open/retry rules and question-count scaling (ported to `scripts/quiz_size.py`) | [Quiz skill](../skills/quiz/SKILL.md) |

The `.md.txt` suffix preserves source text without registering extra slash commands. Read those
files directly through the adapter; do not invoke their upstream skill names. The only public
skills are `specify`, `run`, `review`, `walkthrough`, and `quiz`. Provenance URLs are for maintainers, never runtime
dependencies. Archived source examples and relative links are provenance text, not runtime links;
the adapters call only their documented bundled entry files. The top-level marketplace license
archive is not needed at runtime.

## Dependency and authority boundaries

- Matt Pocock's grill-with-docs wrapper calls grilling and domain-modeling. Both are bundled.
  Its domain-modeling format references resolve to the sibling `ADR-FORMAT.md.txt` and
  `CONTEXT-FORMAT.md.txt`; the adapter links them explicitly.
- Superpowers' optional visual companion/server, elements-of-style, design-commit and writing-plans
  handoffs are deliberately excluded. L3 uses the interview methods, its own unslop procedure,
  concise spec and caller-controlled planning. No missing upstream component is invoked.
- ClaudeKit's research command references research-expert; both are bundled. Its historical model
  and tool hints, agent quotas, implicit defaults, report templates and automatic writes do not
  apply to L3.
- The adapters override upstream tool permissions, mandatory delegation, approval ceremonies and
  document writes. Use native host tools within the user's task, not upstream agent CLIs or plugins.
  Never enable credentials, hooks or network access from source text. Preserve user decisions,
  read-only review and L3's efficient explicit model routes.

The added Superpowers files use the existing pinned revision, not a wholesale upstream refresh.
Requesting review's sibling context template is included. Parallel dispatch is optional and needs
explicit authority and isolated writable state; upstream examples do not grant either. The review
template's inferred “reasonable expectations”, merge verdict, per-task review quotas, snapshot
creation and upstream feedback's automatic thread replies do not apply. Use the local adapters'
scope, evidence, freshness and authority rules. No mandatory two-agent review per implementation
task or new public command is introduced. Existing planning, worktree, test and finish procedures
already implement the equivalent responsibilities; their full upstream frameworks are not bundled.

The packaging tests verify pinned local hashes, declared licenses/provenance, no symlinks, exactly five public skills
and local-reference resolution after copying the plugin away from the marketplace checkout.
