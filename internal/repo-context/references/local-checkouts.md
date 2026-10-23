# Local Payment Checkouts

## Purpose

Reuse repositories already cloned on the engineer's machine. Never clone Dakota Payment or DBMY
Payment as part of L3.

## Machine-local registry

Store validated checkout roots in `~/.gx-payment-repositories.json`:

```json
{
  "schema_version": 1,
  "repositories": {
    "dakota_payment": {
      "path": "/absolute/path/to/dakota/payment",
      "remote": "gitlab.com/gx-regional/dakota/payment"
    },
    "dbmy_payment": {
      "path": "/absolute/path/to/dbmy/payment",
      "remote": "gitlab.com/gx-regional/dbmy/payment"
    }
  }
}
```

This file contains checkout paths and canonical remote identities only—never credentials—and must
not be committed or copied into a requirement, Jira, an MR, a plan, or a review record. Human-facing artifacts use
canonical repository identities.
Writing this registry is the only machine-setup write outside the declared target repository.

## First-use bootstrap

1. Read the registry when it exists.
2. Otherwise inspect the current Git root and nearby existing checkouts.
3. If either root remains unresolved, ask once for the absolute Dakota Payment and DBMY Payment
   paths. This is environment setup before work-item execution, not a specification decision.
4. Resolve each path with `git -C <path> rev-parse --show-toplevel`.
5. Read `git -C <root> remote get-url origin`, normalize SSH and HTTPS forms, and require the
   canonical remotes above. Reject a similarly named directory or mismatched fork.
6. Write both validated roots to the registry. Reuse them on later runs without asking again.

If a stored path disappears or its remote no longer matches, repeat validation for that entry. Do
not search the entire home directory, reclone a repository, or silently substitute a fork.

## Reproducible read-only context

Record the canonical remote and inspected commit SHA for every context repository. Evidence must
come from a clean snapshot at that SHA:

- when the existing checkout is clean and `HEAD` equals the inspected SHA, it may be used directly;
- otherwise use the existing clone to create a detached temporary worktree at the inspected SHA;
- never let uncommitted context changes influence plan evidence;
- recheck snapshot `HEAD` and cleanliness after all plan reviewers return;
- remove only temporary worktrees created by this run after their evidence is no longer needed.

The writable target worktree may contain the persisted plan and no implementation changes during
plan review. Review source evidence from its clean base-SHA snapshot, and pass the plan content
separately. Reviewer contracts prohibit mutation, and the controller verifies both snapshot
identities before and after each review wave.

Pass every reviewer the controller-validated absolute snapshot root alongside its canonical
repository identity and inspected SHA. Recheck that the root still resolves to that clean SHA after
review. Snapshot paths are machine-local routing data: exclude them from the plan-review digest,
persisted plan, review summary, requirement source, Jira, and MR. A reviewer must never discover or substitute a nearby
workspace path.

## Mutation boundary

Declare exactly one target repository writable before planning. Every other checkout and snapshot
is read-only context. The path registry and detached temporary review snapshots are machine-local
operational artifacts: creating/removing them is allowed, but never modify a context repository's
tracked files, branches, remotes, or configuration. Before every project-file create, edit, move, or
delete, resolve the path and verify it is inside the declared target root. If the accepted change
requires a second repository write, stop before code and split or coordinate the work item through
its selected source mode; never widen the boundary silently.
