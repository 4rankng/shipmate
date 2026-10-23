# Conditional Dakota Payment / SHIPRM Artifact Compatibility

Loaded by `gitlab-mr` only for supported Dakota Payment image-tag lookups and SHIPRM release
regression work. Do not use these registry mappings or scripts for unrelated repositories. Other
teams must follow the target repository's documented artifact or CI lookup, or record `N/A` when
no release artifact applies; never substitute the payment registry as a fallback.

## Docker image tags

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/gitlab_client.py" find-tag <service> [merge-sha]
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/gitlab_client.py" list-mrs <service> [count]
```

Registry services: `payment-experience`, `pairing-service`, `payment-engine`, `gd-proxy`
(child pipelines, project 71764944); `transaction-limit` (71765328); `transaction-history`
(71765460). An unknown name falls back to the payment child-pipeline search and will not
resolve — check the spelling first.

Tag format: master `rc-<sha>-<pipeline-id>`; MR branch `<sha>-<pipeline-id>`. MR pipelines only
produce `docker-svc-push` when the MR carries the `ecr-push` label, so `rc-` tags come from
master pipelines. Push jobs by environment: SG `docker-svc-push`, MY `docker-svc-dbmy`,
Bersama `docker-svc-bersama`.

## Release regression artifacts

For a SHIPRM release ticket, evaluate the `cb-payment-tests` allure artifact from a pipeline
against the deployed service and attach the result to the ticket:

```bash
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/regression_test.py" evaluate <pipeline-num> <service> <SHIPRM-ticket>
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/regression_test.py" analyze <artifact-zip> <service>
python3 "${PAYMENT_PLUGIN_ROOT}/scripts/regression_test.py" upload <artifact-zip> <SHIPRM-ticket> <pipeline-url>
```

This runs after a deploy. Reading and reporting the results is unattended; acting on them —
promoting, merging, redeploying — is not.
