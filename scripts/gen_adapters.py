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


def copy_tree_files(root: Path, skill: str, tree: str) -> dict[str, str]:
    """Copy a whole skill directory into a discovery tree such as .agents/skills.

    Markdown files get the same link rewriting as generated single-file surfaces
    so ../../internal/... links resolve from the new location; other files are
    copied verbatim. The mirrored internal/ copy is excluded: one repo-root
    internal/ already backs the rewritten links.
    """
    outputs: dict[str, str] = {}
    source_root = root / "skills" / skill
    output_root = root / tree / skill
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or "internal" in path.relative_to(source_root).parts:
            continue
        relative = path.relative_to(source_root).as_posix()
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".md":
            source_dir = posixpath.dirname(f"skills/{skill}/{relative}")
            output_dir = posixpath.dirname(f"{tree}/{skill}/{relative}")
            content = rewrite_links(content, source_dir=source_dir, output_dir=output_dir)
        outputs[str(output_root / relative)] = content
    return outputs


def generate(root: Path) -> dict[str, str]:
    spec = json.loads((root / "adapters.json").read_text(encoding="utf-8"))
    titles = spec["titles"]
    outputs: dict[str, str] = {}
    # omp resolves skill:// paths inside the skill's own directory and clamps
    # "../"-escaping links to it, so each skill needs its own copy of internal/
    # for the installed plugin's ../../internal/... links to resolve.
    internal_dir = root / "internal"
    internal_files = {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(internal_dir.rglob("*"))
        if path.is_file()
    } if internal_dir.is_dir() else {}
    for skill in spec["skills"]:
        doc = load_skill(root, skill)
        for tree, surface in spec["trees"].items():
            output_dir = root / tree
            if surface.get("copy_skill"):
                outputs.update(copy_tree_files(root, skill, tree))
                continue
            body = render(surface, doc, titles[skill], tree, spec["argument_hints"][skill])
            outputs[str(output_dir / surface["file"].replace("{skill}", skill))] = body
        for relative, content in internal_files.items():
            outputs[f"skills/{skill}/{relative}"] = content
        # Discovery copies of a skill dir must not carry the per-skill internal/
        # mirror: their ../../internal links are rewritten to the repo root.
    return outputs


def expected_surface_files(root: Path, spec: dict) -> set[str]:
    expected = set()
    for skill in spec["skills"]:
        for tree, surface in spec["trees"].items():
            if surface.get("copy_skill"):
                source_root = root / "skills" / skill
                expected.update(
                    str(root / tree / skill / path.relative_to(source_root).as_posix())
                    for path in source_root.rglob("*")
                    if path.is_file() and "internal" not in path.relative_to(source_root).parts
                )
            else:
                expected.add(str(root / tree / surface["file"].replace("{skill}", skill)))
    return expected


def surface_set_mismatches(root: Path, spec: dict) -> list[str]:
    """Report adapter files that are missing from or orphaned within the trees.

    Byte-clean regeneration proves the existing surfaces are reproducible, not
    that the set matches the current skill list: a renamed or deleted skill can
    leave stale copies behind that still pass --check.
    """
    expected = expected_surface_files(root, spec)
    actual = set()
    for tree, surface in spec["trees"].items():
        for path in (root / tree).rglob("*"):
            if not path.is_file():
                continue
            if surface.get("copy_skill") or path.suffix in {
                Path(s["file"]).suffix for s in spec["trees"].values()
            }:
                actual.add(str(path))
    return sorted(
        f"missing: {path}" for path in expected - actual
    ) + sorted(f"orphan: {path}" for path in actual - expected)



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
    spec = json.loads((root / "adapters.json").read_text(encoding="utf-8"))
    for relative, content in sorted(outputs.items()):
        path = root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(relative)
    stale.extend(surface_set_mismatches(root, spec))
    if stale:
        print("stale adapter surfaces: " + ", ".join(stale))
        return 1
    print(f"{len(outputs)} adapter surfaces byte-clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
