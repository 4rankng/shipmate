"""Attach usage collection only to the explicitly launched CLI process."""
from datetime import datetime, timezone
import json
import subprocess
import sys
import time

from codex_usage import extract_codex_usage
from usage_sink import UsageSink


INCOMPLETE_COPILOT_COVERAGE = (
    "unsupported_payload", "conflicting_session_identity", "trace_identity_evicted",
    "skill_events_missing_identity", "usage_capacity_exceeded", "unsupported_content_type",
    "unsupported_content_encoding", "decoded_body_too_large", "invalid_json_or_gzip",
    "usage_callback_failures", "request_body_too_large", "upstream_failures",
    "upstream_rejected_batches",
)


def collect_codex(settings, run_id, started_at, api, attempts=4):
    filters = [
        {"column": "metadata", "type": "stringObject", "key": "run_id", "operator": "=", "value": run_id},
        {"column": "startTime", "type": "datetime", "operator": ">=", "value": started_at},
        {"column": "type", "type": "stringOptions", "operator": "any of", "value": ["AGENT", "TOOL"]},
    ]
    for attempt in range(attempts):
        rows, cursor, seen = [], None, set()
        for _ in range(100):
            args = ["--filter", json.dumps(filters), "--fields", "basic,metadata,trace_context,io", "--limit", "1000"]
            if cursor:
                args.extend(["--cursor", cursor])
            result = api(settings, "observations", "list", extra=args)
            body = result.get("body", result)
            if not isinstance(body, dict) or not isinstance(body.get("data"), list):
                raise ValueError("Session usage could not read the current Codex run.")
            rows.extend(body["data"])
            cursor = body.get("meta", {}).get("cursor")
            if not cursor:
                break
            if cursor in seen:
                raise ValueError("Session usage pagination did not complete.")
            seen.add(cursor)
        else:
            raise ValueError("Session usage exceeded the bounded observation limit.")
        roots = [row for row in rows if row.get("type") == "AGENT" and row.get("name") == "Codex Turn"]
        if roots:
            return extract_codex_usage(rows)
        if attempt + 1 < attempts:
            time.sleep(3)
    raise ValueError("Codex full-content observations are not available yet; usage coverage is unknown for this run.")


def local_copilot_env(env, proxy):
    local = dict(env)
    header = ",".join(key + "=" + value for key, value in proxy.local_headers.items())
    local.update({
        "COPILOT_OTEL_ENDPOINT": proxy.base_url,
        "OTEL_EXPORTER_OTLP_ENDPOINT": proxy.base_url,
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": proxy.trace_url,
        "OTEL_EXPORTER_OTLP_HEADERS": header,
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS": header,
        "COPILOT_OTEL_PROTOCOL": "http/json",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/json",
        "COPILOT_OTEL_EXPORTER_TYPE": "otlp-http",
    })
    local.pop("COPILOT_OTEL_FILE_EXPORTER_PATH", None)
    local.pop("COPILOT_OTEL_HEADERS", None)
    return local


def wait_process(command, env):
    process = subprocess.Popen(command, env=env)
    try:
        code = process.wait()
    except KeyboardInterrupt:
        # Child shares the foreground process group and has received Ctrl-C.
        try:
            code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                code = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
    return code if code >= 0 else 128 - code


def run_with_usage(command, env, agent, full_content, run_id, settings, developer, authorization, api):
    if agent != "copilot" and not (agent == "codex" and full_content):
        print("This mode has no established skill/plugin usage coverage; do not enable content capture to fill it.", flush=True)
        return wait_process(command, env)
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = []
    if agent == "copilot":
        from copilot_proxy import CopilotProxy
        # on_record is metadata only; raw spans continue forwarding during the session.
        with CopilotProxy(authorization, records.append) as proxy:
            code = wait_process(command, local_copilot_env(env, proxy))
        coverage = dict(proxy.coverage)
        print("SNS usage adapter:", json.dumps(coverage, sort_keys=True), flush=True)
        if not coverage.get("forwarded_batches") or any(
            coverage.get(key) for key in INCOMPLETE_COPILOT_COVERAGE
        ):
            print("SNS usage coverage is incomplete; successful records can still be published.", file=sys.stderr)
    else:
        code = wait_process(command, env)
        try:
            records = collect_codex(settings, run_id, started_at, api)
        except Exception:
            print("SNS usage coverage is unknown: current-run Codex observations could not be read. Raw tracing is separate.", file=sys.stderr)
            return code
    sink = None
    try:
        sink = UsageSink(settings, developer, authorization)
        counts = sink.publish(records)
        print("SNS skill/plugin session records:", json.dumps(counts, sort_keys=True), flush=True)
    except Exception:
        print("SNS skill/plugin session records could not be fully uploaded; usage coverage is incomplete. Agent exit status is preserved.", file=sys.stderr)
    finally:
        if sink:
            try:
                sink.close()
            except Exception:
                print("SNS usage receipt store could not close cleanly. Agent exit status is preserved.", file=sys.stderr)
    return code
