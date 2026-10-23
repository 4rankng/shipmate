#!/usr/bin/env python3
"""Command-line front end for the Jira modules.

Replaces long inline `python3 -c "..."` invocations with named subcommands.

Usage:
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" view TSE-1170
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" comments TSE-1170 [--all] [--json]
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" snapshot TSE-1170 --expected-updated TS [--decision-comment-id ID]
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" add-label TSE-1170 l3-workflow
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" set-description TSE-1170 --file description.md  # destructive
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" set-summary TSE-1170 --summary "Plain title"  # verified
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" move TSE-1170 "In Development"
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" move-children RGPAYM-2582 "Ready for Production"
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" list [--region sg]
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/jira_cli.py" search "payment failed"

Region is auto-detected from the ticket prefix; override with --region sg|my.

`set-description` overwrites the whole description with no Jira-side backup: read the full
existing description first (`view <KEY> --max-description 100000`) and keep a copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import get_jira_creds  # noqa: E402
from jira_client import (  # noqa: E402
    JiraAuthError,
    extract_adf_text,
    jira_get,
    jira_put,
    search_jql,
)
from jira_workflow import bulk_move_children, move_ticket_to  # noqa: E402


def _region(args):
    """--region is SUPPRESS-defaulted so it survives in either position."""
    return getattr(args, "region", None)


def _kw(args) -> dict:
    region = _region(args)
    return {"region": region} if region else {}


def cmd_view(args) -> int:
    ticket = jira_get(
        f"/rest/api/3/issue/{args.key}?expand=renderedFields,names",
        ticket_key=args.key,
        **_kw(args),
    )
    f = ticket["fields"]
    print(f"Key:         {args.key}")
    print(f"Summary:     {f.get('summary', '')}")
    print(f"Status:      {f.get('status', {}).get('name', '')}")
    print(f"Type:        {f.get('issuetype', {}).get('name', '')}")
    print(f"Priority:    {(f.get('priority') or {}).get('name', '-')}")
    print(f"Reporter:    {(f.get('reporter') or {}).get('displayName', '?')}")
    print(f"Assignee:    {(f.get('assignee') or {}).get('displayName', 'Unassigned')}")
    print(f"Labels:      {f.get('labels', [])}")
    print(f"Created:     {f.get('created', '')[:10]}")
    print(f"Updated:     {f.get('updated', '')}")
    desc = ticket.get("renderedFields", {}).get("description") or extract_adf_text(
        f.get("description") or {}
    )
    print(f"\nDescription:\n{desc[:args.max_description]}")
    return 0


def _comment_id_sort_key(comment: dict):
    value = str(comment.get("id", ""))
    return (comment.get("created", ""), not value.isdigit(), int(value) if value.isdigit() else value)


def _comment_inventory(comments: list[dict]) -> list[dict]:
    return [
        {
            "id": str(c.get("id", "")),
            "author": {
                "account_id": c.get("author", {}).get("accountId", ""),
                "display_name": c.get("author", {}).get("displayName", ""),
            },
            "created": c.get("created", ""),
            "updated": c.get("updated", ""),
            "body": c.get("body"),
        }
        for c in sorted(comments, key=_comment_id_sort_key)
    ]


def _fetch_comments(args) -> list[dict]:
    comments = []
    seen_ids = set()
    start_at = 0
    page_size = 100 if args.all else args.limit
    order = "created" if args.all else "-created"
    expected_total = None
    while True:
        data = jira_get(
            f"/rest/api/3/issue/{args.key}/comment"
            f"?maxResults={page_size}&startAt={start_at}&orderBy={order}",
            ticket_key=args.key,
            **_kw(args),
        )
        page = data.get("comments", [])
        if not args.all:
            return page

        try:
            page_start = int(data["startAt"])
            page_total = int(data["total"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("comment page omitted valid startAt/total metadata") from exc
        if page_start != start_at:
            raise ValueError(f"comment page started at {page_start}, expected {start_at}")
        if expected_total is None:
            expected_total = page_total
        elif page_total != expected_total:
            raise ValueError("comment total changed during pagination")
        if not page:
            if start_at == expected_total:
                break
            raise ValueError("comment page was empty before the reported total was reached")

        for comment in page:
            comment_id = str(comment.get("id", ""))
            if not comment_id:
                raise ValueError("comment page contained an entry without an ID")
            if comment_id in seen_ids:
                raise ValueError(f"comment ID {comment_id} repeated across pages")
            seen_ids.add(comment_id)
        comments.extend(page)
        start_at += len(page)
        if start_at == expected_total:
            break
        if start_at > expected_total:
            raise ValueError("comment count exceeded the reported total")

    if expected_total is None or len(comments) != expected_total or len(seen_ids) != expected_total:
        raise ValueError("comment inventory count did not match the reported total")
    return comments


def _get_specification_issue(args) -> dict:
    return jira_get(
        f"/rest/api/3/issue/{args.key}?fields=summary,description,updated",
        ticket_key=args.key,
        **_kw(args),
    )


def _issue_updated(issue: dict) -> str:
    updated = issue.get("fields", {}).get("updated") or ""
    if not updated:
        raise ValueError("Jira issue response omitted fields.updated")
    return updated


def cmd_comments(args) -> int:
    # Read one complete inventory. Issue timestamps include unrelated edits and
    # cannot establish semantic freshness; the controller compares source meaning.
    try:
        comments = _fetch_comments(args)
    except ValueError as exc:
        print(f"ERROR: unable to read complete comment inventory: {exc}", file=sys.stderr)
        return 1

    if args.json:
        inventory = _comment_inventory(comments)
        output = {"comments": inventory}
        if args.all:
            canonical = json.dumps(
                inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            output["inventory_sha256"] = hashlib.sha256(canonical).hexdigest()
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0

    for c in comments:
        author = c.get("author", {}).get("displayName", "?")
        body = extract_adf_text(c.get("body", {}))
        if not args.full_body:
            body = body[: args.max_body]
        print(f"[{c.get('created', '')[:10]}] id={c['id']} {author}: {body}")
    return 0


def cmd_snapshot(args) -> int:
    comment_ids = sorted(
        set(args.decision_comment_id),
        key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value),
    )
    issue = _get_specification_issue(args)
    fields = issue.get("fields", {})
    try:
        before = _issue_updated(issue)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if before != args.expected_updated:
        print(
            "ERROR: Jira changed after comment inventory; rebuild the inventory and decision IDs",
            file=sys.stderr,
        )
        return 1

    decision_comments = []
    for comment_id in comment_ids:
        comment = jira_get(
            f"/rest/api/3/issue/{args.key}/comment/{comment_id}",
            ticket_key=args.key,
            **_kw(args),
        )
        decision_comments.append({"id": str(comment["id"]), "body": comment.get("body")})

    try:
        after = _issue_updated(_get_specification_issue(args))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if before != after:
        print(
            "ERROR: Jira changed while freezing the specification; rebuild the inventory",
            file=sys.stderr,
        )
        return 1

    specification = {
        "key": args.key,
        "summary": fields.get("summary") or "",
        "description": fields.get("description"),
        "decision_comments": decision_comments,
    }
    canonical = json.dumps(
        specification,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    snapshot = {
        "jira_updated": fields.get("updated") or "",
        "spec_sha256": hashlib.sha256(canonical).hexdigest(),
        "specification": specification,
    }
    print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def cmd_add_label(args) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.label):
        print("ERROR: label must contain only letters, digits, dot, underscore, or hyphen",
              file=sys.stderr)
        return 1

    path = f"/rest/api/3/issue/{args.key}?fields=labels"
    issue = jira_get(path, ticket_key=args.key, **_kw(args))
    labels = issue.get("fields", {}).get("labels") or []
    if args.label not in labels:
        jira_put(
            f"/rest/api/3/issue/{args.key}",
            {"update": {"labels": [{"add": args.label}]}},
            ticket_key=args.key,
            **_kw(args),
        )

    verified = jira_get(path, ticket_key=args.key, **_kw(args))
    if args.label not in (verified.get("fields", {}).get("labels") or []):
        print(f"ERROR: Jira did not retain label {args.label!r} on {args.key}", file=sys.stderr)
        return 1
    print(f"Label {args.label!r} verified on {args.key}")
    return 0


_INLINE_MARK_RE = re.compile(r"(\*\*[^*\n]+\*\*|`[^`\n]+`)")


def _inline_nodes(text: str) -> list[dict]:
    """Render the strong and code marks used by the concise specification template."""
    nodes: list[dict] = []
    cursor = 0
    for match in _INLINE_MARK_RE.finditer(text):
        if match.start() > cursor:
            nodes.append({"type": "text", "text": text[cursor:match.start()]})
        token = match.group(0)
        if token.startswith("**"):
            nodes.append({
                "type": "text",
                "text": token[2:-2],
                "marks": [{"type": "strong"}],
            })
        else:
            nodes.append({
                "type": "text",
                "text": token[1:-1],
                "marks": [{"type": "code"}],
            })
        cursor = match.end()
    if cursor < len(text):
        nodes.append({"type": "text", "text": text[cursor:]})
    return [node for node in nodes if node["text"]]


def _split_markdown_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [
        cell.strip().replace(r"\|", "|")
        for cell in re.split(r"(?<!\\)\|", stripped[1:-1])
    ]


def _is_markdown_table_separator(line: str, width: int) -> bool:
    cells = _split_markdown_table_row(line)
    return bool(
        cells
        and len(cells) == width
        and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)
    )


def _adf_table_row(cells: list[str], *, header: bool) -> dict:
    cell_type = "tableHeader" if header else "tableCell"
    return {
        "type": "tableRow",
        "content": [
            {
                "type": cell_type,
                "content": [{"type": "paragraph", "content": _inline_nodes(cell)}],
            }
            for cell in cells
        ],
    }


def text_to_adf(text: str) -> dict:
    """Convert plain markdown-ish text into an Atlassian Document Format doc.

    Jira REST v3 rejects a plain string for rich-text fields such as
    `description`; it requires an ADF document. This covers the block shapes the
    specification template emits (headings, bullet lists, tables, fenced code,
    paragraphs, strong labels, and inline code).
    """
    content: list = []
    bullets: list = []
    fence_lang = None
    fence_lines: list = []

    def flush_bullets() -> None:
        if bullets:
            content.append({"type": "bulletList", "content": list(bullets)})
            bullets.clear()

    lines = (text or "").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if fence_lang is not None:
            if stripped.startswith("```"):
                block = {"type": "codeBlock", "content": []}
                if fence_lang:
                    block["attrs"] = {"language": fence_lang}
                code = "\n".join(fence_lines)
                if code:
                    block["content"] = [{"type": "text", "text": code}]
                content.append(block)
                fence_lang, fence_lines = None, []
            else:
                fence_lines.append(line)
            index += 1
            continue

        if stripped.startswith("```"):
            flush_bullets()
            fence_lang, fence_lines = stripped[3:].strip(), []
            index += 1
            continue

        if not stripped:
            flush_bullets()
            index += 1
            continue

        header_cells = _split_markdown_table_row(line)
        if (
            header_cells
            and index + 1 < len(lines)
            and _is_markdown_table_separator(lines[index + 1], len(header_cells))
        ):
            flush_bullets()
            table_rows = [_adf_table_row(header_cells, header=True)]
            index += 2
            while index < len(lines):
                row_cells = _split_markdown_table_row(lines[index])
                if not row_cells or len(row_cells) != len(header_cells):
                    break
                table_rows.append(_adf_table_row(row_cells, header=False))
                index += 1
            content.append({
                "type": "table",
                "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                "content": table_rows,
            })
            continue

        heading = re.match(r"^(#{1,6})\s+(.*\S)\s*$", stripped)
        if heading:
            flush_bullets()
            content.append({
                "type": "heading",
                "attrs": {"level": len(heading.group(1))},
                "content": _inline_nodes(heading.group(2)),
            })
            index += 1
            continue

        bullet = re.match(r"^[-*+]\s+(.*\S)\s*$", stripped)
        if bullet:
            bullets.append({
                "type": "listItem",
                "content": [{
                    "type": "paragraph",
                    "content": _inline_nodes(bullet.group(1)),
                }],
            })
            index += 1
            continue

        flush_bullets()
        content.append({
            "type": "paragraph",
            "content": _inline_nodes(stripped),
        })
        index += 1

    if fence_lang is not None:
        block = {"type": "codeBlock", "content": []}
        if fence_lang:
            block["attrs"] = {"language": fence_lang}
        code = "\n".join(fence_lines)
        if code:
            block["content"] = [{"type": "text", "text": code}]
        content.append(block)
    flush_bullets()

    if not content:
        content = [{"type": "paragraph", "content": []}]
    return {"type": "doc", "version": 1, "content": content}


def cmd_set_description(args) -> int:
    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    jira_put(
        f"/rest/api/3/issue/{args.key}",
        {"fields": {"description": text_to_adf(text)}},
        ticket_key=args.key,
        **_kw(args),
    )
    print(f"Description replaced for {args.key} (previous description is gone)")
    return 0


SUMMARY_MAX_LENGTH = 255


def cmd_set_summary(args) -> int:
    summary = args.summary.strip()
    if not summary or "\n" in summary or "\r" in summary or len(summary) > SUMMARY_MAX_LENGTH:
        print(f"ERROR: summary must be one non-empty line of at most {SUMMARY_MAX_LENGTH} characters",
              file=sys.stderr)
        return 1
    path = f"/rest/api/3/issue/{args.key}?fields=summary"
    previous = jira_get(path, ticket_key=args.key, **_kw(args)).get("fields", {}).get("summary") or ""
    if previous != summary:
        jira_put(
            f"/rest/api/3/issue/{args.key}",
            {"fields": {"summary": summary}},
            ticket_key=args.key,
            **_kw(args),
        )
    stored = jira_get(path, ticket_key=args.key, **_kw(args)).get("fields", {}).get("summary") or ""
    if stored != summary:
        print(f"ERROR: Jira did not retain the new summary on {args.key}", file=sys.stderr)
        return 1
    print(json.dumps({"key": args.key, "previous_summary": previous, "summary": stored,
                      "verified": True}))
    return 0


def cmd_move(args) -> int:
    return 0 if move_ticket_to(args.key, args.status, **_kw(args)) else 1


def cmd_move_children(args) -> int:
    # A bulk transition where every child failed must not report success.
    not_done = bulk_move_children(args.key, args.status, **_kw(args))
    return 1 if not_done else 0


def _print_issues(result) -> None:
    for issue in result.get("issues", []):
        f = issue["fields"]
        priority = (f.get("priority") or {}).get("name", "-")
        print(
            f"  {issue['key']} [{f['status']['name']}] (P:{priority}) "
            f"{f['summary']} — updated {f.get('updated', '')[:10]}"
        )


def cmd_list(args) -> int:
    region = _region(args) or "sg"
    _, email, _ = get_jira_creds(region=region)
    if not email:
        print(f"No Jira username configured for region {region}", file=sys.stderr)
        return 1
    _print_issues(
        search_jql(
            f'assignee = "{email}" ORDER BY updated DESC', region=region, limit=args.limit
        )
    )
    return 0


def cmd_search(args) -> int:
    jql = args.jql or f'text ~ "{args.query}" ORDER BY created DESC'
    _print_issues(search_jql(jql, region=_region(args) or "sg", limit=args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    # SUPPRESS is load-bearing. A subparser parses into a fresh namespace and
    # copies every attribute back over the parent's, so an ordinary default of
    # None would silently overwrite a --region given *before* the subcommand.
    # With SUPPRESS the attribute only exists when the flag was actually passed.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--region", choices=["sg", "my"], default=argparse.SUPPRESS,
                        help="override region detection")

    # Do NOT call set_defaults("region") here: it mutates the shared action
    # object that every subparser inherited, turning SUPPRESS back into None
    # and reintroducing the overwrite. Consumers use _region() instead.
    parser = argparse.ArgumentParser(description=__doc__, parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("view", help="show a ticket", parents=[common])
    p.add_argument("key")
    p.add_argument("--max-description", type=int, default=2000)
    p.set_defaults(func=cmd_view)

    p = sub.add_parser("comments", help="list comments", parents=[common])
    p.add_argument("key")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--max-body", type=int, default=500)
    p.add_argument("--all", action="store_true", help="read every comment page, oldest first")
    p.add_argument("--full-body", action="store_true", help="do not truncate rendered comment text")
    p.add_argument("--json", action="store_true", help="emit raw full-body comment inventory as JSON")
    p.set_defaults(func=cmd_comments)

    p = sub.add_parser(
        "snapshot",
        help="emit a deterministic specification snapshot and SHA-256",
        parents=[common],
    )
    p.add_argument("key")
    p.add_argument(
        "--decision-comment-id",
        action="append",
        default=[],
        help="comment ID whose body is part of the current requirement audit export; repeat as needed",
    )
    p.add_argument(
        "--expected-updated",
        required=True,
        help="require the Jira updated timestamp returned by comments --all --json",
    )
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("add-label", help="idempotently add and verify a label", parents=[common])
    p.add_argument("key")
    p.add_argument("label")
    p.set_defaults(func=cmd_add_label)

    p = sub.add_parser(
        "set-description",
        help="replace a ticket description (destructive: overwrites it, no backup)",
        parents=[common],
    )
    p.add_argument("key")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file")
    p.set_defaults(func=cmd_set_description)

    p = sub.add_parser(
        "set-summary",
        help="replace a ticket summary and verify it by readback (prints the previous summary)",
        parents=[common],
    )
    p.add_argument("key")
    p.add_argument("--summary", required=True)
    p.set_defaults(func=cmd_set_summary)

    p = sub.add_parser("move", help="transition a ticket, with BFS pathfinding", parents=[common])
    p.add_argument("key")
    p.add_argument("status")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("move-children", help="transition every child of a parent", parents=[common])
    p.add_argument("key")
    p.add_argument("status")
    p.set_defaults(func=cmd_move_children)

    p = sub.add_parser("list", help="list tickets assigned to you", parents=[common])
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("search", help="search tickets by text or JQL", parents=[common])
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--jql", help="raw JQL, overrides the text query")
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(func=cmd_search)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except JiraAuthError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as exc:
        # A traceback here buries the one useful fact: which status Jira sent.
        detail = exc.read().decode(errors="replace")[:400]
        print(f"ERROR: HTTP {exc.code} from Jira\n{detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
