# Edge-Case and Impact-Surface Scouting

Run read-only discovery against the candidate before formal review. The diff defines what changed;
the call graph and contracts define what can break.

## Trace

- every caller, importer, handler, worker, job, and generated consumer of changed interfaces;
- early returns, error mapping, retry and fallback paths;
- null, empty, zero, negative, maximum, malformed, duplicate, and stale inputs;
- concurrent execution, optimistic locking, transaction boundaries, and lost updates;
- timeout, partial success, retry, duplicate callback, and out-of-order event behavior;
- cache invalidation, event publication, audit, metrics, and other side effects;
- schema, migration, public API, protobuf, event, and configuration compatibility;
- generated-file sources and regeneration commands;
- read-only contracts in Dakota or DBMY context repositories.

Context repositories may expand the review surface but never the writable scope. If an acceptance
criterion requires a second repository change, return a blocking scope finding.

## Output

```text
Reviewed candidate SHA:
Changed files:
Impacted files outside diff:
Traced flows:
Boundary and failure cases:
Unverified paths:
```

Every impacted file or flow must be handed to the appropriate reviewer. Absence from the diff is
not a reason to exclude a consumer from review.
