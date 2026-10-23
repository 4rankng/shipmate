#!/usr/bin/env python3
"""Opt-in native Codex CLI spans, not desktop or transcript tracking."""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import stat
import subprocess
import tempfile
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

BASE_URL = "https://langfuse.stg.dakota.com.sg"
PROFILE = "sns-langfuse-native"
PROFILE_CONTENT = '''# Opt-in CLI profile. Credentials come from the launcher's process environment.
[otel]
environment = "development"
log_user_prompt = false
trace_exporter = { otlp-http = { endpoint = "https://langfuse.stg.dakota.com.sg/api/public/otel/v1/traces", protocol = "json" } }

# This profile does not upload transcripts or change hook trust.
[plugins."tracing@codex-observability-plugin"]
enabled = false

# Keep the exporter header out of model-launched shell commands.
[shell_environment_policy.set]
OTEL_EXPORTER_OTLP_TRACES_HEADERS = ""
'''


class OnboardingError(ValueError):
    """A fixed, non-secret message suitable for the user."""


def read_keys(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise OnboardingError("Credential file must be owner-only, owned by you, and not a symlink.")
    values = {}
    allowed = {"LANGFUSE_BASE_URL", "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY",
               "LANGFUSE_SECRET_KEY", "LANGFUSE_TRACING_ENVIRONMENT"}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key not in allowed or key in values:
            raise OnboardingError("Use only the guide's five fields, without duplicates.")
        if value[:1] in ("'", '"'):
            if len(value) < 2 or value[-1] != value[0]:
                raise OnboardingError("Unmatched quotes in credential file.")
            value = value[1:-1]
        values[key] = value
    if any(values.get(key) != BASE_URL for key in ("LANGFUSE_BASE_URL", "LANGFUSE_HOST")):
        raise OnboardingError("Use the documented SNS server.")
    if values.get("LANGFUSE_TRACING_ENVIRONMENT") != "development":
        raise OnboardingError("This onboarding profile uses development.")
    for key, prefix in (("LANGFUSE_PUBLIC_KEY", "pk-lf-"), ("LANGFUSE_SECRET_KEY", "sk-lf-")):
        value = values.get(key, "")
        if not value.startswith(prefix) or len(value) <= len(prefix) or any(c.isspace() for c in value):
            raise OnboardingError("Fill both project keys locally; never paste them into chat.")
    return values


def make_env(values, inherited):
    if any(key.startswith("OTEL_EXPORTER_") for key in inherited):
        raise OnboardingError("Existing OTel exporter found; preserve and review its destinations first.")
    if inherited.get("TRACE_TO_LANGFUSE", "false").lower() != "false":
        raise OnboardingError("Existing transcript tracking found; preserve its configuration.")
    result = dict(inherited)
    encoded = base64.b64encode((values["LANGFUSE_PUBLIC_KEY"] + ":" +
                                values["LANGFUSE_SECRET_KEY"]).encode()).decode()
    result["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = (
        "Authorization=Basic " + encoded + ",x-langfuse-ingestion-version=4")
    result["TRACE_TO_LANGFUSE"] = "false"
    return result


def check_settings(codex_home, cwd):
    if tomllib is None:
        raise OnboardingError("Use Python 3.11+ or install tomli for Python 3.9/3.10.")
    profile = codex_home / (PROFILE + ".config.toml")
    try:
        actual = tomllib.loads(profile.read_text())
        expected = tomllib.loads(PROFILE_CONTENT)
    except ValueError:
        raise OnboardingError("Prepare the opt-in native profile from the procedure.") from None
    if profile.is_symlink() or any(actual.get(k) != v for k, v in expected.items()):
        raise OnboardingError("Native profile privacy/exporter settings differ; review without overwriting.")
    parents = (cwd, *cwd.parents)
    files = [codex_home / "config.toml", codex_home / "managed_config.toml",
             Path("/etc/codex/config.toml"),
             Path("/etc/codex/managed_config.toml")]
    files += [parent / ".codex/config.toml" for parent in parents]
    for path in files:
        if path.is_file():
            active = "\n".join(line for line in path.read_text().splitlines()
                               if not line.lstrip().startswith("#"))
            if re.search(r'''(?m)^\s*(?:\[\s*["']?otel["']?\s*[.\]]|["']?otel["']?\s*[.=])''', active):
                raise OnboardingError("Existing OTel settings found; preserve their destinations first.")
    if (codex_home / "langfuse.json").exists() or any(
            (parent / ".codex/langfuse.json").exists() for parent in parents):
        raise OnboardingError("Existing Langfuse settings found; review them before onboarding.")


def native_command(binary, user_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,199}", user_id):
        raise OnboardingError("Use a nonempty username or email as --user-id (maximum 200 characters).")
    # Set the whole table: dotted-key overrides are not supported by all clients.
    attributes = ('{"langfuse.user.id"=' + json.dumps(user_id) +
                  ',"langfuse.environment"="development","langfuse.trace.metadata.team"="SNS"}')
    return [binary, "--profile", PROFILE, "-c", "otel.span_attributes=" + attributes]


def install_launcher(home):
    """Keep the runnable helper outside disposable worktrees and plugin caches."""
    if tomllib is None:
        raise OnboardingError("Install using Python 3.11+ or Python with tomli.")
    home = home.resolve()
    target = home / ".local/share/sns-langfuse/sns_langfuse_codex.py"
    launcher = home / ".local/bin/sns-codex"
    for path in (target, launcher):
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise OnboardingError("Refusing a symlinked launcher installation path.")
        if path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()):
            raise OnboardingError("Launcher installation must be owned by you.")
    # Explicit install replaces only these two managed files, never keys/config.
    for path, contents in ((target, Path(__file__).read_text()), (launcher,
            '#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(target)) + ' "$@"\n')):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".sns-install-", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(contents)
            os.chmod(temporary, 0o700)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return launcher


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="run", choices=("profile", "check", "run", "test", "install"))
    parser.add_argument("--codex-bin", help="Explicit CLI executable, never a desktop app.")
    parser.add_argument("--user-id", default=getpass.getuser(), help="Langfuse user identity; defaults to OS username.")
    args = parser.parse_args(argv)
    if args.action == "profile":
        print(PROFILE_CONTENT, end="")
        return 0
    try:
        home, cwd = Path.home(), Path.cwd().resolve()
        if args.action == "install":
            print("Installed stable metadata-only launcher:", install_launcher(home))
            return 0
        codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).resolve()
        keys = read_keys(home / ".config/langfuse/sns.env")
        env = make_env(keys, os.environ)
        check_settings(codex_home, cwd)
        bundled = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
        binary = args.codex_bin or (str(bundled) if bundled.is_file() else shutil.which("codex"))
        if not binary:
            raise OnboardingError("Codex CLI is not installed.")
        help_text = subprocess.run([binary, "--help"], capture_output=True, text=True, check=True)
        if "<name>.config.toml" not in help_text.stdout:
            raise OnboardingError("This CLI does not document separate profile-file support.")
        if args.action == "check":
            print("Private CLI setup is ready; actual trace ingestion still needs verification.")
            return 0
        command = native_command(binary, args.user_id)
        # A process-local opt-in for L3 entry reporting; no credentials in agent shells.
        env['SNS_LANGFUSE_CLIENT'] = 'codex'
        env['SNS_LANGFUSE_USER_ID'] = args.user_id
        if args.action == "test":
            command += ["exec", "--skip-git-repo-check", "--sandbox", "read-only", "--json",
                        "Reply exactly: SNS native tracing test OK. Do not use tools or read files."]
            with tempfile.TemporaryDirectory(prefix="sns-codex-fresh-") as fresh:
                return subprocess.run(command, cwd=fresh, env=env, stdin=subprocess.DEVNULL).returncode
        # No passthrough flags: cannot resume/fork old sessions or bypass hook trust.
        return subprocess.run(command, env=env).returncode
    except OnboardingError as error:
        print(str(error))
        return 1
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Could not read private setup or launch the CLI; no settings were changed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
