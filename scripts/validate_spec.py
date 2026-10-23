"""Validate Specify drafts without changing files or publishing anywhere."""
import argparse
import json
import re
from pathlib import Path

TARGET_CHARACTERS = 1200
TARGET_WORDS_EXCLUSIVE = 150
ORDER = ["Problem / Context", "Definitions", "Objective", "Acceptance Criteria", "Out of Scope",
         "Technical Notes"]
REQUIRED = ["Problem / Context", "Objective", "Acceptance Criteria"]
BULLET_LIMITS = {"Definitions": 6, "Out of Scope": 3, "Technical Notes": 3}
AC_LINE = re.compile(r"- (AC-\d+)(?: \([^()\n]+\))?: Given (.+), When (.+), Then (.+)")
DEFINITION_LINE = re.compile(r"- \*\*[^*\n]+\*\*: \S.*")
PLACEHOLDER = re.compile(r"<(?:state|event|observable result|Short title|Code or term)>"
                         r"|<(?:One or two|Verified meaning|Exclusion|Essential agreed)[^<>\n]*>"
                         r"|NEEDS CLARIFICATION")
# TODO/TBD can be domain values. Only reject explicit annotations or a marker that
# replaces an entire line, bullet or Given/When/Then clause, not ordinary prose.
OPEN_MARKER = re.compile(
    r"\b(?:TBD|TODO)[ \t]*:|\[(?:TBD|TODO)(?:[ \t]*:[^\]\n]*)?\]"
    r"|(?:^[ \t]*(?:[-*][ \t]+)?|\b(?:Given|When|Then)[ \t]+)"
    r"(?:TBD|TODO)[ \t]*[.!?]?(?=[ \t]*(?:$|,[ \t]*(?:When|Then)\b))", re.MULTILINE)
# Advisory only: these never change validity or the length target.
VAGUE = re.compile(r"\b(?:correct(?:ly)?|proper(?:ly)?|appropriate(?:ly)?|graceful(?:ly)?|robust(?:ly)?"
                   r"|seamless(?:ly)?|efficient(?:ly)?|quickly|user[- ]friendly|sufficient|reasonable"
                   r"|as needed|as far as possible|if possible|where possible|etc)\b", re.I)
GUARANTEE = re.compile(r"exactly[- ]once|never (?:get |be )?stuck|guarantee[sd]?", re.I)


def validate(text):
    errors, warnings, smells = [], [], []
    characters, words = len(text), len(text.split())
    # Length is a target, not a cap: exceeding it needs a stated reason, not a rewrite failure.
    if characters > TARGET_CHARACTERS:
        warnings.append("Over the 1,200-character target; state the strong reason with the draft.")
    if words >= TARGET_WORDS_EXCLUSIVE:
        warnings.append("Over the fewer-than-150-words target; state the strong reason with the draft.")
    # Parse either line-ending convention without changing raw length accounting.
    text = text.replace("\r\n", "\n")
    headings = re.findall(r"^## (.+)$", text, re.MULTILINE)
    if "User Story" in headings:
        errors.append("User Story is replaced by Objective; use the current section order.")
    present = [h for h in ORDER if h in headings]
    if headings != present or any(h not in headings for h in REQUIRED):
        errors.append("Use Problem / Context, optional Definitions, Objective, Acceptance Criteria, "
                      "then optional Out of Scope and Technical Notes.")
    sections = re.split(r"^## .+$", text, flags=re.MULTILINE)
    if sections[0].strip():
        errors.append("Remove the preamble.")
    if PLACEHOLDER.search(text) or OPEN_MARKER.search(text):
        errors.append("Replace template placeholders and TBD/TODO/NEEDS CLARIFICATION markers; "
                      "ask the open question instead of publishing it.")
    bodies = dict(zip(headings, sections[1:]))
    if any(not body.strip() for body in bodies.values()):
        errors.append("Remove empty optional sections; fill required sections.")
    criteria = bodies.get("Acceptance Criteria", "").strip().splitlines()
    ids, scenarios = [], {}
    if not criteria:
        errors.append("At least one acceptance criterion is required.")
    for line in criteria:
        match = AC_LINE.fullmatch(line)
        if not match:
            errors.append("Each acceptance criterion needs an AC ID, optional (title) and "
                          "Given/When/Then bullet.")
        else:
            ac_id, given, when, then = match.groups()
            ids.append(ac_id)
            smells.extend(f"{ac_id}: replace vague '{word}' with an observable result."
                          for word in VAGUE.findall(line))
            first, first_then = scenarios.setdefault((given.lower(), when.lower()), (ac_id, then))
            if first != ac_id and first_then.lower() != then.lower():
                smells.append(f"{first} and {ac_id} share Given/When but differ in Then; "
                              "confirm they cannot conflict.")
    if GUARANTEE.search(text):
        smells.append("Delivery/recovery guarantee wording needs verified evidence and boundaries.")
    if len(ids) != len(set(ids)):
        errors.append("Acceptance criterion IDs must be unique.")
    for name, limit in BULLET_LIMITS.items():
        if name not in bodies or not bodies[name].strip():
            continue
        lines = bodies[name].strip().splitlines()
        pattern = DEFINITION_LINE if name == "Definitions" else re.compile(r"- \S.*")
        if len(lines) > limit or any(not pattern.fullmatch(line) for line in lines):
            shape = "`**Term**: meaning` bullets" if name == "Definitions" else "non-empty bullets"
            errors.append(f"{name} allows at most {limit} {shape}.")
    return {"valid": not errors, "within_target": not warnings, "characters": characters,
            "words": words, "warnings": warnings, "errors": errors, "smells": smells}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()
    try:
        # Preserve CRLF and all whitespace: count the exact file content.
        text = args.draft.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        parser.exit(2, "Cannot read draft as UTF-8.\n")
    result = validate(text)
    print(json.dumps(result))  # Never echo ticket content.
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
