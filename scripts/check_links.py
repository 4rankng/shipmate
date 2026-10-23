#!/usr/bin/env python3
"""Validate every relative markdown link in the repository resolves to a file.

Shipmate skills are a deep reference graph: an agent that follows a broken link
silently skips a required contract. This checker guards that graph. Anchors,
external http(s)/mailto targets and plain fragments are ignored.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^()\s]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:")


def markdown_files(root: Path) -> list[Path]:
    # plans/ holds machine-local session reports, not part of the plugin graph.
    skip_dirs = {".git", "node_modules", "__pycache__", "plans"}
    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not (set(path.parts) & skip_dirs)
    ]


def broken_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    broken = []
    for match in LINK.finditer(text):
        target = match.group(1)
        if target.startswith(SKIP_PREFIXES):
            continue
        candidate = target.split("#", 1)[0]
        if not candidate:
            continue
        if not (path.parent / candidate).is_file():
            broken.append(f"{target}")
    return broken


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures = []
    checked = 0
    for path in markdown_files(root):
        links = broken_links(path)
        checked += sum(1 for _ in LINK.finditer(path.read_text(encoding="utf-8")))
        for target in links:
            failures.append(f"{path.relative_to(root)}: broken link -> {target}")
    for failure in failures:
        print(failure)
    print(f"checked {checked} links in markdown")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
