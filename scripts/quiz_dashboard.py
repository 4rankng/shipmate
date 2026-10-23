"""Render computed quiz aggregates as a portable, bounded-width chat dashboard."""
from __future__ import annotations

import re
import unicodedata

ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))")
TEXT_FIELDS = {"participant", "target", "source", "session", "coverage", "focus"}
FIELDS = TEXT_FIELDS | {"attempt", "walkthrough", "replaced", "revisit"}
WALKTHROUGHS = ("Provided in this chat", "None in this chat", "Not known")


def plain(text: str) -> str:
    text = ANSI.sub("", text)
    return "".join(" " if c.isspace() else c for c in text if c.isspace() or
                   unicodedata.category(c) not in ("Cc", "Cf", "Cs")).strip()


def clean(text: str) -> str:
    return " ".join(plain(text).split())


def columns(text: str) -> int:
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in clean(text).split():
        if line and columns(line + " " + word) <= width:
            line += " " + word
            continue
        if line:
            lines.append(line)
            line = ""
        while columns(word) > width:
            used, end = 0, 0
            for char in word:
                size = columns(char)
                if used + size > width:
                    break
                used += size
                end += 1
            lines.append(word[:end])
            word = word[end:]
        line = word
    return lines + ([line] if line else []) or [""]


def context(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) - FIELDS:
        raise ValueError("report context contains unsupported fields")
    for field in TEXT_FIELDS & value.keys():
        if not isinstance(value[field], str) or not clean(value[field]):
            raise ValueError("report text fields must be nonempty strings")
    attempt = value.get("attempt")
    if attempt is not None and (type(attempt) is not int or attempt not in range(1, 4)):
        raise ValueError("report attempt must be 1, 2, 3 or null")
    replaced = value.get("replaced", 0)
    if type(replaced) is not int or replaced < 0:
        raise ValueError("report replaced must be a nonnegative integer")
    if value.get("walkthrough", "Not known") not in WALKTHROUGHS:
        raise ValueError("report walkthrough must use an observed-use label")
    revisits = value.get("revisit", [])
    if not isinstance(revisits, list) or len(revisits) > 8:
        raise ValueError("report revisit must be a list of at most 8 references")
    for revisit in revisits:
        if (not isinstance(revisit, dict) or set(revisit) != {"detail", "source"}
                or any(not isinstance(v, str) or not clean(v) for v in revisit.values())):
            raise ValueError("each revisit requires nonempty detail and source text")
    return {**value, **{field: clean(value[field]) for field in TEXT_FIELDS & value.keys()},
            "revisit": [{field: clean(text) for field, text in revisit.items()}
                        for revisit in revisits]}


def render(summary: dict, metadata: dict, width: int = 76) -> str:
    if type(width) is not int or not 64 <= width <= 120:
        raise ValueError("dashboard width must be between 64 and 120 columns")
    metadata = context(metadata)
    inner, lines = width - 4, []

    def row(text="", indent=0):
        text = plain(text)
        parts = [text] if columns(text) <= inner - indent else wrap(text, inner - indent)
        for part in parts:
            part = " " * indent + part
            lines.append("│ " + part + " " * (inner - columns(part)) + " │")

    def section(title):
        lines.append("├" + "─" * (width - 2) + "┤")
        row(title)

    counts = summary["counts"]
    lines.append("╭" + "─" * (width - 2) + "╮")
    title, status = "SHIPMATE / QUIZ REPORT", summary["status"].upper()
    row(title + " " * (inner - len(title) - len(status)) + status)
    if summary["percent"] is not None:
        percent = summary["percent"]
        filled = (percent * 24 + 50) // 100
        meter = "█" * filled + "░" * (24 - filled)
        label = summary["level"] or "Provisional"
        row(f"{percent}%  {meter}  {counts['correct']}/{summary['total']}  {label}")
        if summary["passed"] is not None:
            row("Quiz passed!" if summary["passed"] else "Not yet...")
    else:
        reason = ("source changed" if summary["freshness"] == "stale" else
                  "answer integrity compromised" if summary["integrity"] == "compromised" else
                  "insufficient submitted answers")
        row("No current score — " + reason)
    row(" · ".join(f"{counts[name]} {name}" for name in
                   ("correct", "wrong", "skipped", "unanswered")))

    section("SESSION")
    row("Target: " + metadata.get("target", "Not supplied"))
    source = metadata.get("source")
    row("Source: " + (source + " · " + summary["freshness"] if source else "Not supplied"))
    if summary["freshness"] == "unverified":
        row("Source not rechecked; result covers the earlier snapshot only.")
    row("When: " + metadata.get("session", "Not supplied"))
    attempt = metadata.get("attempt")
    attempt_text = "Attempt not known" if attempt is None else f"Attempt {attempt}/3"
    if attempt is not None:
        attempt_text += f" · {3 - attempt} remaining"
    row(metadata.get("participant", "Chat participant") + " · " + attempt_text)

    for state in ("Needs review", "Partly assessed", "Not assessed", "Demonstrated"):
        topics = [topic for topic, result in summary["topics"].items() if result == state]
        if topics:
            section(f"{state.upper()} ({len(topics)})")
            # Every frozen topic stays visible; grouping never changes its result.
            for topic in topics:
                row("• " + clean(topic))

    if metadata.get("revisit"):
        section("REVISIT")
        for index, revisit in enumerate(metadata["revisit"], 1):
            row(f"{index}. {revisit['detail']}")
            row(revisit["source"], indent=3)
    if metadata.get("focus"):
        row("Focus: " + metadata["focus"])
    section("COVERAGE")
    row(metadata.get("coverage", "Scope not supplied"))
    row("Walkthrough: " + metadata.get("walkthrough", "Not known"))
    replaced = metadata.get("replaced", 0)
    if replaced:
        row(f"{replaced} question{'s' if replaced != 1 else ''} replaced")
    lines.append("├" + "─" * (width - 2) + "┤")
    row("Session self-check only; not approval or verified understanding.")
    lines.append("╰" + "─" * (width - 2) + "╯")
    return "\n".join(lines)
