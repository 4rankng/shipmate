# Secure engineering in the existing workflow

Use this guide when a change touches the controls below. It applies to any team's repository,
not only one service type. Keep the existing risk-selected reviewers and approval boundaries.
Documentation-only work does not need a security questionnaire or new tests unless it changes
security instructions. Do not generate a ten-category report for every task.

## Establish what protects the affected path

During Specify or direct Run intake, trace the caller, untrusted input, sensitive data and side
effect through the existing code. Find the actual authorization middleware, query/command APIs,
secret provider, logging filters and network client relevant to that path. Record only applicable
controls with a code/config/test reference in working notes; one short note can cover a small change.
Distinguish verified controls from assumptions and missing evidence.

Reuse the repository's supported mechanisms. A corporate template is not evidence that a named
identity service, permission library, vault, logger or service mesh is installed. Authentication
does not prove resource authorization; an internal hostname does not prove mTLS or caller trust.
Inspect the deployment/config evidence when it matters. Do not introduce a replacement framework,
secret store or custom crypto merely because the reference names a different stack.

Grill only unresolved consequential choices: who may act on which resource, what data may leave
the boundary, and what happens if a control or dependency fails. Ask the human when those choices
change behaviour or authority; do not ask them to locate inspectable code. Put the agreed constraint
and a focused Given/When/Then failure case in the existing specification, not a new security dossier.

## Choose checks from the changed behaviour

Carry the applicable checks into the implementation plan, tests and candidate review. The last
column gives examples, not a quota. Use synthetic data and non-production tests. A read-only
reviewer inspects controller-supplied test evidence; this guide never authorizes executing a test,
probing a live endpoint or changing infrastructure.

| Change | Control to inspect or implement | Useful failure test |
|---|---|---|
| Resource IDs, tenant scope, authentication or sessions | Authorize the authenticated actor for the resource and action before disclosure or mutation. Reuse scoped queries/policy checks; do not duplicate a proven control. Validate tokens through the existing library, including issuer, audience, expiry and permitted algorithms as applicable. | Another user/tenant's ID, expired token or permission-service failure cannot disclose data or perform the action. |
| Queries, commands, templates or paths | Bind query values; allowlist identifiers/operators that cannot be bound. Prefer direct APIs or argv-based execution over a shell; argv still needs option/argument and path validation. Use context-appropriate output encoding, safe template APIs and permitted filesystem roots. | Malicious value stays data; command options, traversal or rendered markup cannot change the intended operation. |
| Secrets, sensitive data or cryptography | Use the configured secret/key provider and approved crypto libraries. Check access, rotation, authenticated encryption and TLS verification where relevant. Environment injection alone does not prove secure storage. Do not replace protocol-required algorithms or non-security checksums without checking purpose and compatibility. | Missing key or invalid certificate fails safely; logs, traces, errors and fixtures contain no credential or sensitive payload. |
| Outbound destinations supplied by a caller | Prefer the existing restricted client/egress policy. Validate scheme, host and resolved IPv4/IPv6 destinations against the intended destination policy. Disable redirects or revalidate every hop; address DNS rebinding at connection time. Prevent unintended private, loopback, link-local and metadata access. An explicitly required internal destination needs narrow authorization, not a blanket private-network exception. | An allowed public URL cannot redirect or resolve to a forbidden destination; credentials are not forwarded across origins. |
| Web/server configuration | Preserve safe error contracts, explicit origin/credential rules, CSRF protection where relevant, least privilege and non-debug production settings. CORS is not authorization; public non-credentialed resources need not acquire an arbitrary origin restriction. | Unauthorized origin or forged state-changing request fails; failures expose no stack trace, token or internal detail. |
| Dependencies, CI or downloaded artifacts | Reuse maintained repository-compatible packages and lockfiles. Check applicable advisories and provenance using available repository tooling. Verify artifacts against a trusted digest/signature source before execution; a checksum served beside an attacker-controlled binary is not proof of authenticity. | Tampered/untrusted artifact is rejected; dependency changes retain required security checks. Do not upgrade unrelated packages just to select the newest release. |
| Deserialization, uploads or imported data | Use a data-only parser, schema and size/depth limits. Disable external entities where applicable; avoid object deserialization or executable formats for untrusted input. Signing alone does not make an unsafe parser safe. | Malformed, oversized or executable payload is rejected without code execution, external entity fetches or partial writes. |
| Security events or logging | Use the existing structured audit/logging path for relevant authentication/authorization failures and sensitive state changes. Record safe identifiers and outcomes, redact secrets/PII, and prevent log injection. Avoid raw bodies, unbounded attacker-controlled log volume or duplicating central audit events. | A denied action produces usable safe evidence; malicious input cannot forge log entries or leak secrets. |
| Exceptions, retries or resource limits | Fail closed at an authorization boundary, bound time/retries/resources and preserve transaction/state invariants. After an uncertain external side effect, use existing recovery/idempotency rather than assuming nothing happened or blindly retrying. | Dependency error, timeout, duplicate input or partial write neither grants access nor repeats a side effect; resources are released. |

## Findings that change an engineering decision

In candidate review, trace the actual caller-to-effect path, including existing mitigations outside
the diff. Use the existing finding schema: location, reproducible exploit/failure path, impact,
smallest safe correction and verification. A missing library name, checklist heading or preferred
design is not a vulnerability. Separate a demonstrated defect from an unverified control.

Fix demonstrated in-scope risks under implementation authority; read-only Review returns findings
without changing code. Required failed security checks still prevent successful delivery under
workflow-policy. Unavailable optional scanners or unreachable reference sites are advisory; missing
material evidence follows the existing pending/clarification path. Do not turn every suggestion
into a veto, bypass required checks, or claim compliance because a scanner passed.

Explain residual risks briefly in review/handoff prose. A warning does not make insecure code
acceptable. Do not insert boilerplate `OWASP WARNING` comments throughout source; comment only
when a non-obvious constraint needs to remain beside the code. Never ship a known bypass merely
because the user requested an insecure shortcut. Offer the safe in-scope implementation or ask the
specific unresolved policy decision while continuing unaffected work.

## Reference directory

These are optional drill-down references, not runtime dependencies or copied company policy.
The controller may consult the relevant source and pass an excerpt to a read-only reviewer; the
reviewer does not gain network authority. Record the version when citing a numbered requirement.

| Reference | Use |
|---|---|
| [OWASP Top 10:2025](https://top10.owasp.org/2025/) | Risk awareness, not a complete verification standard. Use category names plus edition; never copy older A-numbers under a newer heading. In 2025, A03 covers supply-chain failures and A10 exceptional conditions. Keep SSRF checks even though the category layout changed. |
| [OWASP ASVS](https://github.com/OWASP/ASVS) | Select testable web/API requirements for the affected control; do not require full certification for a small change. |
| [OWASP MASVS](https://mas.owasp.org/MASVS/) | Use for mobile-specific storage, platform and network behaviour, not as a mandatory backend checklist. |
| [NIST SSDF](https://csrc.nist.gov/projects/ssdf) | Connect secure design, implementation, verification and vulnerability response to the existing lifecycle. |
| [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/) | Consult a focused implementation guide when the existing code or local guidance is insufficient, such as [SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html). |

The local guidance remains usable offline. It adapts the supplied reference's direction into
repository-grounded decisions; it does not install external rules, assume another company's tools
or claim an organization-wide security standard has been adopted.
