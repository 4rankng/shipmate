#!/usr/bin/env python3
"""Fail if a file carries something that looks like a live credential.

Run before every commit. This is deliberately small and high-signal: it only
matches credential formats that are unambiguous, so a hit is worth stopping for
rather than something to habitually override.

    python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/scan_secrets.py" [path ...]
    python3 "${SHIPMATE_PLUGIN_ROOT}/scripts/scan_secrets.py" --staged

Exits 1 on any finding. Values are never printed — only the file, line and the
kind of credential — so the scanner cannot itself leak the secret into a log.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Names that denote a credential, and the shape of a value worth flagging.
CRED_NAME = (
    r"api[-_]?key|apikey|client[-_]?secret|secret|password|passwd|token|"
    r"auth[-_]?token|access[-_]?token|refresh[-_]?token|bearer|private[-_]?token|"
    r"app(?:lication)?[-_]?key|tm[-_]?token|jwt[-_]?token|"
    r"id[-_]?token|proof[-_]?token|authorization"
)
# Not a template ({{var}}, $VAR, <placeholder>, %s), not empty, and long enough
# to be a real credential rather than a flag or an enum.
# Optionally preceded by an auth scheme ("Basic ", "Bearer "), and allowing
# base64 padding, so `Authorization: Basic <b64>` is not missed.
LITERAL = (
    r"(?!\{\{|\$|<|%)(?:(?:Basic|Bearer|Token|Digest)\s+)?"
    r"[A-Za-z0-9_\-\.~+/]{12,}={0,2}"
)

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Project access token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Atlassian Cloud API token", re.compile(r"\bATATT[A-Za-z0-9_\-=]{20,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    # A credential-named key assigned a *quoted literal*. Requiring quotes is
    # what keeps `api_key = os.environ.get(...)` and `f"{email}:{api_key}"` out
    # of the results -- those assign an expression, not a secret.
    (
        "credential-named literal",
        re.compile(
            r"(?i)\b[A-Za-z0-9_\-]{0,12}?[-_]?(" + CRED_NAME + r")\b\s*[\"']?\s*[:=]\s*"
            r"[\"'](" + LITERAL + r")[\"']"
        ),
    ),
    # Postman/JSON header form, where the name and the value are separate
    # fields:  {"key": "api-key", "value": "QAFt..."}
    (
        "credential-named literal",
        re.compile(
            r"(?i)[\"']key[\"']\s*:\s*[\"']\s*[A-Za-z0-9_\-]{0,12}?[-_]?"
            r"(" + CRED_NAME + r")\s*[\"']"
            r"[^{}]{0,120}?[\"']value[\"']\s*:\s*[\"'](" + LITERAL + r")[\"']"
        ),
    ),
]

# Values that look like credentials but are structurally public or obviously fake.
ALLOWED = re.compile(
    r"(?i)^(?:gts-internal|example|placeholder|changeme|redacted|your[-_]|test[-_]?value|"
    r"xxx+|aaa+|fake|dummy|sample|none|undefined)"
)

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "vendor"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".pyc", ".so", ".bin"}


def _candidates(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(f for f in p.rglob("*") if f.is_file())
    return [
        f
        for f in out
        if not (SKIP_DIRS & set(f.parts)) and f.suffix.lower() not in SKIP_SUFFIXES
    ]


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()


def _staged() -> tuple[list[str], int]:
    """Return (existing staged paths, count reported by git).

    git prints paths relative to the repo root, so they must be resolved against
    it -- not the current directory -- or every path misses and the scan silently
    passes. Callers compare the two values to detect that case.
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return [], -1
    root = _repo_root()
    reported = [line for line in result.stdout.splitlines() if line]
    return [str(root / line) for line in reported if (root / line).is_file()], len(reported)


def scan(paths: list[str]) -> int:
    findings: list[str] = []
    scanned = 0

    for path in _candidates(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(match.lastindex or 0)
                if match.lastindex and ALLOWED.match(value):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"  {path}:{line}  {label}")

    if findings:
        print(f"Secret scan: {len(findings)} finding(s) in {scanned} files\n")
        for f in sorted(set(findings)):
            print(f)
        print(
            "\nBlocked. Replace each value with a variable reference or an "
            "environment lookup, then rescan. If a credential was ever real, "
            "rotate it — removing it from the working tree is not enough."
        )
        return 1

    print(f"Secret scan: clean ({scanned} files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories")
    parser.add_argument("--staged", action="store_true", help="scan git-staged files only")
    args = parser.parse_args()

    if args.staged:
        paths, reported = _staged()
        if reported < 0:
            print("Secret scan: cannot read the git index -- refusing to pass.")
            return 1
        if reported == 0:
            print("Secret scan: nothing staged")
            return 0
        if not paths:
            print(
                f"Secret scan: git reported {reported} staged file(s) but none "
                "could be read -- refusing to pass."
            )
            return 1
        return scan(paths)
    return scan(args.paths or ["."])


if __name__ == "__main__":
    sys.exit(main())
