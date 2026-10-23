#!/usr/bin/env python3
"""Jira workflow operations: BFS pathfinding, ticket transitions, and bulk move.

Imports shared API client from jira_client.py for all HTTP operations.

Usage from another script:
    import sys
    sys.path.insert(0, "/absolute/path/to/payment-plugin/scripts")
    from jira_workflow import move_ticket_to, bulk_move_children
"""

import json
import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jira_client import jira_get, jira_post


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def get_transitions(key: str, **kwargs) -> list:
    """Return available transitions for a ticket."""
    return jira_get(f"/rest/api/3/issue/{key}/transitions", **kwargs).get("transitions", [])


# Statuses that actually resolve/close a ticket and therefore accept a `resolution` field.
# Other screened transitions (e.g. MY "Blocked") have a screen for OTHER custom fields
# (Blocked Justification / Blocked Reason) and will REJECT a `resolution` with HTTP 400.
_RESOLVING_STATUSES = {"closed", "done", "resolved", "cancelled", "canceled", "won't do", "wont do"}


def _resolution_fields(transition: dict) -> Optional[dict]:
    """Return {"resolution": ...} ONLY when the transition's TARGET status is a resolving
    state AND the transition has a screen. Injecting `resolution` into a non-resolving
    screened transition (e.g. Blocked) causes HTTP 400. Returns None otherwise.

    Note: resolving transitions may also need extra required fields (e.g. MY Closed needs
    customfield_10045 RCA) — callers handle those separately; this only covers `resolution`.
    """
    if not transition.get("hasScreen"):
        return None
    target = transition.get("to", {}).get("name", "").lower()
    if target in _RESOLVING_STATUSES:
        return {"resolution": {"name": "Won't Do"}}
    return None


def get_current_status(key: str, **kwargs) -> str:
    """Return current status name for a ticket."""
    return jira_get(f"/rest/api/3/issue/{key}?fields=status", **kwargs)["fields"]["status"]["name"]


def get_issue_type(key: str, **kwargs) -> str:
    """Return issue type name for a ticket."""
    return jira_get(f"/rest/api/3/issue/{key}?fields=issuetype", **kwargs)["fields"]["issuetype"]["name"]


def do_transition(key: str, transition_id: str, fields: dict = None, **kwargs):
    """Execute a single transition on a ticket."""
    payload = {"transition": {"id": str(transition_id)}}
    if fields:
        payload["fields"] = fields
    jira_post(f"/rest/api/3/issue/{key}/transitions", payload, **kwargs)


# ---------------------------------------------------------------------------
# BFS pathfinding
# ---------------------------------------------------------------------------

def find_path_to_status(key: str, target_status: str, **kwargs) -> Optional[list]:
    """BFS to find shortest path of transition IDs from current state to target.

    Returns list of (transition_id, transition_name, target_status_name, hasScreen) tuples,
    or None if unreachable.

    NOTE: This BFS modifies ticket state as it explores. It cannot backtrack,
    so it explores one path deeply then retries from the new state.
    """
    current = get_current_status(key, **kwargs)
    if current.lower() == target_status.lower():
        return []

    # Check direct transitions first
    for t in get_transitions(key, **kwargs):
        if t["to"]["name"].lower() == target_status.lower():
            return [(t["id"], t["name"], t["to"]["name"], t.get("hasScreen", False))]

    # BFS exploration (modifies state)
    visited = {current}
    queue = [(current, [])]

    while queue:
        current_status, path = queue.pop(0)
        transitions = get_transitions(key, **kwargs)
        for t in transitions:
            next_status = t["to"]["name"]
            if next_status in visited:
                continue
            new_path = path + [(t["id"], t["name"], next_status, t.get("hasScreen", False))]
            if next_status.lower() == target_status.lower():
                return new_path
            visited.add(next_status)
            try:
                fields = _resolution_fields(t)
                do_transition(key, t["id"], fields, **kwargs)
                queue.append((next_status, new_path))
            except Exception:
                continue
        # Can't backtrack in state-modifying BFS; stop after one level
        break

    # Retry from wherever we ended up
    current = get_current_status(key, **kwargs)
    if current.lower() != target_status.lower():
        for t in get_transitions(key, **kwargs):
            if t["to"]["name"].lower() == target_status.lower():
                return [(t["id"], t["name"], target_status, t.get("hasScreen", False))]
    return None


# ---------------------------------------------------------------------------
# High-level move
# ---------------------------------------------------------------------------

def move_ticket_to(key: str, target_status: str, **kwargs) -> bool:
    """Move a ticket to the target status, using BFS pathfinding if needed.

    Returns True on success.
    """
    current = get_current_status(key, **kwargs)
    if current.lower() == target_status.lower():
        print(f"  {key}: already {current}")
        return True

    # Try direct transition
    for t in get_transitions(key, **kwargs):
        if t["to"]["name"].lower() == target_status.lower():
            fields = _resolution_fields(t)
            do_transition(key, t["id"], fields, **kwargs)
            new_status = get_current_status(key, **kwargs)
            print(f"  {key}: {current} -> {new_status}")
            return True

    # Pathfinding through intermediate states
    print(f"  {key}: no direct transition from '{current}' to '{target_status}', pathfinding...")
    visited_states = set()
    for _ in range(15):
        current = get_current_status(key, **kwargs)
        if current.lower() == target_status.lower():
            print(f"  {key}: reached {current}")
            return True
        if current in visited_states:
            break
        visited_states.add(current)

        transitions = get_transitions(key, **kwargs)
        for t in transitions:
            next_name = t["to"]["name"].lower()
            if next_name not in visited_states and t["name"] not in ["Cancel", "In Backlog"]:
                try:
                    fields = _resolution_fields(t)
                    do_transition(key, t["id"], fields, **kwargs)
                    new_status = get_current_status(key, **kwargs)
                    print(f"  {key}: {current} -> {new_status}")
                    # Check if target is now reachable
                    for nt in get_transitions(key, **kwargs):
                        if nt["to"]["name"].lower() == target_status.lower():
                            nt_fields = _resolution_fields(nt)
                            do_transition(key, nt["id"], nt_fields, **kwargs)
                            final = get_current_status(key, **kwargs)
                            print(f"  {key}: {new_status} -> {final}")
                            return True
                    break  # moved to new state, continue exploring
                except Exception:
                    continue

    print(f"  {key}: FAILED to reach '{target_status}', current: {get_current_status(key, **kwargs)}")
    return False


# ---------------------------------------------------------------------------
# Bulk move
# ---------------------------------------------------------------------------

def bulk_move_children(parent_key: str, target_status: str, **kwargs):
    """Find all linked child items of a parent ticket and move each to target status."""
    parent = jira_get(f"/rest/api/3/issue/{parent_key}?fields=summary,issuelinks,subtasks", **kwargs)
    print(f"Parent: {parent_key} - {parent['fields']['summary']}")

    child_keys = []

    for st in parent["fields"].get("subtasks", []):
        status = st["fields"]["status"]["name"]
        if status.lower() != target_status.lower():
            child_keys.append(st["key"])
            print(f"  Subtask: {st['key']} [{status}] {st['fields']['summary']}")

    for link in parent["fields"].get("issuelinks", []):
        for direction in ["outwardIssue", "inwardIssue"]:
            if direction in link:
                li = link[direction]
                status = li["fields"]["status"]["name"]
                key = li["key"]
                if status.lower() != target_status.lower():
                    child_keys.append(key)
                    print(f"  Linked: {key} [{status}] {li['fields']['summary']}")

    print(f"\nTotal tickets to move: {len(child_keys)}")

    for key in child_keys:
        move_ticket_to(key, target_status, **kwargs)

    # Verify
    print("\n--- Final Verification ---")
    parent = jira_get(f"/rest/api/3/issue/{parent_key}?fields=issuelinks,subtasks", **kwargs)
    not_done = []
    for link in parent["fields"].get("issuelinks", []):
        for direction in ["outwardIssue", "inwardIssue"]:
            if direction in link:
                li = link[direction]
                if li["fields"]["status"]["name"].lower() != target_status.lower():
                    not_done.append(f"{li['key']} [{li['fields']['status']['name']}]")
    for st in parent["fields"].get("subtasks", []):
        if st["fields"]["status"]["name"].lower() != target_status.lower():
            not_done.append(f"{st['key']} [{st['fields']['status']['name']}]")

    if not_done:
        print(f"NOT {target_status}:")
        for n in not_done:
            print(f"  {n}")
        return not_done
    else:
        print(f"ALL child items are now {target_status}!")
    return not_done


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: jira_workflow.py <ticket_key> <target_status> [--region sg|my]")
        sys.exit(1)

    _key = sys.argv[1]
    _target = sys.argv[2]
    _kw = {}
    if "--region" in sys.argv:
        _kw["region"] = sys.argv[sys.argv.index("--region") + 1]

    move_ticket_to(_key, _target, **_kw)
