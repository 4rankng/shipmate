"""Extract observed Codex skill/plugin use from an explicitly scoped API batch.

This module does not query Langfuse, discover local sessions, read files, or
upload telemetry. Its caller must supply only observations from the authorized
current run. The records measure sessions with detected usage, not invocation
counts, installed inventory, successful task completion, or L3 delivery.

Root-turn skill/plugin tags are explicit evidence. Plugin ownership can also
be established by a recorded skill-access TOOL whose command references a
supported plugin cache path. ERROR tools are excluded; DEFAULT/WARNING tools
are recorded accesses, not a claim that the underlying workflow succeeded.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional


_MISSING = object()
_ACCESS_TOOLS = {
    "exec_command", "exec", "shell", "local_shell", "bash", "js",
    "read_mcp_resource",
}
_INPUT_FIELDS = ("cmd", "command", "code", "uri")
_CACHE_ACCESS = re.compile(
    r"(?:^|/)\.(?:codex|copilot)/plugins/cache/"
    r"(?P<marketplace>[A-Za-z0-9_.-]+)/"
    r"(?P<plugin>[A-Za-z0-9_.@+-]+)/"
    r"[A-Za-z0-9_.+-]+/skills/"
    r"[A-Za-z0-9_.@+-]+/"
    r"(?:SKILL\.md(?=$|[\s\"'`;:)])|scripts/[^\s\"'`;:)]+)"
)
_TIMESTAMP = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d{1,9}))?(?P<zone>Z|[+-]\d{2}:\d{2})$"
)


def _get(row: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return default


def _nonempty(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _timestamp_ns(row: Mapping[str, Any]) -> Optional[int]:
    explicit = row.get("observed_at_ns")
    if isinstance(explicit, int) and not isinstance(explicit, bool) and explicit > 0:
        return explicit
    value = _get(row, "startTime", "start_time")
    if not isinstance(value, str):
        return None
    match = _TIMESTAMP.fullmatch(value)
    if not match:
        return None
    try:
        parsed = datetime.fromisoformat(
            match["date"] + match["zone"].replace("Z", "+00:00")
        )
        delta = parsed.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    except ValueError:
        return None
    seconds = delta.days * 86400 + delta.seconds
    nanos = int((match["fraction"] or "").ljust(9, "0"))
    result = seconds * 1_000_000_000 + nanos
    return result if result > 0 else None


def _root_turn(row: Mapping[str, Any]) -> bool:
    if row.get("type") != "AGENT" or row.get("name") != "Codex Turn":
        return False
    explicit = _get(row, "isRootObservation", "is_root_observation", default=_MISSING)
    if explicit is not _MISSING:
        return explicit is True
    # A projection that omitted parent information cannot prove root status.
    parent = _get(row, "parentObservationId", "parent_observation_id", default=_MISSING)
    return parent is None or parent == ""


def _tags(row: Mapping[str, Any]) -> Iterable[str]:
    value = row.get("tags")
    if isinstance(value, list):
        return (tag for tag in value if isinstance(tag, str))
    return ()


def _input_text(value: Any) -> Optional[str]:
    """Inspect only tool arguments, never model text, output, or arbitrary metadata."""
    if isinstance(value, str):
        # Langfuse can expose JSON-encoded tool arguments as a string.
        if value.lstrip().startswith("{"):
            try:
                decoded = json.loads(value)
            except (ValueError, TypeError):
                return None
            return _input_text(decoded)
        return value
    if not isinstance(value, Mapping):
        return None
    for field in _INPUT_FIELDS:
        candidate = value.get(field)
        if isinstance(candidate, str):
            return candidate
        if isinstance(candidate, list) and all(isinstance(part, str) for part in candidate):
            return " ".join(candidate)
    # Some API projections explicitly wrap the original tool arguments.
    if "args" in value:
        return _input_text(value["args"])
    return None


def _plugin_owners(row: Mapping[str, Any]) -> Iterable[str]:
    if row.get("type") != "TOOL" or not str(row.get("name", "")).startswith("skill:"):
        return ()
    if str(row.get("level", "DEFAULT")).upper() not in {"DEFAULT", "WARNING"}:
        return ()
    metadata = row.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("codex.tool_name") not in _ACCESS_TOOLS:
        return ()
    text = _input_text(row.get("input"))
    if text is None:
        return ()
    return {
        match["plugin"] + "@" + match["marketplace"]
        for match in _CACHE_ACCESS.finditer(text)
    }


def extract_codex_usage(observations: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Return earliest evidence per (session_id, kind, name), sorted stably.

    Every returned item contains only identifiers, a canonical name, timestamp
    and a fixed evidence label. Raw prompts, tool arguments/results, paths and
    arbitrary metadata are never returned. Missing session/source IDs or a
    valid timestamp cause an observation to be skipped, not assigned a guess.

    Names from explicit tags retain their suffix. Cache-derived plugin names
    use ``plugin@marketplace``; an unqualified explicit plugin tag is not merged
    with a qualified owner without authoritative alias information.
    """
    earliest: Dict[tuple, Dict[str, Any]] = {}
    for row in observations:
        if not isinstance(row, Mapping):
            continue
        session = _nonempty(_get(row, "sessionId", "session_id"))
        trace_id = _nonempty(_get(row, "traceId", "trace_id"))
        span_id = _nonempty(_get(row, "id", "spanId", "span_id"))
        observed_at = _timestamp_ns(row)
        if session is None or trace_id is None or span_id is None or observed_at is None:
            continue

        candidates = []
        if _root_turn(row):
            for tag in _tags(row):
                kind, separator, name = tag.partition(":")
                if separator and kind in {"skill", "plugin"} and name.strip():
                    candidates.append((kind, name, "codex_root_turn_explicit_" + kind + "_tag"))
        for owner in _plugin_owners(row):
            candidates.append(("plugin", owner, "codex_detected_skill_based_plugin_access"))

        for kind, name, evidence in candidates:
            record = {
                "agent": "codex",
                "session_id": session,
                "kind": kind,
                "name": name,
                "observed_at_ns": observed_at,
                "source_trace_id": trace_id,
                "source_span_id": span_id,
                "evidence": evidence,
            }
            key = (session, kind, name)
            previous = earliest.get(key)
            rank = (observed_at, trace_id, span_id, evidence)
            if previous is None or rank < (
                previous["observed_at_ns"], previous["source_trace_id"],
                previous["source_span_id"], previous["evidence"],
            ):
                earliest[key] = record
    return sorted(earliest.values(), key=lambda row: (
        row["observed_at_ns"], row["session_id"], row["kind"], row["name"],
    ))
