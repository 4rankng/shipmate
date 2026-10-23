#!/usr/bin/env python3
"""Preflight check for the shipmate plugin.

Reports every missing CLI, environment variable and path in one pass, so a run
fails up front with a clear message instead of halfway through a task.

Usage:
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/doctor.py"
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/doctor.py" --group jira,gitlab
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/doctor.py" --group jira --live --region sg

A variable being set is not the same as it being valid: a token rotated after
this process started is still present and still 401s. `--live` makes one real
Jira call for the selected region to tell those two states apart. No secret is printed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import lookup  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# group -> (required CLIs, credential sets). Each credential set is
# (label, alternatives); it passes when ANY alternative is fully populated, so
# region-prefixed and legacy unprefixed variables are both accepted.
CHECKS: dict[str, dict] = {
    "core": {
        "clis": ["git", "python3"],
        "creds": [],
    },
    "gitlab": {
        "clis": ["glab"],
        "creds": [("GitLab token", (["GITLAB_PRIVATE_TOKEN"],))],
    },
    "jira": {
        "clis": [],
        "creds": [
            (
                "Jira SG",
                (
                    ["SG_JIRA_DOMAIN", "SG_JIRA_USERNAME", "SG_JIRA_API_KEY"],
                    ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
                ),
            ),
            (
                "Jira MY",
                (
                    ["MY_JIRA_DOMAIN", "MY_JIRA_USERNAME", "MY_JIRA_API_KEY"],
                    ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
                ),
            ),
        ],
    },
    "go": {
        "clis": ["go"],
        "creds": [],
    },
}


def _cred_set_ok(alternatives: tuple[list[str], ...]) -> tuple[bool, list[str]]:
    """A credential set passes if any alternative has every variable set."""
    for group in alternatives:
        if all(lookup(name) for name in group):
            return True, []
    return False, [" or ".join(" + ".join(g) for g in alternatives)]


def _glab_auth_ok() -> bool:
    """Return whether glab has usable auth without printing its token or config."""
    try:
        result = subprocess.run(
            ["glab", "config", "get", "token", "--host", "gitlab.com"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _live_jira_check(regions: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Call /myself for the requested regions. Presence checks pass on a rotated-away token;
    only a real call proves the credential still works."""
    lines: list[str] = []
    problems: list[str] = []
    sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
    try:
        from jira_client import JiraAuthError, jira_get  # noqa: PLC0415
    except ImportError as exc:
        return [], [f"jira live check unavailable: {exc}"]

    import urllib.error  # noqa: PLC0415

    for region in regions:
        try:
            me = jira_get("/rest/api/3/myself", region=region)
            lines.append(f"ok    jira: {region} credential valid ({me.get('displayName')})")
        except JiraAuthError:
            problems.append(
                f"jira: {region} credential rejected (401). Rotate or re-export "
                f"{region.upper()}_JIRA_API_KEY; confirm {region.upper()}_JIRA_USERNAME "
                "is the account that issued it."
            )
        except urllib.error.HTTPError as exc:
            problems.append(f"jira: {region} live check returned HTTP {exc.code}")
        except Exception as exc:  # network, DNS, malformed domain
            problems.append(f"jira: {region} live check failed: {type(exc).__name__}")
    return lines, problems


def run(groups: list[str], live: bool = False, region: str = "sg") -> int:
    problems: list[str] = []
    lines: list[str] = []

    if not (PLUGIN_ROOT / "scripts").is_dir():
        problems.append(f"plugin scripts directory not found at {PLUGIN_ROOT / 'scripts'}")

    for group in groups:
        spec = CHECKS.get(group)
        if spec is None:
            problems.append(f"unknown check group: {group}")
            continue
        for cli in spec["clis"]:
            if shutil.which(cli):
                lines.append(f"ok    {group}: {cli}")
            else:
                problems.append(f"{group}: `{cli}` not on PATH")
        for relative_path in spec.get("paths", []):
            path = PLUGIN_ROOT / relative_path
            if path.exists():
                lines.append(f"ok    {group}: {relative_path}")
            else:
                problems.append(f"{group}: missing bundled path {relative_path}")
        # Regional credential sets are alternatives to each other: a group is
        # satisfied when at least one region resolves. Missing other regions are
        # reported as warnings so an SG-only engineer is not blocked by MY vars.
        if group == "gitlab" and _glab_auth_ok():
            lines.append("ok    gitlab: authenticated glab session")
            results = []
        else:
            results = [(label, *_cred_set_ok(alts)) for label, alts in spec["creds"]]
        any_ok = any(ok for _, ok, _ in results)
        for label, ok, missing in results:
            if ok:
                lines.append(f"ok    {group}: {label} credentials present")
            elif any_ok:
                lines.append(f"warn  {group}: {label} unavailable, set {missing[0]}")
            else:
                problems.append(f"{group}: {label} needs {missing[0]}")

    if live and "jira" in groups:
        live_regions = ("sg", "my") if region == "all" else (region,)
        live_lines, live_problems = _live_jira_check(live_regions)
        lines.extend(live_lines)
        problems.extend(live_problems)

    print("\n".join(lines))
    if problems:
        print("\nBlocked. Fix these before continuing:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nAll checks passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group",
        default=",".join(CHECKS),
        help=f"comma-separated groups to check. Available: {','.join(CHECKS)}",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="also call Jira /myself to prove the selected regional token works",
    )
    parser.add_argument(
        "--region",
        choices=("sg", "my", "all"),
        default="sg",
        help="region for live Jira authentication checks (default: sg)",
    )
    args = parser.parse_args(argv)
    return run(
        [g.strip() for g in args.group.split(",") if g.strip()],
        live=args.live,
        region=args.region,
    )


if __name__ == "__main__":
    raise SystemExit(main())
