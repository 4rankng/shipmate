import base64
import contextlib
import io
import os
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch

import sns_langfuse_codex as sns


class NativeOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.cwd = self.root / "project"
        self.cwd.mkdir()
        self.keys = {"LANGFUSE_BASE_URL": sns.BASE_URL, "LANGFUSE_HOST": sns.BASE_URL,
                     "LANGFUSE_PUBLIC_KEY": "pk-lf-test-only", "LANGFUSE_SECRET_KEY": "sk-lf-test-only",
                     "LANGFUSE_TRACING_ENVIRONMENT": "development"}
        self.path = self.root / "sns.env"
        self.path.write_text("\n".join(k + "=" + v for k, v in self.keys.items()))
        self.path.chmod(0o600)
        (self.home / (sns.PROFILE + ".config.toml")).write_text(sns.PROFILE_CONTENT)

    def test_private_file_is_read_as_data_without_execution(self):
        self.assertEqual(sns.read_keys(self.path), self.keys)
        text = self.path.read_text().replace("sk-lf-test-only", "sk-lf-$(false)")
        self.path.write_text(text)
        self.assertEqual(sns.read_keys(self.path)["LANGFUSE_SECRET_KEY"], "sk-lf-$(false)")

    def test_world_readable_and_symlink_credentials_are_rejected(self):
        self.path.chmod(0o644)
        with self.assertRaises(sns.OnboardingError):
            sns.read_keys(self.path)
        self.path.chmod(0o600)
        link = self.root / "link.env"
        link.symlink_to(self.path)
        with self.assertRaises(sns.OnboardingError):
            sns.read_keys(link)

    def test_blank_duplicate_and_wrong_destination_are_rejected_without_values(self):
        for text in ("LANGFUSE_SECRET_KEY=", self.path.read_text() + "\nLANGFUSE_SECRET_KEY=private-marker",
                     self.path.read_text().replace(sns.BASE_URL, "https://other.invalid")):
            self.path.write_text(text)
            with self.assertRaises(sns.OnboardingError) as result:
                sns.read_keys(self.path)
            self.assertNotIn("private-marker", str(result.exception))

    def test_auth_is_process_only_and_parent_environment_is_preserved(self):
        original = {"PATH": "/example", "OTEL_RESOURCE_ATTRIBUTES": "existing=true"}
        env = sns.make_env(self.keys, original)
        encoded = base64.b64encode(b"pk-lf-test-only:sk-lf-test-only").decode()
        self.assertIn(encoded, env["OTEL_EXPORTER_OTLP_TRACES_HEADERS"])
        self.assertIn("x-langfuse-ingestion-version=4", env["OTEL_EXPORTER_OTLP_TRACES_HEADERS"])
        self.assertEqual(env["TRACE_TO_LANGFUSE"], "false")
        self.assertEqual(original, {"PATH": "/example", "OTEL_RESOURCE_ATTRIBUTES": "existing=true"})
        self.assertNotIn("LANGFUSE_SECRET_KEY", env)

    def test_skill_opt_in_is_set_only_when_launching_not_during_checks(self):
        # Keep the launch-scoped opt-in distinct from reusable credentials/config checks.
        env = sns.make_env(self.keys, {})
        self.assertNotIn('SNS_LANGFUSE_CLIENT', env)
        self.assertNotIn('SNS_LANGFUSE_USER_ID', env)

    def test_existing_exporters_are_not_replaced(self):
        for existing in ({"OTEL_EXPORTER_OTLP_ENDPOINT": "https://other.invalid"},
                         {"OTEL_EXPORTER_OTLP_TRACES_HEADERS": "private-marker"},
                         {"TRACE_TO_LANGFUSE": "true"}):
            with self.assertRaises(sns.OnboardingError) as result:
                sns.make_env(self.keys, existing)
            self.assertNotIn("private-marker", str(result.exception))

    def test_profile_contains_no_secrets_or_transcript_opt_in(self):
        self.assertIn("log_user_prompt = false", sns.PROFILE_CONTENT)
        self.assertIn('enabled = false', sns.PROFILE_CONTENT)
        self.assertNotIn("Authorization", sns.PROFILE_CONTENT)
        self.assertIn('OTEL_EXPORTER_OTLP_TRACES_HEADERS = ""', sns.PROFILE_CONTENT)
        self.assertNotIn("hooks =", sns.PROFILE_CONTENT)
        self.assertNotIn("sk-lf-", sns.PROFILE_CONTENT)
        sns.check_settings(self.home, self.cwd)

    def test_existing_user_project_and_parent_otel_settings_are_preserved(self):
        for path in (self.home / "config.toml", self.cwd / ".codex/config.toml",
                     self.root / ".codex/config.toml"):
            path.parent.mkdir(exist_ok=True)
            existing = '[otel]\ntrace_exporter = "none"\n'
            path.write_text(existing)
            with self.assertRaises(sns.OnboardingError):
                sns.check_settings(self.home, self.cwd)
            self.assertEqual(path.read_text(), existing)
            path.unlink()

    def test_quoted_and_inline_otel_tables_are_not_overridden(self):
        path = self.home / "config.toml"
        for text in ('["otel"]\nexporter="none"', "['otel'.trace_exporter]\nendpoint='other'",
                     'otel = { trace_exporter = "none" }', 'otel.trace_exporter = "none"'):
            path.write_text(text)
            with self.assertRaises(sns.OnboardingError):
                sns.check_settings(self.home, self.cwd)
            self.assertEqual(path.read_text(), text)
        path.unlink()

    def test_modified_profile_and_existing_langfuse_are_not_overwritten(self):
        p = self.home / (sns.PROFILE + ".config.toml")
        p.write_text("private-marker")
        with self.assertRaises(sns.OnboardingError):
            sns.check_settings(self.home, self.cwd)
        self.assertEqual(p.read_text(), "private-marker")
        p.write_text(sns.PROFILE_CONTENT)
        (self.home / "langfuse.json").write_text('{"enabled":true}')
        with self.assertRaises(sns.OnboardingError):
            sns.check_settings(self.home, self.cwd)

    def test_resume_and_hook_bypass_flags_are_not_accepted(self):
        for argv in (["run", "resume"], ["run", "--dangerously-bypass-hook-trust"], ["desktop"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                sns.main(argv)

    def test_errors_do_not_print_private_file_contents(self):
        output = io.StringIO()
        with patch.object(sns, "read_keys", side_effect=ValueError("private-marker")), \
                contextlib.redirect_stdout(output):
            self.assertEqual(sns.main(["check"]), 1)
        self.assertNotIn("private-marker", output.getvalue())

    def test_check_does_not_claim_trace_ingestion_or_launch_a_session(self):
        with patch.object(sns, "read_keys", return_value=self.keys), \
                patch.object(sns, "check_settings"), patch.object(sns.shutil, "which", return_value="codex"), \
                patch.object(sns.subprocess, "run") as run, patch.dict(os.environ, {}, clear=True), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            run.return_value.stdout = "Layer $CODEX_HOME/<name>.config.toml"
            self.assertEqual(sns.main(["check"]), 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], "--help")
        self.assertIn("still needs verification", output.getvalue())

    def test_test_uses_fresh_directory_read_only_and_no_resume(self):
        with patch.object(sns, "read_keys", return_value=self.keys), \
                patch.object(sns, "check_settings"), patch.object(sns.shutil, "which", return_value="codex"), \
                patch.object(sns.subprocess, "run") as run, patch.dict(os.environ, {}, clear=True):
            run.return_value.stdout = "Layer $CODEX_HOME/<name>.config.toml"
            run.return_value.returncode = 0
            self.assertEqual(sns.main(["test"]), 0)
        args, kwargs = run.call_args
        self.assertIn("read-only", args[0])
        self.assertNotIn("resume", args[0])
        self.assertNotEqual(kwargs["cwd"], str(Path.cwd()))
        self.assertEqual(kwargs["stdin"], sns.subprocess.DEVNULL)
        self.assertEqual(kwargs['env']['SNS_LANGFUSE_CLIENT'], 'codex')
        self.assertTrue(kwargs['env']['SNS_LANGFUSE_USER_ID'])

    def test_native_identity_is_sent_without_content_capture(self):
        command = sns.native_command("codex", "frank.nguyen")
        self.assertIn('"langfuse.user.id"="frank.nguyen"', command[-1])
        attributes = sns.tomllib.loads(command[-1])["otel"]["span_attributes"]
        self.assertEqual(attributes["langfuse.environment"], "development")
        self.assertEqual(attributes["langfuse.user.id"], "frank.nguyen")
        self.assertNotIn("log_user_prompt=true", " ".join(command))
        for identity in ("", "private\nmarker", "x" * 201, 'x"=true'):
            with self.assertRaises(sns.OnboardingError):
                sns.native_command("codex", identity)

    def test_saved_ui_state_is_preserved_but_privacy_changes_are_rejected(self):
        profile = self.home / (sns.PROFILE + ".config.toml")
        saved = sns.PROFILE_CONTENT + '\n[tui]\ntheme="dark"\n[hooks.state]\ntrusted=[]\n'
        profile.write_text(saved)
        sns.check_settings(self.home, self.cwd)
        self.assertEqual(profile.read_text(), saved)
        for old, new in (("log_user_prompt = false", "log_user_prompt = true"),
                         ("enabled = false", "enabled = true"),
                         ('protocol = "json"', 'protocol = "binary"')):
            profile.write_text(saved.replace(old, new))
            with self.assertRaises(sns.OnboardingError):
                sns.check_settings(self.home, self.cwd)

    def test_installed_launcher_survives_source_removal(self):
        source = self.root / "disposable" / "helper.py"
        source.parent.mkdir()
        shutil.copyfile(sns.__file__, source)
        with patch.object(sns, "__file__", str(source)):
            launcher = sns.install_launcher(self.home)
        shutil.rmtree(source.parent)
        result = sns.subprocess.run([str(launcher), "profile"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, sns.PROFILE_CONTENT)
        self.assertNotIn("disposable", launcher.read_text())
        self.assertEqual(launcher.stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.home / ".config/langfuse/sns.env").exists())

    def test_install_rejects_symlink_without_changing_target(self):
        victim = self.root / "unrelated"
        victim.write_text("preserve")
        launcher = self.home / ".local/bin/sns-codex"
        launcher.parent.mkdir(parents=True)
        launcher.symlink_to(victim)
        with self.assertRaises(sns.OnboardingError):
            sns.install_launcher(self.home)
        self.assertEqual(victim.read_text(), "preserve")


class OnboardingProcedureTests(unittest.TestCase):
    def test_internal_only_explicit_capture_and_verified_client_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        doc = (root / "internal/sns-langfuse/PROCEDURE.md").read_text()
        for phrase in ("Use only when the engineer requests", "not desktop verification",
                       "its own fresh-session verification", "never request them in chat", "metadata-only",
                       "Never bypass hook approval", "never export existing conversations or archives",
                       "/api/public/v2/observations", "No app/deployment changes"):
            self.assertIn(phrase, doc)
        self.assertFalse((root / "skills/sns-langfuse").exists())
        self.assertFalse((root / "internal/sns-langfuse/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
