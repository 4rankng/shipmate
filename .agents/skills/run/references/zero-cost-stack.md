# Zero-cost operating stack (solo delivery)

Advisory reference for delivering and operating a product at $0/month. Quotas change
often: verify the current free tier at the provider before adopting. Nothing here is
installed or configured automatically; propose what fits the user's stack and let them
choose. Never sign the user up for a service or spend their quota without approval.

## Releases

- Tag every delivered change (`git tag`, then push the tag); generate the changelog from
  commit messages (Conventional Commits style makes this mechanical). GitHub Releases can
  be created from a tag without any workflow runner.
- Keep the lint/test gates in the run itself (Stage 8); no hosted CI runner is required.

## Hosting free tiers

- Static sites: GitHub Pages, Cloudflare Pages.
- Application hosting: free or trial allowances on Render, Fly.io, Vercel (hobby),
  Koyeb; sleep/spin-down on idle is normal on free tiers.
- Databases: Supabase or Neon free projects; Turso for embedded-style edge SQLite.

## Monitoring at $0

- Uptime: UptimeRobot or healthchecks.io heartbeat checks against a `/health` endpoint.
- Errors: Sentry free tier, or self-hosted GlitchTip.
- Correlate alerts to changes: tag every deploy with its release so the alert names the
  version that likely caused it.

## Secret hygiene at $0

- Keep secrets in the platform's secret store (repository/environment secrets), never in
  the repo; the run's `scan_secrets.py` gate catches local leaks before push.
- Rotate immediately on any suspected exposure; free tiers do not exempt rotation.

## When to propose this reference

Offer it when the user asks how to deliver, deploy, release or monitor on no budget —
for example during Stage 10/11 handback. It is guidance, not a run stage: adopting any
item is separately authorized work.
