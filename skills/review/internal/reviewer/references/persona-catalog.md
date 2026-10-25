# Reviewer Persona and Model Catalog

## Selection policy

Each phase selects only personas with clearly distinct, high-impact failure classes. There is no
minimum or quota. The hard maximum is four personas per phase. The shared workflow policy selects
one requirements/testability specification reviewer, one architecture/simplicity plan reviewer and
one requirements/code-quality candidate reviewer for qualifying low-risk work, and focused
applicable existing personas for higher-risk or uncertain work.
Evidence gathering, option comparison, human decisions, and domain-specific concerns remain
controller responsibilities and evidence inputs rather than generic personas.

At dispatch, inspect the current host's available model metadata: provider family, supported
capability/cost class, and reasoning efforts when exposed. Select only a supported Claude/GPT route
in the persona's capability class. Request a supported non-maximum reasoning effort explicitly
when the host exposes that control; otherwise leave it unset and verify the documented/default route
is not maximum. An absent effort control is not an unavailable safe route. Never inherit an unknown
default or automatically choose the host's most expensive/frontier model. Never request `xhigh`,
`max`, or `ultra` for a reviewer.

If the preferred class is absent, choose the closest supported efficient class within the task's
constraints and record why. Do not hard-veto a review merely because a historical alias is absent.
When cost/capability metadata is unavailable, use the documented current-host lightweight/balanced
description or configured efficient route, and record that the cost class is unknown; never invent
pricing, cost, or a capability label. Only an explicitly unsafe or unidentifiable route is
`UNABLE_TO_REVIEW`. Requested route and actual runtime model/usage remain separate best-effort audit
data and never participate in a contract, input, cohort, or gate hash.

| Phase | Persona ID | Persona | Capability class | Selection rule |
|---|---|---|---|---|
| Specification | `requirements-testability` | Requirements & Testability Reviewer | lightweight | supported Claude/GPT, non-maximum if configurable |
| Specification | `integration-operability` | Integration & Operability Reviewer | balanced | supported Claude/GPT, non-maximum if configurable |
| Plan | `architecture-simplicity` | Architecture & Simplicity Reviewer | balanced | supported Claude/GPT, non-maximum if configurable |
| Plan | `failure-security-rollback` | Failure, Security & Rollback Reviewer | balanced | supported Claude/GPT, non-maximum if configurable |
| Candidate | `requirements-code-quality` | Requirements & Code Quality Reviewer | balanced | supported Claude/GPT, non-maximum if configurable |
| Candidate | `security-reliability` | Security & Reliability Reviewer | balanced | supported Claude/GPT, non-maximum if configurable |

Phase references define freshness, evidence, exact duties, ordering, and output schemas.
