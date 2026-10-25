#!/usr/bin/env python3
"""Fail if shipped skill or procedure prose carries dangerous instructions.

Skill files and internal/ procedures are executable instructions for agents:
patterns like `curl ... | sh`, `rm -rf /`, `chmod 777`, `git commit --no-verify`
or prompt-injection phrasing can pass every other gate (links, byte-clean
regeneration, secret scan) and still ship. This scanner fails on any hit so the
hit is worth stopping for.

    python3 scripts/scan_unsafe_instructions.py
    python3 scripts/scan_unsafe_instructions.py --staged

Exits 1 on any finding. Only the file, line and pattern kind are printed, never
surrounding content, so the scanner cannot itself amplify the payload.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# High-signal dangerous-instruction patterns. A hit should be rare enough that
# it is always worth a human look; widen deliberately, never casually.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("pipe remote script to shell", re.compile(r"\bcurl\b[^|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b")),
    ("recursive force delete of a root path", re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+(?:--no-preserve-root\s+)?[/~]")),
    ("world-writable chmod", re.compile(r"\bchmod\s+(?:-R\s+)?777\b")),
    ("commit hook bypass", re.compile(r"\b--no-verify\b")),
    ("prompt-injection phrasing", re.compile(r"(?i)\bignore\s+(?:all\s+)?previous\s+instructions\b")),
    ("ssh private material read", re.compile(r"(?i)\b(?:cat|read|copy|cp)\b[^;\n]*\.ssh/(?:id_[a-z0-9]+|identity)\b")),
]


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()


def _targets(root: Path) -> list[Path]:
    """Maintained instruction surfaces: skills, procedures and adapter copies.

    The generated skills/<skill>/internal/ mirrors are excluded: they duplicate
    internal/ byte-for-byte and would only double-report the same finding.
    """
    skip = {".git", "node_modules", "__pycache__", "plans"}
    files = []
    for top in ("skills", "internal", "commands", ".cursor", ".windsurf", ".continue", ".github"):
        base = root / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in (".md", ".prompt", ".mdc", ".yml", ".yaml"):
                continue
            parts = path.relative_to(root).parts
            if set(parts) & skip:
                continue
            if len(parts) >= 3 and parts[0] == "skills" and parts[2] == "internal":
                continue
            files.append(path)
    return sorted(files)


def scan(root: Path) -> int:
    findings: list[str] = []
    scanned = 0
    for path in _targets(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"  {path.relative_to(root)}:{line}  {label}")
    if findings:
        print(f"Unsafe-instruction scan: {len(findings)} finding(s) in {scanned} files\n")
        for finding in findings:
            print(finding)
        return 1
    print(f"Unsafe-instruction scan: clean ({scanned} files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return scan(_repo_root())


if __name__ == "__main__":
    raise SystemExit(main())
