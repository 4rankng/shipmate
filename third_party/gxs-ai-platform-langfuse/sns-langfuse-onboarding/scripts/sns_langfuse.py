#!/usr/bin/env python3
"""Opt-in SNS tracing setup. Never prints keys or sources executable env files."""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

from codex_config import ensure_profile, codex_command
from usage_runtime import run_with_usage

BASE_URL = "https://langfuse.stg.dakota.com.sg"
CLI_VERSION = "1.2.4"
ALLOWED_KEYS = {
    "LANGFUSE_BASE_URL", "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY", "LANGFUSE_TRACING_ENVIRONMENT", "SNS_DEVELOPER_ID",
}
TEMPLATE = '''# Local SNS project credentials; never commit this file.
LANGFUSE_BASE_URL="https://langfuse.stg.dakota.com.sg"
LANGFUSE_HOST="https://langfuse.stg.dakota.com.sg"
LANGFUSE_PUBLIC_KEY=""
LANGFUSE_SECRET_KEY=""
LANGFUSE_TRACING_ENVIRONMENT="development"
# Optional stable professional identifier; defaults to your OS username.
SNS_DEVELOPER_ID=""
'''


def config_path():
    return Path.home() / ".config/langfuse/sns.env"


def codex_config_directory(home):
    """Match the configuration directory used by the launched Codex process."""
    configured = os.environ.get("CODEX_HOME")
    return Path(configured) if configured else home / ".codex"


def initialize(home, config_dir=None):
    path = home / ".config/langfuse/sns.env"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print("Preserved existing key file:", path)
    else:
        with os.fdopen(fd, "w") as output:
            output.write(TEMPLATE)
        print("Created private key template:", path)
    print("Ready profile:", ensure_profile(home, full_content=False, config_dir=config_dir))
    return path


def load_settings(path, require_keys=True):
    """Parse a small dotenv subset as data: no shell expansion or execution."""
    if not path.is_file():
        raise ValueError("Run init first, then fill the private sns.env file.")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("The key file must be private: chmod 600 <path-to-sns.env>.")
    values = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or key not in ALLOWED_KEYS:
            raise ValueError("Unsupported setting on line %d; no values were displayed." % number)
        try:
            pieces = shlex.split(value, comments=True, posix=True)
        except ValueError:
            raise ValueError("Invalid quoting on line %d." % number) from None
        if len(pieces) > 1 or key in values:
            raise ValueError("Invalid or duplicate setting on line %d." % number)
        values[key] = pieces[0] if pieces else ""
    for key in ("LANGFUSE_BASE_URL", "LANGFUSE_HOST"):
        if values.get(key, BASE_URL).rstrip("/") != BASE_URL:
            raise ValueError("This SNS setup only sends credentials to the configured staging host.")
        values[key] = BASE_URL
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        value = values.get(key, "")
        if require_keys and (not value or "placeholder" in value or value.endswith("...")):
            raise ValueError("Fill both project key fields in the private sns.env file first.")
        if any(c.isspace() for c in value):
            raise ValueError("A project key contains whitespace; correct it locally.")
    env_name = values.setdefault("LANGFUSE_TRACING_ENVIRONMENT", "development")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", env_name):
        raise ValueError("Use a simple lowercase tracing environment name.")
    return values


def basic_authorization(settings):
    pair = settings["LANGFUSE_PUBLIC_KEY"] + ":" + settings["LANGFUSE_SECRET_KEY"]
    return "Basic " + base64.b64encode(pair.encode()).decode()


def runtime_env(settings, agent, full_content, run_id, jira_key="", inherited=None):
    if full_content:
        raise ValueError("SNS tracking is metadata-only; full-content capture is disabled.")
    env = dict(os.environ if inherited is None else inherited)
    # The file is the only credential source for this launcher. Scoped Codex
    # variables override generic Langfuse variables, so set both deliberately.
    for key in ALLOWED_KEYS - {"SNS_DEVELOPER_ID"}:
        if key in settings:
            env[key] = settings[key]
    developer = settings.get("SNS_DEVELOPER_ID") or getpass.getuser()
    metadata = {"team": "SNS", "agent": agent, "run_id": run_id}
    if jira_key:
        metadata["jira_key"] = jira_key
    auth = basic_authorization(settings)
    if agent == "codex":
        # Codex 0.153 copies configured header strings literally; ${VAR} in
        # TOML is not interpolated. Its Rust OTLP SDK supports signal-specific
        # environment headers, which keep credentials out of profiles/argv.
        env.pop("SNS_LANGFUSE_AUTHORIZATION", None)
        if not full_content:
            endpoint = BASE_URL + "/api/public/otel"
            for key, expected in (("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint),
                                  ("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", endpoint + "/v1/traces")):
                if env.get(key) and env[key].rstrip("/") != expected:
                    raise ValueError("An existing OTel destination is active. Use a clean shell so its routing is preserved.")
            env["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = endpoint + "/v1/traces"
            env["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = (
                "Authorization=" + urllib.parse.quote(auth, safe="")
                + ",x-langfuse-ingestion-version=4"
            )
        env["TRACE_TO_LANGFUSE"] = "true" if full_content else "false"
        env["LANGFUSE_CODEX_PUBLIC_KEY"] = settings["LANGFUSE_PUBLIC_KEY"]
        env["LANGFUSE_CODEX_SECRET_KEY"] = settings["LANGFUSE_SECRET_KEY"]
        env["LANGFUSE_CODEX_BASE_URL"] = BASE_URL
        env["LANGFUSE_CODEX_ENVIRONMENT"] = settings["LANGFUSE_TRACING_ENVIRONMENT"]
        env["LANGFUSE_CODEX_USER_ID"] = developer
        env["LANGFUSE_CODEX_TAGS"] = json.dumps(["team:sns", "agent:codex", "pilot"])
        env["LANGFUSE_CODEX_METADATA"] = json.dumps(metadata)
        env["LANGFUSE_CODEX_DEBUG"] = "false"
        env["LANGFUSE_CODEX_FAIL_ON_ERROR"] = "false"
        env.pop("LANGFUSE_CODEX_TRACE_SEED", None)
    else:
        endpoint = BASE_URL + "/api/public/otel"
        for key in ("COPILOT_OTEL_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT"):
            if env.get(key) and env[key].rstrip("/") != endpoint:
                raise ValueError("An existing OTel destination is active. Use a clean shell so its routing is preserved.")
        traces_endpoint = env.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if traces_endpoint and traces_endpoint.rstrip("/") != endpoint + "/v1/traces":
            raise ValueError("An existing OTel destination is active. Use a clean shell so its routing is preserved.")
        # Native Copilot exports spans; Langfuse does not retain OTel logs/metrics.
        headers = "Authorization=" + auth + ",x-langfuse-ingestion-version=4"
        env.update({
            "COPILOT_OTEL_ENABLED": "true",
            "COPILOT_OTEL_ENDPOINT": endpoint,
            "OTEL_EXPORTER_OTLP_ENDPOINT": endpoint,
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": endpoint + "/v1/traces",
            "OTEL_EXPORTER_OTLP_HEADERS": headers,
            "OTEL_EXPORTER_OTLP_TRACES_HEADERS": headers,
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "COPILOT_OTEL_PROTOCOL": "http",
            "COPILOT_OTEL_CAPTURE_CONTENT": str(full_content).lower(),
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": str(full_content).lower(),
            "OTEL_SERVICE_NAME": "sns-copilot",
        })
        attributes = ["sns.team=SNS", "sns.run_id=" + run_id,
                      "sns.developer_id=" + urllib.parse.quote(developer, safe=""),
                      "deployment.environment.name=" + settings["LANGFUSE_TRACING_ENVIRONMENT"]]
        if jira_key:
            attributes.append("sns.jira_key=" + jira_key)
        previous = env.get("OTEL_RESOURCE_ATTRIBUTES", "")
        env["OTEL_RESOURCE_ATTRIBUTES"] = ",".join(([previous] if previous else []) + attributes)
    return env, developer


def langfuse_cli(settings, resource, action, extra=(), body=None):
    env = dict(os.environ)
    env.update({key: value for key, value in settings.items() if key.startswith("LANGFUSE_")})
    command = ["npx", "--yes", "langfuse-cli@" + CLI_VERSION,
               "api", resource, action, *extra, "--json"]
    if body is not None:
        command.extend(["--body-file", "-"])
    result = subprocess.run(command, env=env, input=json.dumps(body) if body is not None else None,
                            text=True, capture_output=True, timeout=60)
    if result.returncode:
        # CLI stderr can include HTTP request diagnostics. Keep it out of
        # terminal/transcripts; only report the process status.
        raise ValueError("Langfuse API check failed (CLI exit %d). Check VPN, project keys, scopes and expiry." % result.returncode)
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise ValueError("Langfuse CLI returned an unexpected response; no raw response was displayed.") from None


def find_records(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("data", "body", "result", "response"):
            if key in value:
                records = find_records(value[key])
                if records is not None:
                    return records
    return None


def check_connection(settings):
    data = langfuse_cli(settings, "projects", "list")
    projects = find_records(data)
    if projects is None or not projects:
        raise ValueError("The API returned no accessible project; verify a project API key pair.")
    safe = [{"id": p.get("id"), "name": p.get("name")} for p in projects]
    print(json.dumps({"authenticated": True, "projects": safe}, indent=2))
    return projects


def smoke_test(settings):
    """Send a labeled transport-only span, then verify persisted readback."""
    projects = check_connection(settings)
    trace_id, span_id = uuid.uuid4().hex, uuid.uuid4().hex[:16]
    session_id = "sns-onboarding-" + uuid.uuid4().hex
    started = time.time_ns()
    values = {
        "langfuse.observation.type": "span",
        "langfuse.trace.name": "verify-sns-telemetry",
        "langfuse.session.id": session_id,
        "langfuse.environment": settings["LANGFUSE_TRACING_ENVIRONMENT"],
        "langfuse.observation.metadata.team": "SNS",
        "langfuse.observation.metadata.test_kind": "transport-smoke",
    }
    span = {"traceId": trace_id, "spanId": span_id, "name": "verify-sns-telemetry",
            "kind": 1, "startTimeUnixNano": str(started), "endTimeUnixNano": str(time.time_ns()),
            "attributes": [{"key": k, "value": {"stringValue": v}} for k, v in values.items()],
            "status": {"code": 1}}
    payload = {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "sns-onboarding-check"}}]},
                                  "scopeSpans": [{"scope": {"name": "sns-onboarding"}, "spans": [span]}]}]}

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    request = urllib.request.Request(BASE_URL + "/api/public/otel/v1/traces",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json",
        "Authorization": basic_authorization(settings), "x-langfuse-ingestion-version": "4"}, method="POST")
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            receipt = json.load(response)
    except urllib.error.HTTPError as error:
        raise ValueError("OTLP smoke ingestion returned HTTP %d." % error.code) from None
    except (OSError, ValueError):
        raise ValueError("OTLP smoke ingestion did not return a valid receipt.") from None
    if receipt.get("partialSuccess", {}).get("rejectedSpans") not in (None, 0, "0"):
        raise ValueError("OTLP ingestion rejected the smoke span.")
    for attempt in range(6):
        records = find_records(langfuse_cli(settings, "observations", "list",
            ["--trace-id", trace_id, "--limit", "10", "--fields", "core,basic,metadata,io"])) or []
        matching = [r for r in records if r.get("id") == span_id and r.get("traceId") == trace_id]
        if matching:
            actual = matching[0]
            if actual.get("name") != "verify-sns-telemetry" or actual.get("sessionId") != session_id:
                raise ValueError("Smoke span persisted but expected name/session mapping failed.")
            print(json.dumps({"persisted": True, "trace_id": trace_id, "session_id": session_id,
                "type": actual.get("type"), "environment": actual.get("environment"),
                "trace_url": BASE_URL + "/project/" + projects[0]["id"] + "/traces/" + trace_id,
                "scope": "transport verification only; no model invocation or coding-agent session"}, indent=2))
            return
        time.sleep(2 + attempt)
    raise ValueError("Smoke ingestion acknowledged but readback is pending; trace ID " + trace_id)


def doctor(path):
    for binary in ("python3", "node", "npx", "codex", "copilot", "code"):
        print(binary + ":", "available" if shutil.which(binary) else "not on PATH")
    print("Key file:", path)
    print("Destination:", BASE_URL)
    try:
        settings = load_settings(path)
    except ValueError as exc:
        print("Configuration:", str(exc))
        return 1
    print("Configuration: key fields present; authenticated readback has not been run.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=config_path())
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("init", help="Create private key template and opt-in Codex profiles")
    sub.add_parser("doctor", help="Check local prerequisites without sending credentials")
    sub.add_parser("check", help="Read the Langfuse project using the configured key pair")
    sub.add_parser("smoke", help="Send one labeled non-LLM span and verify stored readback")
    run = sub.add_parser("run", help="Launch one opted-in coding-agent process")
    run.add_argument("agent", choices=["codex", "copilot", "vscode"])
    run.add_argument("--full-content", action="store_true", help="Unsupported: SNS tracking is metadata-only")
    run.add_argument("--jira", default="")
    run.add_argument("--run-id", default="")
    run.add_argument("--agent-args", nargs=argparse.REMAINDER, default=[], help="Pass remaining arguments to the agent")
    args = parser.parse_args(argv)
    if args.operation == "run" and args.full_content:
        raise ValueError("SNS tracking is metadata-only; full-content capture is disabled.")
    if args.operation == "init":
        initialize(Path.home(), config_dir=codex_config_directory(Path.home()))
        return 0
    if args.operation == "doctor":
        return doctor(args.env_file)
    settings = load_settings(args.env_file)
    if args.operation == "check":
        check_connection(settings)
        return 0
    if args.operation == "smoke":
        smoke_test(settings)
        return 0
    if args.jira and not re.fullmatch(r"(?:RGWEALTH|RGPAYM|RGCARDS)-[1-9][0-9]*", args.jira):
        raise ValueError("Use an SNS Jira key: RGWEALTH-, RGPAYM-, or RGCARDS- followed by its number.")
    run_id = args.run_id or str(uuid.uuid4())
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", run_id):
        raise ValueError("Use a simple run ID without spaces or separators.")
    env, developer = runtime_env(settings, args.agent, args.full_content, run_id, args.jira)
    if args.agent == "codex":
        ensure_profile(Path.home(), full_content=args.full_content,
                       config_dir=codex_config_directory(Path.home()))
        command = codex_command(args.agent_args, full_content=args.full_content,
                                run_id=run_id, developer_id=developer, jira_key=args.jira,
                                tracing_environment=settings["LANGFUSE_TRACING_ENVIRONMENT"])
    else:
        command = ["code" if args.agent == "vscode" else "copilot", *args.agent_args]
        if args.agent == "vscode":
            print("Fully quit VS Code first; an already-running GUI process may not inherit these settings.")
    if not shutil.which(command[0]):
        raise ValueError("Required agent command is not on PATH: " + command[0])
    print("Tracing opted in for this process. Run ID:", run_id, flush=True)
    if args.full_content:
        print("Content mode sends prompts/tool data. Codex plugin has no automatic masking; start a new, non-forked task.", flush=True)
    return run_with_usage(command, env, args.agent, args.full_content, run_id,
                          settings, developer, basic_authorization(settings), langfuse_cli)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, subprocess.TimeoutExpired) as exc:
        print("SNS Langfuse:", str(exc) if isinstance(exc, ValueError) else "API verification timed out.", file=sys.stderr)
        raise SystemExit(2)
