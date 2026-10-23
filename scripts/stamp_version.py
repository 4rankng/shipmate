#!/usr/bin/env python3
"""Stamp the root VERSION into every plugin manifest without reformatting JSON.

One release train: bump VERSION, run this script, commit, tag. --check reports stale
manifests and exits 1 without writing, for CI and doctor-style verification.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MANIFESTS = [
    "plugin.json",
    "package.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".omp-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".openclaw-plugin/openclaw.plugin.json",
    "openclaw.plugin.json",
    "configs/antigravity-cli/plugin.json",
]
VERSION_FIELD = re.compile(r'^(\s*"version":\s*")[^"]+(",?\s*)$', re.MULTILINE)
SEMVER = re.compile(r"\d+\.\d+\.\d+")


def stamp(root: Path, version: str, check: bool = False) -> int:
    stale = []
    for relative in MANIFESTS:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        updated, fields = VERSION_FIELD.subn(lambda match: match.group(1) + version + match.group(2),
                                             text)
        if fields != 1:
            raise SystemExit(f"{relative}: expected exactly one version field, found {fields}")
        if updated != text:
            stale.append(relative)
            if not check:
                path.write_text(updated, encoding="utf-8")
    if check and stale:
        print("stale manifests: " + ", ".join(stale))
        return 1
    print(f"version {version}: {len(MANIFESTS)} manifests {'ok' if not stale else 'stamped'}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report stale manifests without writing")
    parser.add_argument("--root", default=".", help="plugin root (default: current directory)")
    args = parser.parse_args(argv)
    version = (Path(args.root) / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(version):
        raise SystemExit(f"VERSION must be semver, got {version!r}")
    return stamp(Path(args.root), version, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
