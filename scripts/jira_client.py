#!/usr/bin/env python3
"""Shared Jira API client with region-aware auth and ADF parsing.

Handles both SG (gxsbank.atlassian.net) and MY (gxbank.atlassian.net).
MY search requires POST to /rest/api/3/search/jql (old GET endpoint returns 410).

IMPORTANT for SHIPRM tickets: The description field MUST be a plain wiki markup
string, NOT an ADF (Atlassian Document Format) JSON object. ADF breaks table
rendering. Always pass description as a string, e.g.:
    {"fields": {"description": "||col1||col2||\\n|val1|val2|"}}
NOT:
    {"fields": {"description": {"type": "doc", "version": 1, ...}}}

Wiki markup tables MUST have consecutive rows with NO blank lines between them.
Use sanitize_wiki_tables() to clean go-kit rnotes output before posting.

Usage from another script:
    import sys
    sys.path.insert(0, "/absolute/path/to/payment-plugin/scripts")
    from jira_client import jira_get, jira_post, jira_put, jira_delete, extract_adf_text, extract_adf_tables, sanitize_wiki_tables
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

from auth import get_jira_creds, refresh_credentials


class JiraAuthError(RuntimeError):
    """Raised when a credential is rejected, with no secret in the message."""


STALE_CREDENTIAL_HINT = (
    "Jira/Confluence rejected the credential (401). This usually means the API "
    "token in the process environment is stale — rotated in your shell rc file "
    "after this process started. The rc file was re-read and retried once and "
    "it still failed, so check the token is current and that "
    "{REGION}_JIRA_USERNAME matches the account that issued it."
)


def _make_request(path: str, base_url: str, email: str, api_key: str,
                  data: Optional[dict] = None, method: str = "GET") -> dict:
    credentials = base64.b64encode(f"{email}:{api_key}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    }
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        if not raw:
            return {}
        return json.loads(raw)


def _request(path: str, region: Optional[str], ticket_key: Optional[str],
             data: Optional[dict] = None, method: str = "GET") -> dict:
    """Authenticated request with one refresh-and-retry on 401.

    A 401 is the only reliable signal that the token carried in os.environ has
    been rotated away, so it is the one case where re-reading the shell rc file
    is worth it. Anything else propagates unchanged.
    """
    base_url, email, api_key = get_jira_creds(region=region, ticket_key=ticket_key)
    try:
        return _make_request(path, base_url, email, api_key, data=data, method=method)
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
    refresh_credentials()
    retry_url, retry_email, retry_key = get_jira_creds(region=region, ticket_key=ticket_key)
    if (retry_url, retry_email, retry_key) == (base_url, email, api_key):
        raise JiraAuthError(STALE_CREDENTIAL_HINT)
    try:
        return _make_request(path, retry_url, retry_email, retry_key, data=data, method=method)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise JiraAuthError(STALE_CREDENTIAL_HINT) from None
        raise


def jira_get(path: str, region: Optional[str] = None,
             ticket_key: Optional[str] = None) -> dict:
    return _request(path, region, ticket_key)


def jira_post(path: str, data: dict, region: Optional[str] = None,
              ticket_key: Optional[str] = None) -> dict:
    return _request(path, region, ticket_key, data=data, method="POST")


def jira_put(path: str, data: dict, region: Optional[str] = None,
             ticket_key: Optional[str] = None) -> dict:
    return _request(path, region, ticket_key, data=data, method="PUT")


def jira_delete(path: str, region: Optional[str] = None,
                ticket_key: Optional[str] = None) -> dict:
    return _request(path, region, ticket_key, method="DELETE")


def search_jql(jql: str, region: Optional[str] = None,
               ticket_key: Optional[str] = None, limit: int = 20) -> dict:
    """Search Jira using JQL. Uses POST /rest/api/3/search/jql for MY compatibility."""
    base_url, email, api_key = get_jira_creds(region=region, ticket_key=ticket_key)
    # Use the newer search endpoint that works for both SG and MY
    path = f"/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "maxResults": limit,
        "fields": ["summary", "status", "priority", "updated"],
    }
    return _make_request(path, base_url, email, api_key, data=payload, method="POST")


# ---------------------------------------------------------------------------
# Wiki markup helpers
# ---------------------------------------------------------------------------
def sanitize_wiki_tables(text: str) -> str:
    """Remove blank lines between wiki markup table rows.

    Jira wiki markup tables require consecutive rows. Blank lines between
    rows split the table into separate single-row tables. Use this to clean
    go-kit rnotes output before posting to Jira.

    Example:
        Input:  "||h1||h2||\\n\\n|a|b|\\n\\n|c|d|"
        Output: "||h1||h2||\\n|a|b|\\n|c|d|"
    """
    lines = text.split('\n')
    result = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('||') or stripped.startswith('|'):
            in_table = True
            result.append(line)
        elif in_table and stripped == '':
            # Skip blank lines inside tables
            continue
        else:
            in_table = False
            result.append(line)
    return '\n'.join(result)


# ---------------------------------------------------------------------------
# ADF (Atlassian Document Format) extraction
# ---------------------------------------------------------------------------
def extract_adf_text(node: dict) -> str:
    """Extract plain text from Atlassian Document Format node."""
    if not node:
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    texts = []
    for child in node.get("content", []):
        texts.append(extract_adf_text(child))
    return " ".join(t for t in texts if t)


def extract_adf_tables(doc: dict) -> List[List[List[str]]]:
    """Extract all tables from ADF doc.

    Returns list of tables. Each table is list of rows. Each row is list of cell texts.
    """
    tables = []
    for node in doc.get("content", []):
        if node.get("type") == "table":
            table = []
            for row in node.get("content", []):
                if row.get("type") == "tableRow":
                    cells = []
                    for cell in row.get("content", []):
                        if cell.get("type") == "tableCell":
                            cells.append(extract_adf_text(cell).strip())
                    table.append(cells)
            tables.append(table)
    return tables
