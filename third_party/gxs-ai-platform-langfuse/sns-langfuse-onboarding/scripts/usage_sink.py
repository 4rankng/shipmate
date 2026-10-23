"""Metadata-only session usage records, with stable identity and retry timestamps."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import urllib.request

ENDPOINT = "https://langfuse.stg.dakota.com.sg/api/public/otel/v1/traces"
VERSION = "1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def identity(record):
    values = ["sns-session-usage-v1"]
    for key in ("agent", "session_id", "kind", "name"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 512:
            raise ValueError("Incomplete or invalid session usage evidence.")
        values.append(value)
    if record["agent"] not in {"codex", "copilot"} or record["kind"] not in {"skill", "plugin"}:
        raise ValueError("Unsupported session usage evidence.")
    digest = hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()
    return digest[:32], digest[32:48]


def payload(record, settings, developer, timestamp):
    trace_id, span_id = identity(record)
    attrs = {
        "langfuse.observation.type": "event",
        "langfuse.trace.name": "SNS " + record["kind"] + " usage",
        "langfuse.session.id": record["session_id"],
        "langfuse.user.id": developer,
        "user.id": developer,
        "langfuse.environment": settings["LANGFUSE_TRACING_ENVIRONMENT"],
        "langfuse.observation.metadata.sns_usage_version": VERSION,
        "langfuse.observation.metadata.kind": record["kind"],
        "langfuse.observation.metadata.unit": "session",
        "langfuse.observation.metadata.agent": record["agent"],
        "langfuse.observation.metadata.evidence": record["evidence"],
        "langfuse.observation.metadata.source_trace_id": record["source_trace_id"],
        "langfuse.observation.metadata.source_span_id": record["source_span_id"],
    }
    attributes = [{"key": key, "value": {"stringValue": value}} for key, value in attrs.items()]
    return {"resourceSpans": [{"resource": {"attributes": [
        {"key": "service.name", "value": {"stringValue": "sns-session-usage"}}
    ]}, "scopeSpans": [{"scope": {"name": "sns-session-usage", "version": VERSION}, "spans": [{
        "traceId": trace_id, "spanId": span_id, "name": record["name"],
        "kind": 1, "startTimeUnixNano": str(timestamp), "endTimeUnixNano": str(timestamp + 1),
        "attributes": attributes, "status": {"code": 1},
    }]}]}]}


def send_payload(body, authorization):
    request = urllib.request.Request(ENDPOINT, json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Authorization": authorization,
        "x-langfuse-ingestion-version": "4",
    })
    # Disable proxy discovery and redirects: keys go only to the fixed TLS endpoint.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=15) as response:
            result = json.loads(response.read(1024 * 1024) or b"{}")
        partial = result.get("partialSuccess", {})
        if int(partial.get("rejectedSpans", 0)):
            raise ValueError("Langfuse rejected session usage records.")
    except Exception:
        raise ValueError("Session usage upload failed; credentials and response content were not displayed.") from None


class UsageSink:
    """Store only hashed IDs, first timestamp and acknowledgement locally.

    A resumed client session cannot move its usage date or inflate counts.
    Stable remote IDs preserve identity after an uncertain HTTP response.
    Langfuse v4 can retain physical replay rows: widgets must use
    uniqueSessionIds/uniq, never raw row count, to count sessions safely.
    """
    def __init__(self, settings, developer, authorization, directory=None, sender=send_payload):
        self.settings, self.developer, self.authorization = settings, developer, authorization
        self.sender = sender
        directory = Path(directory or Path.home() / ".local/state/sns-langfuse")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        namespace = hashlib.sha256(settings["LANGFUSE_PUBLIC_KEY"].encode()).hexdigest()[:16]
        path = directory / ("usage-" + namespace + ".sqlite")
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        os.chmod(path, 0o600)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, first_ns INTEGER NOT NULL, sent INTEGER NOT NULL DEFAULT 0)")
        self.db.commit()

    def publish(self, records):
        uploaded, previously_sent = 0, 0
        for record in sorted(records, key=lambda r: r["observed_at_ns"]):
            trace_id, _ = identity(record)
            stamp = record.get("observed_at_ns")
            if not isinstance(stamp, int) or isinstance(stamp, bool) or stamp <= 0:
                raise ValueError("Session usage evidence has no valid timestamp.")
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO receipts (id, first_ns) VALUES (?, ?)", (trace_id, stamp))
            stamp, sent = self.db.execute("SELECT first_ns, sent FROM receipts WHERE id=?", (trace_id,)).fetchone()
            if sent:
                previously_sent += 1
                continue
            self.sender(payload(record, self.settings, self.developer, stamp), self.authorization)
            with self.db:
                self.db.execute("UPDATE receipts SET sent=1 WHERE id=?", (trace_id,))
            uploaded += 1
        return {"uploaded": uploaded, "already_recorded": previously_sent}

    def close(self):
        self.db.close()
