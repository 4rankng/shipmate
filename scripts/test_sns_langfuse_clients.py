import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sns_langfuse_clients as sns


class MultiClientTests(unittest.TestCase):
    def test_environment_has_identity_but_no_injected_keys_or_headers(self):
        original = {"PATH": "/example", "UNRELATED": "preserved"}
        result = sns.child_env("omp", "test.engineer", original)
        self.assertEqual(result["SNS_LANGFUSE_USER_ID"], "test.engineer")
        self.assertEqual(result["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"], "false")
        self.assertEqual(result["UNRELATED"], "preserved")
        self.assertNotIn("SNS_LANGFUSE_CLIENT", original)
        self.assertFalse(any("KEY" in k or "HEADERS" in k for k in result))

    def test_existing_exporters_are_preserved_by_declining_conflict(self):
        with self.assertRaises(sns.OnboardingError):
            sns.child_env("omp", "engineer", {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://elsewhere.invalid"})
        with self.assertRaises(sns.OnboardingError):
            sns.child_env("omp", "bad\nidentity", {})

    def test_commands_use_explicit_extension_and_standalone_server(self):
        root = Path("/installed")
        self.assertIn("--extension", sns.client_command("omp", "omp", [], root))
        self.assertEqual(sns.client_command("opencode", "opencode", [], root), ["opencode", "--standalone"])
        self.assertEqual(sns.client_command("opencode", "opencode", ["run", "hello"], root),
                         ["opencode", "run", "--standalone", "hello"])
        for flag in ("--resume=old", "--session", "--server=http://localhost:1", "--full-content", "-c"):
            with self.assertRaises(sns.OnboardingError):
                sns.client_command("omp", "omp", [flag], root)

    def test_install_preserves_other_config_and_survives_source_removal(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            source = home / "source"
            source.mkdir()
            for name in ("sns_langfuse_clients.py", "sns_langfuse_codex.py"):
                shutil.copyfile(Path(sns.__file__).parent / name, source / name)
            shutil.copytree(Path(sns.__file__).parent / "sns-clients", source / "sns-clients")
            config = home / ".config/opencode/opencode.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"model":"unchanged"}')
            with patch.object(sns, "__file__", str(source / "sns_langfuse_clients.py")):
                target = sns.install(home)
            shutil.rmtree(source)
            self.assertEqual(config.read_text(), '{"model":"unchanged"}')
            for client in ("omp", "opencode"):
                launcher = home / (".local/bin/sns-" + client)
                result = subprocess.run([str(launcher), "--help"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(launcher.stat().st_mode & 0o777, 0o700)
            self.assertTrue((target / "sns-clients/omp.ts").is_file())
            self.assertFalse((home / ".config/langfuse/sns.env").exists())

    def test_install_does_not_touch_unrelated_plugin_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            path = home / ".config/opencode/plugins/sns-langfuse.ts"
            path.parent.mkdir(parents=True)
            path.write_text("unrelated plugin")
            sns.install(home)
            self.assertEqual(path.read_text(), "unrelated plugin")
            target = home / "target"
            target.write_text("unrelated")
            wrapper = home / ".local/bin/sns-omp"
            wrapper.unlink()
            wrapper.symlink_to(target)
            with self.assertRaises(sns.OnboardingError):
                sns.install(home)
            self.assertEqual(target.read_text(), "unrelated")

    def test_opencode_inline_settings_and_plugins_are_preserved(self):
        import json
        original = {"OPENCODE_CONFIG_CONTENT": '{"model":"unchanged","plugins":["existing-plugin"]}'}
        result = sns.child_env("opencode", "engineer", original, Path("/installed"))
        config = json.loads(result["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(config["model"], "unchanged")
        self.assertEqual(config["plugins"], ["existing-plugin", "/installed/sns-clients/opencode"])
        self.assertNotIn("sns-clients", original["OPENCODE_CONFIG_CONTENT"])

    @unittest.skipUnless(os.environ.get("SNS_TEST_CLIENT_HOOKS") == "1", "opt-in local client hook check")
    def test_installed_client_hooks_without_model_calls_or_network_export(self):
        """Real client loading, fake reporter. No SNS credentials are read."""
        import json
        root = Path(sns.__file__).parent / "sns-clients"
        for client in ("omp", "opencode"):
            binary = shutil.which(client)
            if not binary:
                self.fail("Client hook check requested but client is not installed")
            with tempfile.TemporaryDirectory(prefix="sns-hooks-") as temporary:
                directory = Path(temporary).resolve()
                output = directory / "events.jsonl"
                shim = directory / "probe.ts"
                shim.write_text("import adapter from " + json.dumps((root / (client + ".mjs")).as_uri()) + ";\n"
                    "import {appendFileSync} from 'node:fs';\n"
                    "const reporter={active:true, record:r=>appendFileSync(" + json.dumps(str(output)) +
                    ",JSON.stringify({kind:r.kind,session:r.session,start:r.start,startType:typeof r.start})+'\\n'),flush:async()=>{}};\n"
                    + ("export default {id:'sns-probe',setup:async ctx=>{appendFileSync(" + json.dumps(str(output)) +
                       ",JSON.stringify({kind:'loaded'})+'\\n');const dispose=await setupOpenCode(ctx,reporter);"
                       "await ctx.session.create({});await new Promise(r=>setTimeout(r,100));return dispose}};\n" if client == "opencode"
                       else "export default ctx=>adapter(ctx,reporter);\n"))
                if client == "opencode":
                    shim.write_text(shim.read_text().replace("import adapter from ", "import {setupOpenCode} from "))
                env = dict(os.environ)
                env.pop("SNS_LANGFUSE_CLIENT", None)
                env["XDG_CONFIG_HOME"] = str(directory / "config")
                env["OTEL_SDK_DISABLED"] = "true"
                if client == "omp":
                    command = [binary, "--mode", "rpc", "--no-session", "--no-extensions", "-e", str(shim)]
                    stdin = '{"id":"probe","type":"get_state"}\n'
                else:
                    plugins = directory / "config/opencode/plugins/sns-probe"
                    plugins.mkdir(parents=True)
                    shutil.copyfile(shim, plugins / "index.ts")
                    env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"plugins": [str(plugins)]})
                    # Invalid provider prevents any model call; session admission
                    # still activates the real plugin runtime.
                    command = [binary, "run", "--standalone", "--model", "sns-probe/no-model",
                               "--format", "json", "SNS hook loading probe"]
                    stdin = ""
                result = subprocess.run(command, cwd=directory, env=env, input=stdin,
                                        capture_output=True, text=True, timeout=45)
                # Deliberately do not echo arbitrary client stdout/stderr.
                if client == "omp":
                    self.assertEqual(result.returncode, 0, client + " hook probe failed; inspect locally")
                self.assertTrue(output.exists(), client + " did not emit session.created/session_start")
                records = [json.loads(line) for line in output.read_text().splitlines()]
                self.assertTrue(any(row.get("kind") == "session" and row.get("session") for row in records),
                                client + " plugin loaded but no fresh session event received")
                self.assertTrue(all(isinstance(row.get("start"), (float, int)) and row["start"] > 0
                                    for row in records if row.get("kind") == "session"), client + " event timestamp did not match the contract")


if __name__ == "__main__":
    unittest.main()
