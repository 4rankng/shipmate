#!/usr/bin/env python3
"""Check final MR prose on stdin without publishing it or echoing its contents.

This catches structural boilerplate; the author must still verify meaning and diagrams.
Required user/repository sections can be exempted individually with a stated reason.
"""
import argparse
import json
import re
import sys

FORBIDDEN = {"checklist", "risks and limitations", "deployment", "rollback", "verification",
             "testing", "test evidence", "test cases", "testing procedure",
             "validation performed", "additional notes"}
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CHECKBOX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[[ xX]\](?:\s|$)")
TEST_CASE = re.compile(r"^\s*(?:[-*+]|\d+[.)])?\s*TC\d+\s*:", re.I)
COMMAND = re.compile(r"^\s*(?:[-*+]\s+|`)(?:`)?(?:go test\b|pytest\b|"
                     r"python\S* -m unittest\b|golangci-lint\b)")


def normalize(heading):
    return " ".join(heading.strip().strip("*_`").lower().split())


def validate(text, required_headings=(), exception_reason=""):
    required = {normalize(h) for h in required_headings}
    if required and (not exception_reason.strip() or any(not h or h == "*" for h in required)):
        raise ValueError("Required-heading exceptions need exact headings and an explicit reason")
    errors, fence, exempt_depth, exception_used = [], None, None, False

    def error(line, code):
        errors.append({"line": line, "code": code})

    if not text.strip():
        error(1, "empty-description")
    for number, line in enumerate(text.splitlines(), 1):
        boundary = FENCE.match(line)
        if boundary:
            mark, suffix = boundary.groups()
            if fence is None:
                fence = (mark[0], len(mark), number)
            elif mark[0] == fence[0] and len(mark) >= fence[1] and not suffix.strip():
                fence = None
            continue
        if fence is not None:
            continue
        heading = HEADING.match(line)
        if heading:
            level, name = len(heading[1]), normalize(heading[2])
            if exempt_depth is not None and level <= exempt_depth:
                exempt_depth = None
            if name in required:
                exempt_depth = level
                exception_used = True
            elif name in FORBIDDEN and exempt_depth is None:
                error(number, "report-section")
        if exempt_depth is not None:
            continue
        for pattern, code in ((CHECKBOX, "checklist-item"), (TEST_CASE, "test-inventory"),
                              (COMMAND, "test-command")):
            if pattern.match(line):
                error(number, code)
    if fence is not None:
        error(fence[2], "unclosed-code-fence")
    return {"valid": not errors, "errors": errors, "exception_used": exception_used}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required-heading", action="append", default=[])
    parser.add_argument("--exception-reason", default="")
    args = parser.parse_args()
    try:
        result = validate(sys.stdin.read(), args.required_heading, args.exception_reason)
    except (ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
