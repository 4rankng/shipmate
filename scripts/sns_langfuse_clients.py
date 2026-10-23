#!/usr/bin/env python3
"""Opt-in SNS metadata-only OMP/OpenCode adapters. No historical session reads."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from sns_langfuse_codex import OnboardingError, read_keys


def private_write(path, content):
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise OnboardingError("Refusing a symlinked SNS installation path.")
    if path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()):
        raise OnboardingError("SNS installation files must be owned by you.")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".sns-install-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.chmod(temporary, 0o700)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(home):
    home = home.resolve()
    source = Path(__file__).resolve().parent
    target = home / ".local/share/sns-langfuse/clients"
    files = {name: (source / name).read_text() for name in
             ("sns_langfuse_clients.py", "sns_langfuse_codex.py")}
    for name in ("metadata.mjs", "omp.mjs", "opencode.mjs", "omp-config.yml"):
        files["sns-clients/" + name] = (source / "sns-clients" / name).read_text()
    files["sns-clients/omp.ts"] = "export { default } from './omp.mjs';\n"
    files["sns-clients/opencode/index.ts"] = "export { default } from '../opencode.mjs';\n"
    for name, contents in files.items():
        private_write(target / name, contents)
    for client in ("omp", "opencode"):
        wrapper = "#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(
            str(target / "sns_langfuse_clients.py")) + " --client " + client + ' "$@"\n'
        private_write(home / (".local/bin/sns-" + client), wrapper)
    return target


def child_env(client, user, inherited, root=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,199}", user):
        raise OnboardingError("Use a username or email as --user-id (maximum 200 characters).")
    if any(k.startswith("OTEL_EXPORTER_") for k in inherited) or inherited.get("TRACE_TO_LANGFUSE", "false").lower() != "false":
        raise OnboardingError("Existing telemetry found; review its destinations first. Nothing was changed.")
    env = dict(inherited)
    # Only identity/opt-in markers enter the child environment, not project keys.
    env.update(SNS_LANGFUSE_CLIENT=client, SNS_LANGFUSE_USER_ID=user,
               OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="false")
    if client == "opencode":
        env["SNS_LANGFUSE_STARTED_AT_MS"] = str(time.time_ns() // 1000000)
        try:
            config = json.loads(inherited.get("OPENCODE_CONFIG_CONTENT", "{}"))
            plugins = config.get("plugins", [])
            if not isinstance(config, dict) or not isinstance(plugins, list):
                raise ValueError()
        except (ValueError, AttributeError):
            raise OnboardingError("Existing OpenCode inline config cannot be safely extended.") from None
        plugin = str((root or Path(__file__).resolve().parent) / "sns-clients/opencode")
        config["plugins"] = [*plugins, plugin] if plugin not in plugins else plugins
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
    return env


def client_command(client, binary, arguments, root):
    forbidden = {"--continue", "-c", "--resume", "-r", "--restore", "--session", "-s", "--fork",
                 "--server", "--from-claude", "--from-codex", "--export", "--full-content"}
    if any(arg.split("=", 1)[0] in forbidden for arg in arguments):
        raise OnboardingError("SNS adapters start fresh local sessions; resume/import/server flags are not supported.")
    if client == "omp":
        return [binary, "--config", str(root / "sns-clients/omp-config.yml"),
                "--extension", str(root / "sns-clients/omp.ts"), *arguments]
    if arguments and arguments[0] == "run":
        return [binary, "run", "--standalone", *arguments[1:]]
    if arguments and arguments[0] not in ("run",) and arguments[0].startswith("-"):
        return [binary, "--standalone", *arguments]
    if arguments:
        raise OnboardingError("Use sns-opencode for interactive work, or -- run <prompt> for a fresh CLI test.")
    return [binary, "--standalone"]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    split = argv.index("--") if "--" in argv else len(argv)
    own, arguments = argv[:split], argv[split + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("omp", "opencode"))
    parser.add_argument("--user-id", default=getpass.getuser())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--install", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(own)
    try:
        home = Path.home()
        if args.install:
            install(home)
            print("Installed sns-omp and sns-opencode. Capture starts only through these launchers.")
            return 0
        if not args.client:
            parser.error("--client is required unless installing")
        read_keys(home / ".config/langfuse/sns.env")
        env = child_env(args.client, args.user_id, os.environ)
        binary = shutil.which(args.client)
        if not binary:
            raise OnboardingError("Requested client is not installed.")
        root = Path(__file__).resolve().parent
        command = client_command(args.client, binary, arguments, root)
        help_text = subprocess.run([binary, "--help"], capture_output=True, text=True, check=True, timeout=15).stdout
        if ("--extension" if args.client == "omp" else "--standalone") not in help_text:
            raise OnboardingError("Client does not advertise the required adapter interface.")
        required = [root / "sns-clients/metadata.mjs", root / ("sns-clients/" + args.client + ".mjs"),
                    root / ("sns-clients/omp.ts" if args.client == "omp" else "sns-clients/opencode/index.ts")]
        if any(not path.is_file() or path.is_symlink() for path in required):
            raise OnboardingError("Install this bundle before launching.")
        if args.check:
            print("Local setup ready; fresh trace and userId readback still required. No session was started.")
            return 0
        print("SNS metadata-only adapter active; verify fresh trace ingestion separately.", flush=True)
        return subprocess.run(command, env=env).returncode
    except OnboardingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.SubprocessError):
        print("SNS setup/launch failed; credentials and client configuration were not printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
