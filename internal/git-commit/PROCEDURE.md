---
name: git-commit
description: Use when committing work, staging changes, or creating a branch for a local work item
---

# Commits and Branches

Derive `SHIPMATE_PLUGIN_ROOT` from this procedure's installed path (the directory containing
`plugin.json`) before running bundled commands; do not assume a host-provided plugin-root variable.

## Authority

Unattended: create a feature branch, stage, commit, push to that feature branch.

Never without a human: commit to the repository's default branch or any protected branch, `push --force`, `rebase` or
`reset` a shared branch, amend a pushed commit, or push to a branch you did not create.

## Branch naming

Use the selected `work_item.id` followed by a short kebab summary, separated by `-` or `/`. For
example, `local-0123456789ab/fix-timeout`. Derive the work-item ID only from the stable run-owned
local ID recorded during intake; never invent one.
Prefer the immutable full base SHA pinned by L3. Outside L3, resolve the declared default branch
from validated repository metadata or `refs/remotes/origin/HEAD`, fetch that exact branch, and pin
its full SHA before branching. Never guess `master` or `main`:

```bash
default_ref="$(git symbolic-ref --short refs/remotes/origin/HEAD)"
default_branch="${default_ref#origin/}"
git fetch origin "$default_branch"
base_sha="$(git rev-parse "origin/$default_branch^{commit}")"
git switch -c "<WORK-ITEM-ID>-<summary>" "$base_sha"
```

**L3 pinned-base rule:** `shipmate` fetches and records an immutable full base SHA before
planning. When that SHA is supplied, do not resolve a moving default branch again. Create the
branch/worktree from the exact SHA and verify its merge base matches. If a newer base is required,
inspect the base delta and revalidate affected context/planning rather than advancing silently
or repeating unrelated phases. Base identity establishes reviewed code, not a design approval lock.

## Commit message

Inspect the target repository's commit/subject policy first. Use its required format exactly. A ticket-key subject format below applies only when that repository's policy requires one:

```
<type>: [<TICKET-KEY>] <imperative summary under 72 chars>

<optional body: why, not what — the diff already says what>
```

Allowed types are **`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, and
`chore`**. When the change is scoped to one service, name it after the ticket:
`feat: [ABC-3742] exports: risk-treatment init`.

Some repositories enforce this subject prefix for ordinary and squash commits:

```regex
^(feat|fix|docs|style|refactor|perf|test|chore): \[[A-Z]+-[0-9]+\] .+$
```

Git-generated `Revert ...`, `Merge branch ...`, and `Notes added by 'git notes add'...` messages
are separate company-policy exceptions. Do not use those prefixes to bypass the normal format.

These are invalid:

```text
[feat]: [ABC-1234] improve workflow
feat(l3): [ABC-1234] improve workflow
[ABC-1234] improve workflow
feat: ABC-1234 improve workflow
```

Use the repository's conventional subject format and include the local
work-item ID where accepted, for example `fix: [local-0123456789ab] handle stale state`. If the target repository's commit/subject policy
requires a ticket key and has no ticketless form, preserve the verified local branch and report that
delivery constraint and ask for the documented key convention or alternative; do not invent
a ticket key or restart otherwise valid requirements/implementation. **Never append a trailer.** No `Co-authored-by`, no
`Signed-off-by`, no tool attribution.

Confirm against `git log --oneline -20` before the first commit on an unfamiliar repo.

## Squash commit message and MR title

The hosting platform commonly seeds the squash commit subject from the MR title. Therefore the MR title must use
the same target-repository format as a commit subject; do not rely on a `--fill` option to
choose a compliant title.

Before creating or updating the MR:

1. Choose the squash subject from the overall delivered change, not merely the last commit.
2. Keep the same work-item ID used by the branch and commits.
3. Validate it locally against the target repository's policy. For a ticket-key subject policy:

   ```bash
   squash_subject="feat: [ABC-1234] improve L3 workflow"
   printf '%s\n' "$squash_subject" \
     | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|chore): \[[A-Z]+-[0-9]+\] .+$'
   ```

4. Hand the validated subject to the bundled MR-delivery procedure as the
   explicit MR title. Never let `--fill` choose
   the title.

5. Read the MR back and verify its title still matches. The platform may display a draft as
   `Draft: <squash subject>`; strip only that UI prefix for validation and do not mark the MR ready.
   Before an authorized merge, the human or merge operator must verify the displayed squash commit
   message uses the same compliant subject.

For multiple commits, every manually authored commit subject and the final squash subject must
match. Squashing does not excuse invalid intermediate commit messages because the server may check
the pushed commits independently.

## Before every commit

1. `git status --short` — confirm you are staging only what you intended.
2. `git diff --staged` — read it; a commit you have not read is a commit you cannot defend.
3. Scan the staged set. This is not optional:

   ```bash
   python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/scan_secrets.py" --staged
   ```

   A non-zero exit blocks the commit. Fix it by replacing the value with a variable reference or
   an environment lookup — never by narrowing the scan. If the credential was ever real, say so
   in your report so it can be rotated; deleting it from the working tree does not un-leak it.
4. Confirm no customer record, production log or `.env` file is staged. The scanner catches
   credential *formats*, not customer data — that judgement is yours.
5. Confirm the change is verified. An unverified commit is reported as unverified.

Stage explicitly by path. Do not use `git add -A` or `git add .` in a repository you did not
start clean, and never commit files the task did not require you to change.

## Commit granularity

One commit per coherent behavior change. A test and the code that makes it pass belong in the
same commit. Unrelated cleanup belongs in its own commit, or in no commit at all.
