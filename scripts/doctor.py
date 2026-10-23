#!/usr/bin/env python3
"""Preflight check for the shipmate plugin.

    python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/doctor.py"
    python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/doctor.py" --group delivery

A variable being set is not the same as it being valid: a token rotated after
this process started is still present and still fails. `gh auth status` makes
one real call for the delivery group to tell those two states apart. No secret
is printed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# group -> (required CLIs, credential sets). Each credential set is
# (label, alternatives); it passes when ANY alternative is fully populated.
CHECKS: dict[str, dict] = {
    "core": {
        "clis": ["git", "python3"],
        "creds": [],
    },
    "delivery": {
        "clis": ["gh"],
        "creds": [
            ("GitHub token", (["GH_TOKEN"], ["GITHUB_TOKEN"])),
        ],
    },
}


def _cred_set_ok(alternatives: tuple[list[str], ...]) -> tuple[bool, list[str]]:
    """A credential set passes if any alternative has every variable set."""
    for group in alternatives:
        if all(os.environ.get(name) for name in group):
            return True, []
    return False, [" or ".join(" + ".join(g) for g in alternatives)]


def _gh_auth_ok() -> bool:
    """Return whether gh has usable auth without printing its token or config."""
    gh = shutil.which("gh")
    if not gh:
        return False
    result = subprocess.run(
        [gh, "auth", "status"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode == 0 and bool(result.stdout.strip() or result.stderr.strip())


def run(groups: list[str]) -> int:
    problems: list[str] = []
    for group in groups:
        spec = CHECKS.get(group)
        if spec is None:
            problems.append(f"unknown group: {group}")
            continue
        for cli in spec["clis"]:
            if shutil.which(cli):
                print(f"ok    {group}: {cli} available")
            else:
                problems.append(f"{group}: required CLI not found: {cli}")
        for label, alternatives in spec["creds"]:
            ok, missing = _cred_set_ok(alternatives)
            if ok:
                print(f"ok    {group}: {label} set")
            else:
                problems.append(f"{group}: {label} missing ({missing[0]})")
        if group == "delivery" and _gh_auth_ok():
            print("ok    delivery: authenticated gh session")
        elif group == "delivery":
            problems.append("delivery: gh auth status failed or produced no output; run `gh auth login`")
    for problem in problems:
        print(f"problem: {problem}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group",
        default=",".join(CHECKS),
        help=f"comma-separated groups to check. Available: {','.join(CHECKS)}",
    )
    args = parser.parse_args(argv)
    groups = [group.strip() for group in args.group.split(",") if group.strip()]
    return run(groups)


if __name__ == "__main__":
    raise SystemExit(main())
