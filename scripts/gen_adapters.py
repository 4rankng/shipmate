#!/usr/bin/env python3
"""Generate per-harness adapter surfaces from skills/*/SKILL.md.

Reads adapters.json (per-tree header/footer templates) plus each skill's SKILL.md
(name, description and body), rewrites relative links for each output's depth, and
writes the copy trees: commands/, .cursor/rules/, .windsurf/workflows/,
.continue/prompts/. --check exits 1 when any committed surface differs from a fresh
generation, so CI fails on hand-edited copies.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
DESCRIPTION = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
LINK = re.compile(r"(\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
EXTERNAL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def load_skill(root: Path, skill: str) -> dict:
    text = (root / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    description = ""
    body = text
    match = FRONT_MATTER.match(text)
    if match:
        found = DESCRIPTION.search(match.group(1))
        if found:
            description = found.group(1).strip().strip('"')
        body = text[match.end():]
    return {"skill": skill, "description": description, "body": body.strip()}


def rewrite_links(body: str, source_dir: str, output_dir: str) -> str:
    def replace(match: re.Match) -> str:
        target = match.group(2)
        anchor = ""
        if target.startswith("#"):
            return match.group(0)
        if "#" in target:
            target, anchor = target.split("#", 1)
            anchor = "#" + anchor
        if not target or EXTERNAL.match(target):
            return match.group(0)
        resolved = posixpath.normpath(posixpath.join(source_dir, target))
        relative = posixpath.relpath(resolved, output_dir)
        # group(3) already carries the closing paren; appending another emitted
        # "](path))" and broke every rewritten link before the fix.
        return f"]({relative}{anchor}{match.group(3)}"

    return LINK.sub(replace, body)


def render(surface: dict, skill_doc: dict, title: str, tree: str, argument_hint: str) -> str:
    body = rewrite_links(skill_doc["body"], source_dir=f"skills/{skill_doc['skill']}",
                         output_dir=tree)
    text = surface["header"] + body + surface["footer"]
    return (text.replace("{skill}", skill_doc["skill"])
                .replace("{title}", title)
                .replace("{description}", skill_doc["description"])
                .replace("{argument_hint}", argument_hint))


def generate(root: Path) -> dict[str, str]:
    spec = json.loads((root / "adapters.json").read_text(encoding="utf-8"))
    titles = spec["titles"]
    outputs: dict[str, str] = {}
    for skill in spec["skills"]:
        doc = load_skill(root, skill)
        for tree, surface in spec["trees"].items():
            output_dir = root / tree
            body = render(surface, doc, titles[skill], tree, spec["argument_hints"][skill])
            outputs[str(output_dir / surface["file"].replace("{skill}", skill))] = body
    return outputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="plugin root (default: current directory)")
    parser.add_argument("--check", action="store_true",
                        help="verify committed surfaces match generation; write nothing")
    args = parser.parse_args(argv)
    root = Path(args.root)
    outputs = generate(root)
    if not args.check:
        for relative, content in outputs.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        print(f"generated {len(outputs)} adapter surfaces")
        return 0
    stale = []
    for relative, content in sorted(outputs.items()):
        path = root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(relative)
    if stale:
        print("stale adapter surfaces: " + ", ".join(stale))
        return 1
    print(f"{len(outputs)} adapter surfaces byte-clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
