# Trace the claimed behavior

Use these checks only for affected paths, inside the existing review. They do not add personas,
votes, approval steps or mandatory refactoring. Comments and examples are claims to verify,
not independent proof of the code's behavior.

## Error handling: a fallback is not automatically a defect

Consider a cache backed by an authoritative store. The agreed requirement allows a failed cache
read to fall through to the store. A store failure must be returned to the caller.

```go
value, err := cache.Get(id)
if err == nil {
    return value, nil
}
return store.Get(id)
```

The cache fallback above preserves the requirement. Do not demand a user-facing error for that
cache miss or outage merely because it is an error branch. Check the actual store call and its
returned error. By contrast, returning `Value{}, nil` when `store.Get` fails falsely reports
success and deserves a finding tied to that path.

Trace which error occurred, whether authoritative work completed, what the caller sees, and
whether a retry repeats a side effect. An unavailable optional metric or cache is different from
an unknown result of an authoritative write. Logging alone does not repair a wrong response, and
logging every layer is not a universal requirement.

## Comments and examples: verify the observable claim

If a comment says "accepts widths 64 through 120" but the guard rejects `width >= 120`, trace
the requirement and the boundary test. When the requirement includes 120, the guard is wrong;
when the requirement excludes it, the comment is wrong. Do not infer the intended contract from
the comment alone. Cite the required boundary, actual result and affected caller or example.

For a walkthrough, explain the inspected behavior and flag the misleading comment; do not
rewrite it. For an MR quiz, ask about the code at the selected revision and make that source
mode clear. For a requirements quiz, use settled requirements rather than importing a code behavior.
Drop a scored question if a material ambiguity cannot be resolved from the selected source.

## Tests: name the counterexample

Recommend a missing test only with a concrete input and observable failure it would catch.
For the width example, check 63, 64, 120 and 121 when the required range is inclusive. A single
ordinary value does not establish either boundary. A test that only asserts the presence of the
comment would not detect the faulty guard. Existing integration coverage can satisfy the case;
do not require a duplicate unit test or a percentage target for its own sake.

## Simplification: preserve the reason for the branch

Limit proposed simplification to changed code. Compare an existing utility through a real caller
before adding or removing an abstraction. Preserve a custom path when a protocol or requirement
needs it. A smaller diff, fewer lines or an aesthetic preference is not evidence of correctness.
