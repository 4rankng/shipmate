#!/usr/bin/env python3
"""Command-line front end for Confluence Cloud (REST API v2).

Exists so no caller ever hand-builds an Authorization header. Credentials are
read from the environment inside this process via `auth.get_jira_creds` and are
never accepted as an argument, printed, or placed on a command line.

    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" get 12345
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" children 1835696137
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" search "payment flow"
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" space DEV
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" create --space DEV --title "T" --body-file body.html
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" get 12345 --body-output-file baseline.html
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" update 12345 --expected-body-file baseline.html --body-file body.html --verify
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" title 12345 "New Title"
    python3 "${PAYMENT_PLUGIN_ROOT}/scripts/confluence_cli.py" delete 12345

Page bodies are passed as files, not as argv, so large HTML never lands in shell
history or a process listing. Region defaults to sg; override with --region.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import get_jira_creds, refresh_credentials  # noqa: E402


def _send(method: str, path: str, base_url: str, email: str, api_key: str,
          data: dict | None = None):
    """Issue one authenticated Confluence request.

    The credential is built here and discarded with the stack frame. Callers
    pass a path and a payload, never a header.
    """
    token = base64.b64encode(f"{email}:{api_key}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}

    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()

    req = urllib.request.Request(
        f"{base_url}/wiki/api/v2{path}", data=body, headers=headers, method=method
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status == 204:
            return {"status": "success", "code": 204}
        raw = resp.read()
        return json.loads(raw) if raw else {"status": "success", "code": resp.status}


def _fail(exc: urllib.error.HTTPError, method: str, path: str, region: str):
    detail = exc.read().decode(errors="replace")[:400]
    # Never echo the request headers here — they carry the credential.
    print(f"HTTP {exc.code} on {method} {path}\n{detail}", file=sys.stderr)
    if exc.code == 401:
        print(
            "\nThe credential was rejected. The rc file was re-read and retried "
            f"once. Check that {region.upper()}_JIRA_API_KEY is current and that "
            f"{region.upper()}_JIRA_USERNAME is the account that issued it.",
            file=sys.stderr,
        )
    elif exc.code == 404:
        # Confluence v2 returns an indistinguishable 404 for "no such page" and
        # "your account cannot see this page", including when the account has
        # no Confluence access on that site at all.
        print(
            f"\nA 404 here means the page does not exist on the {region} site, "
            "or this account cannot see it. Confirm the region (--region sg|my) "
            "and that the page id belongs to that site.",
            file=sys.stderr,
        )
    raise SystemExit(1)


def request(method: str, path: str, data: dict | None = None, region: str = "sg"):
    """Authenticated Confluence request with one refresh-and-retry on 401/404.

    A rotated-away token is the common cause of a failure here, and Confluence
    v2 hides it: an unauthenticated request gets the same opaque 404 as a page
    that really is missing. So both codes trigger one retry, but only when the
    shell rc file actually holds a different credential — a genuine 404 with no
    fresher credential costs no extra call.
    """
    base_url, email, api_key = get_jira_creds(region=region)
    try:
        return _send(method, path, base_url, email, api_key, data)
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 404):
            _fail(exc, method, path, region)
        first = exc

    refresh_credentials()
    retry_url, retry_email, retry_key = get_jira_creds(region=region)
    if (retry_url, retry_email, retry_key) == (base_url, email, api_key):
        _fail(first, method, path, region)
    try:
        return _send(method, path, retry_url, retry_email, retry_key, data)
    except urllib.error.HTTPError as exc:
        _fail(exc, method, path, region)


def _get_version(page_id: str, region: str) -> int:
    page = request("GET", f"/pages/{page_id}", region=region)
    return page.get("version", {}).get("number", 1)


def _read_body(args) -> str:
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.body is not None:
        return args.body
    return sys.stdin.read()


def cmd_get(args):
    page = request(
        "GET", f"/pages/{args.id}?body-format={args.body_format}", region=args.region
    )
    print(f"Title:   {page.get('title')}")
    print(f"ID:      {page.get('id')}")
    print(f"Space:   {page.get('spaceId')}")
    print(f"Version: {page.get('version', {}).get('number')}")
    body = page.get("body", {}).get(args.body_format, {}).get("value", "")
    if args.body_output_file:
        Path(args.body_output_file).write_text(body, encoding="utf-8")
        print(
            f"Wrote exact {args.body_format} body for page {page.get('id')} "
            f"to {args.body_output_file}"
        )
        return 0
    if args.body_only:
        print(body)
    else:
        print(f"\n{body[: args.max_body]}")
    return 0


def cmd_children(args):
    data = request("GET", f"/pages/{args.id}/children?limit={args.limit}", region=args.region)
    for child in data.get("results", []):
        print(f"{child.get('id'):>12}  {child.get('title')}")
    return 0


def cmd_search(args):
    query = urllib.parse.quote(args.query)
    data = request("GET", f"/pages?title={query}&limit={args.limit}", region=args.region)
    for page in data.get("results", []):
        print(f"{page.get('id'):>12}  {page.get('title')}")
    return 0


def cmd_space(args):
    data = request("GET", f"/spaces/{args.space}/pages?limit={args.limit}", region=args.region)
    for page in data.get("results", []):
        print(f"{page.get('id'):>12}  {page.get('title')}")
    return 0


def cmd_create(args):
    payload = {
        "spaceId": args.space,
        "status": "current",
        "title": args.title,
        "body": {"representation": "storage", "value": _read_body(args)},
    }
    if args.parent:
        payload["parentId"] = args.parent
    result = request("POST", "/pages", payload, region=args.region)
    print(f"Created {result.get('id')}  {result.get('title')}")
    return 0


def cmd_update(args):
    if not args.expected_body_file or not args.verify:
        print("Confluence update requires --expected-body-file and --verify", file=sys.stderr)
        return 1
    candidate = _read_body(args)
    if not candidate.strip():
        print("Confluence update body must be non-empty", file=sys.stderr)
        return 1
    page = request("GET", f"/pages/{args.id}?body-format=storage", region=args.region)
    current = page.get("body", {}).get("storage", {}).get("value", "")
    if args.expected_body_file:
        expected = Path(args.expected_body_file).read_text(encoding="utf-8")
        if current.rstrip() != expected.rstrip():
            print(
                "Confluence update aborted: current storage body differs from expected baseline",
                file=sys.stderr,
            )
            return 1
    version = page.get("version", {}).get("number", 1) + 1
    payload = {
        "id": args.id,
        "status": "current",
        "title": args.title or page.get("title"),
        "body": {"representation": "storage", "value": candidate},
        "version": {"number": version, "message": args.message or ""},
    }
    result = request("PUT", f"/pages/{args.id}", payload, region=args.region)
    stored = request("GET", f"/pages/{args.id}?body-format=storage", region=args.region)
    actual = stored.get("body", {}).get("storage", {}).get("value", "")
    if _normalize_storage(actual) != _normalize_storage(candidate):
        print("Confluence update verification failed: stored body differs semantically", file=sys.stderr)
        return 1
    print(f"Updated {result.get('id')} to version {version}")
    return 0


_GENERATED_ID_RE = re.compile(r'\s+(?:local-id|ac:local-id|ac:macro-id)="[^"]*"')
_BETWEEN_TAGS_RE = re.compile(r">\s+<")
_OPENING_TAG_RE = re.compile(
    r'''<(?![!/?])(?:[^<>"']+|"[^"]*"|'[^']*')*>''', re.DOTALL
)
_CODE_MACRO_RE = re.compile(
    r'(<ac:structured-macro\b[^>]*\bac:name="code"[^>]*>)(.*?)(</ac:structured-macro>)', re.DOTALL
)
_STRUCTURED_MACRO_RE = re.compile(
    r'(<ac:structured-macro\b[^>]*>)(.*?)(</ac:structured-macro>)', re.DOTALL
)
_DIRECT_PARAM_RE = re.compile(
    r'''<ac:parameter\b(?:[^>"']|"[^"]*"|'[^']*')*(?:/>|>.*?</ac:parameter\s*>)''',
    re.DOTALL,
)
_PAYLOAD_CONTAINER_RES = tuple(
    re.compile(rf'(<{tag}\b[^>]*>)(.*?)(</{tag}>)', re.DOTALL)
    for tag in ("ac:plain-text-body", "pre", "code")
)
_CDATA_RE = re.compile(r'<!\[CDATA\[.*?\]\]>', re.DOTALL)


def _strip_generated_ids(opening_tag: str) -> str:
    """Remove generated ID attributes without inspecting quoted attribute values."""
    output = []
    cursor = 0
    while cursor < len(opening_tag):
        character = opening_tag[cursor]
        if character in ('"', "'"):
            end = opening_tag.find(character, cursor + 1)
            if end == -1:
                output.append(opening_tag[cursor:])
                break
            output.append(opening_tag[cursor:end + 1])
            cursor = end + 1
            continue
        generated_id = _GENERATED_ID_RE.match(opening_tag, cursor)
        if generated_id:
            cursor = generated_id.end()
            continue
        output.append(character)
        cursor += 1
    return "".join(output)


def _normalize_storage(value: str) -> str:
    """Normalize Confluence-generated, semantics-neutral storage changes for readback checks."""
    def sort_code_parameters(match):
        body = match.group(2)
        leading = re.match(r"\s*", body).group(0)
        cursor = len(leading)
        params = []
        while True:
            parameter = _DIRECT_PARAM_RE.match(body, cursor)
            if not parameter:
                break
            params.append(parameter.group(0))
            cursor = parameter.end()
            whitespace = re.match(r"\s*", body[cursor:]).group(0)
            cursor += len(whitespace)
        if not params:
            return match.group(0)
        return match.group(1) + leading + "".join(sorted(params)) + body[cursor:] + match.group(3)

    # Normalize inner code macros first, then their outer structured-macro containers. A single
    # generic regex pass would consume an outer macro and skip its nested code macro.
    value = _CODE_MACRO_RE.sub(sort_code_parameters, value)
    value = _STRUCTURED_MACRO_RE.sub(sort_code_parameters, value)
    protected = []
    placeholder_prefix = "__CONFLUENCE_PROTECTED_"
    while placeholder_prefix in value:
        placeholder_prefix = "_" + placeholder_prefix

    def protect_payload(payload):
        protected.append(payload)
        return f"{placeholder_prefix}{len(protected) - 1}__"

    for container_re in _PAYLOAD_CONTAINER_RES:
        value = container_re.sub(
            lambda match: match.group(1) + protect_payload(match.group(2)) + match.group(3),
            value,
        )
    value = _CDATA_RE.sub(lambda match: protect_payload(match.group(0)), value)
    value = _OPENING_TAG_RE.sub(lambda match: _strip_generated_ids(match.group(0)), value)
    value = _BETWEEN_TAGS_RE.sub("><", value).strip()
    # Decode only after markup-sensitive normalization. Otherwise escaped prose such as
    # ``&lt;span local-id="human"&gt;`` becomes a real-looking tag and can lose text.
    value = html.unescape(value)
    for index, original in enumerate(protected):
        value = value.replace(f"{placeholder_prefix}{index}__", original)
    return value


def cmd_title(args):
    version = _get_version(args.id, args.region) + 1
    page = request("GET", f"/pages/{args.id}?body-format=storage", region=args.region)
    payload = {
        "id": args.id,
        "status": "current",
        "title": args.title,
        "body": {
            "representation": "storage",
            "value": page.get("body", {}).get("storage", {}).get("value", ""),
        },
        "version": {"number": version, "message": "retitle"},
    }
    request("PUT", f"/pages/{args.id}", payload, region=args.region)
    print(f"Retitled {args.id} to {args.title!r}")
    return 0


def cmd_delete(args):
    request("DELETE", f"/pages/{args.id}", region=args.region)
    print(f"Trashed {args.id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--region", choices=["sg", "my"], default="sg")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("get", help="fetch a page")
    p.add_argument("id")
    p.add_argument("--body-format", default="storage",
                   choices=["storage", "atlas_doc_format", "view"])
    p.add_argument("--body-only", action="store_true", help="print only the body")
    p.add_argument("--body-output-file", help="write the exact body to a file without printing it")
    p.add_argument("--max-body", type=int, default=4000)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("children", help="list child pages")
    p.add_argument("id")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_children)

    p = sub.add_parser("search", help="search pages by title")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("space", help="list pages in a space")
    p.add_argument("space")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_space)

    def body_args(sp):
        sp.add_argument("--body-file", help="file containing storage-format HTML")
        sp.add_argument("--body", help="inline body (prefer --body-file)")

    p = sub.add_parser("create", help="create a page")
    p.add_argument("--space", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--parent")
    body_args(p)
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="replace a page body")
    p.add_argument("id")
    p.add_argument("--title")
    p.add_argument("--message")
    p.add_argument(
        "--expected-body-file", required=True,
        help="abort unless current storage matches this baseline",
    )
    p.add_argument(
        "--verify", action="store_true", required=True,
        help="require readback comparison of normalized storage semantics",
    )
    update_body = p.add_mutually_exclusive_group(required=True)
    update_body.add_argument("--body-file", help="file containing storage-format HTML")
    update_body.add_argument("--body", help="inline body (prefer --body-file)")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("title", help="retitle a page")
    p.add_argument("id")
    p.add_argument("title")
    p.set_defaults(func=cmd_title)

    p = sub.add_parser("delete", help="trash a page")
    p.add_argument("id")
    p.set_defaults(func=cmd_delete)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
