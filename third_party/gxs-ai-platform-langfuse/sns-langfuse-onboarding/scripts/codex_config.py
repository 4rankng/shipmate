"""Opt-in Codex profiles and argument construction for SNS Langfuse.

This module does not load credentials or alter the base Codex configuration.
Content tracing uses the separately installed official Langfuse plugin and
must begin with a fresh task: its Stop hook includes earlier transcript turns.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from typing import List, Optional


NATIVE_PROFILE_NAME = "sns-langfuse"
CONTENT_PROFILE_NAME = "sns-langfuse-content"

_NATIVE_PROFILE = '''# SNS Langfuse: opt in with codex --profile sns-langfuse.
# Credentials are supplied by the launcher; never paste a key into this file.
[otel]
environment = "development"
log_user_prompt = false

[otel.trace_exporter.otlp-http]
endpoint = "https://langfuse.stg.dakota.com.sg/api/public/otel/v1/traces"
protocol = "binary"

[otel.trace_exporter.otlp-http.headers]
x-langfuse-ingestion-version = "4"

[otel.span_attributes]
"langfuse.trace.metadata.team" = "SNS"
'''

_CONTENT_PROFILE = '''# SNS Langfuse: opt in with codex --profile sns-langfuse-content.
# Start a new task. The plugin can upload earlier turns of resumed/forked tasks.
# Review and trust the installed plugin's Stop hook in /hooks before use.
[features]
hooks = true

[plugins."tracing@codex-observability-plugin"]
enabled = true
'''


def _has_only_saved_hook_state(suffix: bytes) -> bool:
    """Recognize Codex's appended state without rewriting or granting trust.

    Codex 0.153 HookStateToml contains only enabled and trusted_hash. Keep
    this deliberately narrower than a general TOML parser: only saved plugin
    hook states may follow our exact managed prefix, never hook commands or
    unrelated settings. Python 3.9 has no standard-library TOML parser.
    """
    try:
        lines = suffix.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return False
    root_seen = False
    sections = set()
    fields = None
    section_pattern = re.compile(
        r'\[hooks\.state\."([A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:'
        r'[A-Za-z0-9_./-]+:[a-z_]+:[0-9]+:[0-9]+)"\]'
    )
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not root_seen:
            if line != "[hooks.state]":
                return False
            root_seen = True
            continue
        section = section_pattern.fullmatch(line)
        if section:
            name = section.group(1)
            if name in sections:
                return False
            sections.add(name)
            fields = set()
            continue
        if fields is None:
            return False
        if re.fullmatch(r'trusted_hash\s*=\s*"sha256:[0-9a-f]{64}"', line):
            field = "trusted_hash"
        elif re.fullmatch(r"enabled\s*=\s*(true|false)", line):
            field = "enabled"
        else:
            return False
        if field in fields:
            return False
        fields.add(field)
    return root_seen


def ensure_profile(
    home: Path, full_content: bool = False, config_dir: Optional[Path] = None
) -> Path:
    """Create a private named profile without replacing an existing file.

    ``home`` is the user's home directory, not CODEX_HOME. ``config_dir`` selects
    an explicit Codex configuration directory when CODEX_HOME is set. Existing identical
    files, optionally followed by Codex's saved plugin-hook state, are accepted
    and their permissions tightened to 0600. Saved state is preserved byte for
    byte; this function never grants hook trust. Other changed content,
    directories, and symlinks raise ValueError.
    Only the selected named profile is created; config.toml is never touched.
    """
    profile_name = CONTENT_PROFILE_NAME if full_content else NATIVE_PROFILE_NAME
    contents = _CONTENT_PROFILE if full_content else _NATIVE_PROFILE
    expected = contents.encode("utf-8")
    directory = Path(config_dir) if config_dir is not None else Path(home) / ".codex"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    profile = directory / (profile_name + ".config.toml")
    no_follow = getattr(os, "O_NOFOLLOW", 0)

    try:
        descriptor = os.open(
            profile, os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow, 0o600
        )
    except FileExistsError:
        # Open the existing file without following symlinks. Use fstat/fchmod
        # so validation and permission repair refer to the same opened file.
        try:
            descriptor = os.open(profile, os.O_RDONLY | os.O_NONBLOCK | no_follow)
        except OSError as error:
            raise ValueError("Existing profile is not a regular file: %s" % profile) from error
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ValueError("Existing profile is not a regular file: %s" % profile)
        with os.fdopen(descriptor, "rb") as existing:
            # Bound the read while allowing Codex to append runtime hook
            # preferences. Do not serialize the file: that could erase or
            # inadvertently change a user's saved enablement/trust state.
            actual = existing.read(1024 * 1024 + 1)
            if (
                len(actual) > 1024 * 1024
                or not actual.startswith(expected)
                or (actual != expected and not _has_only_saved_hook_state(actual[len(expected):]))
            ):
                raise ValueError("Refusing to overwrite existing profile: %s" % profile)
            os.fchmod(existing.fileno(), 0o600)
        return profile

    with os.fdopen(descriptor, "wb") as created:
        created.write(expected)
        os.fchmod(created.fileno(), 0o600)
    return profile


def _toml_string(value: str) -> str:
    # JSON string escaping is compatible with TOML basic strings. Preserve
    # Unicode rather than producing UTF-16 surrogate escapes for non-BMP text.
    return json.dumps(value, ensure_ascii=False)


def _attribute_override(attributes: dict) -> List[str]:
    # Codex splits the override path on every dot, including dots inside
    # quoted keys. Override the whole table: TOML then parses literal dotted
    # attribute names in the value rather than in the CLI's key path.
    entries = ", ".join(
        "%s=%s" % (_toml_string(name), _toml_string(value))
        for name, value in attributes.items()
    )
    return ["-c", "otel.span_attributes={%s}" % entries]


def codex_command(
    arguments: List[str],
    *,
    full_content: bool,
    run_id: str,
    developer_id: str,
    jira_key: str = "",
    tracing_environment: str = "development",
) -> List[str]:
    """Build subprocess argv; credentials must be provided in its environment.

    Content mode conservatively refuses resume/fork options wherever they
    occur, including ``exec resume``. It cannot make resuming through an
    already-running Codex UI safe; the onboarding launcher must start fresh.
    """
    if not run_id.strip():
        raise ValueError("run_id must not be empty")
    if not developer_id.strip():
        raise ValueError("developer_id must not be empty")

    if full_content:
        prohibited_commands = {"resume", "fork"}
        prohibited_options = {"--last", "--resume", "--fork"}
        for argument in arguments:
            option = argument.split("=", 1)[0]
            if argument in prohibited_commands or option in prohibited_options:
                raise ValueError(
                    "Content tracing requires a brand-new task; resume/fork can upload history"
                )

    profile_name = CONTENT_PROFILE_NAME if full_content else NATIVE_PROFILE_NAME
    command = ["codex", "--profile", profile_name]
    if not full_content:
        command.extend(["-c", "otel.environment=" + _toml_string(tracing_environment)])
        attributes = {
            "session.id": run_id,
            "user.id": developer_id,
            "langfuse.environment": tracing_environment,
            "langfuse.trace.metadata.team": "SNS",
            "langfuse.trace.metadata.run_id": run_id,
        }
        if jira_key:
            attributes["langfuse.trace.metadata.jira_key"] = jira_key
        command.extend(_attribute_override(attributes))
    command.extend(arguments)
    return command
