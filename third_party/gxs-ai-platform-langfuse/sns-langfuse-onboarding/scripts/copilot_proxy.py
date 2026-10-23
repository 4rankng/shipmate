"""Process-scoped Copilot OTLP forwarding and explicit session-usage evidence.

The caller owns credentials, launcher configuration, and normalized uploads.
This module reads no files or environment, saves no raw telemetry, and never
derives usage from available-skill inventories. Copilot's HTTP/JSON exporter
remains active; its mutually exclusive file exporter is not used.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
import gzip
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
import re
import secrets
import ssl
import threading
from typing import Callable, Dict, List, Tuple
import zlib


DESTINATION = "https://langfuse.stg.dakota.com.sg/api/public/otel/v1/traces"
_HOST = "langfuse.stg.dakota.com.sg"
_PATH = "/api/public/otel/v1/traces"
_LOCAL_PATH = "/v1/traces"
_TOKEN_HEADER = "X-SNS-Usage-Token"
_EVENT = "github.copilot.skill.invoked"
_SKILL = "gen_ai.skill.name"  # Verified Copilot CLI 1.0.92 content-off event.
_LEGACY_SKILL = "github.copilot.skill.name"
_PLUGIN = "github.copilot.skill.plugin_name"
_PLUGIN_VERSION = "github.copilot.skill.plugin_version"
_SESSION = "gen_ai.conversation.id"


def _text(value, limit=256):
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return None
    return value


def _identifier(value, length):
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{%d}" % length, value):
        if set(value) != {"0"}:
            return value.lower()
    return None


def _attributes(items):
    """Read only string-valued OTLP attributes; keep raw content out of output."""
    if not isinstance(items, list):
        return {}
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("value"), dict):
            continue
        key = item.get("key")
        if key in {_SESSION, _SKILL, _LEGACY_SKILL, _PLUGIN, _PLUGIN_VERSION}:
            result[key] = item["value"].get("stringValue")
    return result


class SkillUsageExtractor:
    """Bounded in-memory, once-per-session usage extraction from OTLP JSON."""

    def __init__(self, *, max_records=10000, max_trace_sessions=10000):
        self.coverage = Counter()
        self._seen = set()
        self._trace_sessions = OrderedDict()
        self._max_records = max_records
        self._max_trace_sessions = max_trace_sessions

    def extract(self, document) -> List[Dict]:
        if not isinstance(document, dict) or not isinstance(document.get("resourceSpans"), list):
            self.coverage["unsupported_payload"] += 1
            return []
        spans = []
        for resource in document["resourceSpans"]:
            if not isinstance(resource, dict):
                continue
            for scope in resource.get("scopeSpans", []):
                if isinstance(scope, dict) and isinstance(scope.get("spans"), list):
                    spans.extend(s for s in scope["spans"] if isinstance(s, dict))

        # Cache only trace-scoped root identities. Two passes make batch order
        # irrelevant. Never reuse the last session globally for another trace.
        for span in spans:
            trace_id = _identifier(span.get("traceId"), 32)
            session = _text(_attributes(span.get("attributes")).get(_SESSION))
            if trace_id and session and not span.get("parentSpanId"):
                previous = self._trace_sessions.get(trace_id)
                if previous and previous != session:
                    self.coverage["conflicting_session_identity"] += 1
                    self._trace_sessions[trace_id] = None
                elif trace_id not in self._trace_sessions:
                    self._trace_sessions[trace_id] = session
                self._trace_sessions.move_to_end(trace_id)
                while len(self._trace_sessions) > self._max_trace_sessions:
                    self._trace_sessions.popitem(last=False)
                    self.coverage["trace_identity_evicted"] += 1

        records = []
        for span in spans:
            events = span.get("events", [])
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict) or event.get("name") != _EVENT:
                    continue
                self.coverage["explicit_skill_events"] += 1
                trace_id = _identifier(span.get("traceId"), 32)
                span_id = _identifier(span.get("spanId"), 16)
                session = _text(_attributes(span.get("attributes")).get(_SESSION))
                if not session and trace_id:
                    session = self._trace_sessions.get(trace_id)
                attrs = _attributes(event.get("attributes"))
                current_skill = _text(attrs.get(_SKILL))
                legacy_skill = _text(attrs.get(_LEGACY_SKILL))
                skill = current_skill or legacy_skill
                if current_skill and legacy_skill and current_skill != legacy_skill:
                    # Conflicting explicit names cannot be attributed reliably.
                    skill = None
                    self.coverage["conflicting_skill_identity"] += 1
                stamp = event.get("timeUnixNano")
                if isinstance(stamp, bool) or not isinstance(stamp, (str, int)):
                    stamp = None
                elif not re.fullmatch(r"[0-9]{1,20}", str(stamp)) or int(stamp) <= 0:
                    stamp = None
                if not all((session, trace_id, span_id, skill, stamp)):
                    self.coverage["skill_events_missing_identity"] += 1
                    for field, value in (("session", session), ("trace_id", trace_id),
                                         ("span_id", span_id), ("skill", skill), ("timestamp", stamp)):
                        if not value:
                            self.coverage["missing_" + field] += 1
                    continue
                plugin = _text(attrs.get(_PLUGIN))
                version = _text(attrs.get(_PLUGIN_VERSION))
                for kind, name in (("skill", skill), ("plugin", plugin)):
                    if not name:
                        continue
                    key = (session, kind, name)
                    if key in self._seen:
                        self.coverage["duplicate_session_uses"] += 1
                        continue
                    if len(self._seen) >= self._max_records:
                        self.coverage["usage_capacity_exceeded"] += 1
                        continue
                    record = {
                        "agent": "copilot", "session_id": session,
                        "kind": kind, "name": name,
                        "observed_at_ns": int(stamp),
                        "source_trace_id": trace_id, "source_span_id": span_id,
                        "evidence": "otel_span_event:" + _EVENT,
                    }
                    if plugin:
                        record["plugin_name"] = plugin
                    if version:
                        record["plugin_version"] = version
                    records.append(record)
                    self._seen.add(key)
        self.coverage["usage_records"] += len(records)
        return records


class CopilotProxy:
    """Temporary authenticated loopback receiver forwarding to one HTTPS host.

    Use as a context manager around one Copilot process. Configure its traces
    protocol as http/json, endpoint as trace_url, and headers as local_headers.
    The caller must replace inherited OTLP authentication headers with the
    local token, keeping project keys in this process only. on_record should
    enqueue a record quickly; close waits for the current request/callback.
    """

    def __init__(self, authorization: str, on_record: Callable[[Dict], None], *,
                 timeout: float = 15.0, max_body_bytes: int = 16 * 1024 * 1024,
                 max_decoded_bytes: int = 32 * 1024 * 1024):
        if not _text(authorization, 8192) or "\r" in authorization or "\n" in authorization:
            raise ValueError("Invalid upstream authorization")
        if timeout <= 0 or max_body_bytes <= 0 or max_decoded_bytes <= 0:
            raise ValueError("Proxy bounds must be positive")
        self._authorization = authorization
        self._on_record = on_record
        self._token = secrets.token_urlsafe(32)
        self._timeout = timeout
        self._max_body_bytes = max_body_bytes
        self._max_decoded_bytes = max_decoded_bytes
        self._extractor = SkillUsageExtractor()
        self.coverage = self._extractor.coverage
        self._server = None
        self._thread = None

    @property
    def base_url(self):
        if self._server is None:
            raise RuntimeError("Proxy has not started")
        return "http://127.0.0.1:%d" % self._server.server_port

    @property
    def trace_url(self):
        return self.base_url + _LOCAL_PATH

    @property
    def local_headers(self):
        return {_TOKEN_HEADER: self._token}

    def _forward(self, body: bytes, content_type: str, content_encoding: str) -> Tuple[int, bytes, str]:
        # HTTPSConnection verifies certificates by default. It does not follow
        # redirects; neither the incoming path nor any supplied URL is used.
        connection = http.client.HTTPSConnection(_HOST, 443, timeout=self._timeout,
                                                  context=ssl.create_default_context())
        headers = {"Authorization": self._authorization,
                   "x-langfuse-ingestion-version": "4", "Content-Type": content_type}
        if content_encoding:
            headers["Content-Encoding"] = content_encoding
        try:
            connection.request("POST", _PATH, body=body, headers=headers)
            response = connection.getresponse()
            response_body = response.read(65537)
            if len(response_body) > 65536:
                raise ValueError("Upstream response exceeds size limit")
            if 300 <= response.status < 400:
                raise ValueError("Upstream redirects are not allowed")
            return response.status, response_body, response.getheader("Content-Type", "application/json")
        finally:
            connection.close()

    def _observe(self, body: bytes, content_type: str, content_encoding: str):
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            self.coverage["unsupported_content_type"] += 1
            return
        try:
            if content_encoding == "gzip":
                with gzip.GzipFile(fileobj=io.BytesIO(body)) as compressed:
                    decoded = compressed.read(self._max_decoded_bytes + 1)
            elif not content_encoding:
                decoded = body
            else:
                self.coverage["unsupported_content_encoding"] += 1
                return
            if len(decoded) > self._max_decoded_bytes:
                self.coverage["decoded_body_too_large"] += 1
                return
            document = json.loads(decoded)
            records = self._extractor.extract(document)
        except (ValueError, TypeError, OSError, EOFError, RecursionError, zlib.error):
            self.coverage["invalid_json_or_gzip"] += 1
            return
        for record in records:
            try:
                self._on_record(record)
            except Exception:
                # No exception details: a sink might include credentials or
                # telemetry in its diagnostics. The caller checks coverage.
                self.coverage["usage_callback_failures"] += 1

    def start(self):
        if self._server is not None:
            raise RuntimeError("Proxy is already started")
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(owner._timeout)

            def _reply(self, status, body=b"{}", content_type="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_POST(self):
                expected_host = "127.0.0.1:%d" % self.server.server_port
                if self.path != _LOCAL_PATH or self.headers.get("Host") != expected_host:
                    self._reply(404)
                    return
                tokens = self.headers.get_all(_TOKEN_HEADER, [])
                if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode(), owner._token.encode()):
                    self._reply(401)
                    return
                lengths = self.headers.get_all("Content-Length", [])
                if (self.headers.get("Transfer-Encoding") or len(lengths) != 1
                        or len(lengths[0]) > 12 or not re.fullmatch(r"[0-9]+", lengths[0])):
                    self._reply(411)
                    return
                length = int(lengths[0])
                if length > owner._max_body_bytes:
                    owner.coverage["request_body_too_large"] += 1
                    self._reply(413)
                    return
                try:
                    body = self.rfile.read(length)
                    if len(body) != length:
                        raise ValueError("Incomplete body")
                except (TimeoutError, OSError, ValueError):
                    self._reply(400)
                    return
                content_type = self.headers.get("Content-Type", "application/json")
                encoding = self.headers.get("Content-Encoding", "").lower().strip()
                try:
                    status, response_body, response_type = owner._forward(body, content_type, encoding)
                except Exception:
                    owner.coverage["upstream_failures"] += 1
                    self._reply(502)
                    return
                if 200 <= status < 300:
                    owner.coverage["forwarded_batches"] += 1
                    owner._observe(body, content_type, encoding)
                else:
                    owner.coverage["upstream_rejected_batches"] += 1
                self._reply(status, response_body, response_type)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        kwargs={"poll_interval": 0.05}, daemon=True)
        self._thread.start()
        return self

    def close(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join()
            self._server = None
            self._thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()
