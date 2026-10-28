#!/usr/bin/env python3
"""Query the vendored ui-ux-pro-max catalog (palette, font pairing, style).

BUILD-mode helper for the shipmate uiux skill: returns candidate catalog rows
for a product type or mood. Rows are candidates to adapt through the OKLCH
formulas in references/colors.md, never authority. Stdlib only, no network.

Usage:
    lookup.py "<product type> <mood keywords>" --domain palette|pairing|style [-n N] [--json]
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

DOMAINS = {
    "palette": {
        "file": "colors.csv",
        "text_fields": ["Product Type", "Notes"],
        "name_field": "Product Type",
    },
    "pairing": {
        "file": "typography.csv",
        "text_fields": ["Font Pairing Name", "Category", "Mood/Style Keywords", "Best For"],
        "name_field": "Font Pairing Name",
    },
    "style": {
        "file": "styles.csv",
        "text_fields": ["Style Category", "Type", "Keywords", "Best For"],
        "name_field": "Style Category",
    },
}

ROLE_FIELDS = [
    "Primary", "On Primary", "Secondary", "On Secondary", "Accent", "On Accent",
    "Background", "Foreground", "Card", "Card Foreground", "Muted", "Muted Foreground",
    "Border", "Destructive", "On Destructive", "Ring",
]

PLAIN_FIELDS = {
    "palette": None,  # roles rendered as `role value` pairs, plus Notes
    "pairing": ["Font Pairing Name", "Heading Font", "Body Font", "Category", "Best For", "CSS Import"],
    "style": ["Style Category", "Keywords", "Effects & Animation", "Best For", "Do Not Use For", "Complexity"],
}

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def tokenize(query):
    return [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]


def score(row, tokens, spec):
    text = " ".join((row.get(f) or "") for f in spec["text_fields"]).lower()
    name = (row.get(spec["name_field"]) or "").lower()
    value = 0
    for token in tokens:
        if token in text:
            value += 1
        if token in name:
            value += 1
    return value


def load_rows(path):
    if not path.is_file():
        print(f"missing data file: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def format_plain(domain, row):
    if domain == "palette":
        roles = " ".join(f"{field} {row.get(field, '')}" for field in ROLE_FIELDS)
        return f"{row.get('Product Type', '')} | {roles} | Notes: {row.get('Notes', '')}"
    parts = []
    for field in PLAIN_FIELDS[domain]:
        value = (row.get(field) or "").strip()
        parts.append(f"{field}: {value}" if field in ("Best For", "CSS Import") else value)
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Search the vendored ui-ux-pro-max catalog for palette, "
        "font-pairing or style candidates.",
    )
    parser.add_argument("query", help='product type and mood keywords, e.g. "fintech dashboard"')
    parser.add_argument("--domain", required=True, choices=sorted(DOMAINS), help="catalog to search")
    parser.add_argument("-n", type=int, default=5, help="maximum hits to print (default 5)")
    parser.add_argument("--json", action="store_true", help="print full rows as a JSON array")
    args = parser.parse_args()

    spec = DOMAINS[args.domain]
    rows = load_rows(DATA_DIR / spec["file"])
    tokens = tokenize(args.query)

    scored = [(score(row, tokens, spec), int(row.get("No") or 0), row) for row in rows]
    hits = sorted((item for item in scored if item[0] > 0), key=lambda item: (-item[0], item[1]))
    top = hits[: max(args.n, 0)]

    if not top:
        print(f'no match for "{args.query}" in {args.domain}')
        return

    if args.json:
        print(json.dumps([row for _, _, row in top], indent=2))
        return

    for _, _, row in top:
        print(format_plain(args.domain, row))


if __name__ == "__main__":
    main()
