"""Offline tests: profiles stay isolated and content tracing starts fresh."""

import os
from pathlib import Path
import stat
import tempfile
import unittest

from codex_config import codex_command, ensure_profile


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)

    def test_profiles_are_private_idempotent_and_leave_base_config_intact(self):
        directory = self.home / ".codex"
        directory.mkdir()
        base = directory / "config.toml"
        original = '[otel]\nexporter = "none"\nmodel = "existing"\n'
        base.write_text(original)

        native = ensure_profile(self.home)
        content = ensure_profile(self.home, full_content=True)
        self.assertEqual(native.name, "sns-langfuse.config.toml")
        self.assertEqual(content.name, "sns-langfuse-content.config.toml")
        self.assertEqual(ensure_profile(self.home), native)
        self.assertEqual(ensure_profile(self.home, True), content)
        self.assertEqual(base.read_text(), original)
        for profile in (native, content):
            self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o600)

        settings = native.read_text()
        self.assertIn("https://langfuse.stg.dakota.com.sg/api/public/otel/v1/traces", settings)
        self.assertNotIn("Authorization", settings)
        self.assertNotIn("${", settings)
        self.assertIn('x-langfuse-ingestion-version = "4"', settings)
        self.assertIn("log_user_prompt = false", settings)
        self.assertNotIn("[otel.exporter", settings)
        self.assertNotIn("metrics_exporter", settings)
        self.assertNotIn("[otel]", content.read_text())
        self.assertIn('plugins."tracing@codex-observability-plugin"', content.read_text())

    def test_identical_profile_permission_repair(self):
        profile = ensure_profile(self.home)
        profile.chmod(0o644)
        ensure_profile(self.home)
        self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o600)

    def test_explicit_config_directory_preserves_base_and_default_directory(self):
        directory = self.home / "custom-codex"
        directory.mkdir()
        base = directory / "config.toml"
        base.write_text("# Existing custom Codex configuration\n")
        before = base.read_bytes()
        profile = ensure_profile(self.home, config_dir=directory)
        self.assertEqual(profile.parent, directory)
        self.assertEqual(ensure_profile(self.home, config_dir=directory), profile)
        self.assertEqual(base.read_bytes(), before)
        self.assertFalse((self.home / ".codex").exists())

    def test_existing_different_profile_is_not_overwritten(self):
        profile = ensure_profile(self.home)
        replacement = "# User-maintained configuration\n"
        profile.write_text(replacement)
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            ensure_profile(self.home)
        self.assertEqual(profile.read_text(), replacement)

    def test_codex_saved_hook_trust_and_disabled_state_are_preserved_exactly(self):
        profile = ensure_profile(self.home, full_content=True)
        state = (
            '\n[hooks.state]\n\n'
            '[hooks.state."relay@relay-local:hooks/hooks.json:post_tool_use:0:0"]\n'
            'trusted_hash = "sha256:' + "a" * 64 + '"\n\n'
            '[hooks.state."tracing@codex-observability-plugin:hooks/hooks.json:stop:0:0"]\n'
            'enabled = false\n'
            'trusted_hash = "sha256:' + "b" * 64 + '"\n'
        )
        before = profile.read_bytes() + state.encode()
        profile.write_bytes(before)
        profile.chmod(0o644)
        for _ in range(2):
            self.assertEqual(ensure_profile(self.home, full_content=True), profile)
            self.assertEqual(profile.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(profile.stat().st_mode), 0o600)

    def test_saved_hook_state_cannot_hide_changed_managed_settings(self):
        profile = ensure_profile(self.home, full_content=True)
        modified = profile.read_bytes().replace(b"hooks = true", b"hooks = false")
        modified += b"\n[hooks.state]\n"
        profile.write_bytes(modified)
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            ensure_profile(self.home, full_content=True)
        self.assertEqual(profile.read_bytes(), modified)

    def test_non_hook_settings_and_malformed_hook_states_are_rejected(self):
        profile = ensure_profile(self.home, full_content=True)
        managed = profile.read_bytes()
        section = '[hooks.state."tracing@codex-observability-plugin:hooks/hooks.json:stop:0:0"]\n'
        trusted = 'trusted_hash = "sha256:' + "c" * 64 + '"\n'
        for suffix in (
            '\n[otel]\nlog_user_prompt = true\n',
            '\n[hooks.state]\n[features]\nhooks = false\n',
            '\n[hooks.state]\n' + section + 'command = "unexpected"\n',
            '\n[hooks.state]\n' + section + 'enabled = 1\n',
            '\n[hooks.state]\n' + section + 'trusted_hash = "invalid"\n',
            '\n[hooks.state]\n' + section + trusted + trusted,
            '\n[hooks.state]\n' + section + trusted + section + trusted,
            '\n[hooks.state]\n' + section + trusted + '[model_provider]\nname = "other"\n',
        ):
            with self.subTest(suffix=suffix):
                before = managed + suffix.encode()
                profile.write_bytes(before)
                with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                    ensure_profile(self.home, full_content=True)
                self.assertEqual(profile.read_bytes(), before)

    def test_existing_directory_is_rejected(self):
        profile = self.home / ".codex" / "sns-langfuse.config.toml"
        profile.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "not a regular file"):
            ensure_profile(self.home)
        self.assertTrue(profile.is_dir())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX FIFO support")
    def test_existing_fifo_is_rejected_without_waiting_for_a_writer(self):
        directory = self.home / ".codex"
        directory.mkdir()
        profile = directory / "sns-langfuse.config.toml"
        os.mkfifo(profile)
        with self.assertRaisesRegex(ValueError, "not a regular file"):
            ensure_profile(self.home)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires no-follow file opens")
    def test_existing_symlink_is_not_followed(self):
        profile = ensure_profile(self.home)
        external = self.home / "external.toml"
        profile.rename(external)
        profile.symlink_to(external)
        before = external.read_bytes()
        with self.assertRaisesRegex(ValueError, "not a regular file"):
            ensure_profile(self.home)
        self.assertEqual(external.read_bytes(), before)


class CommandTests(unittest.TestCase):
    def command(self, arguments, full_content=False, **kwargs):
        values = {"run_id": "run-123", "developer_id": "developer-1"}
        values.update(kwargs)
        return codex_command(arguments, full_content=full_content, **values)

    def test_native_arguments_are_literal_and_tagged_without_credentials(self):
        arguments = ["-C", "/tmp/project with spaces", "prompt $(do-not-run)"]
        command = self.command(
            arguments,
            run_id='run-"quoted"',
            developer_id="developer\\name",
            jira_key="RGWEALTH-634",
        )
        self.assertEqual(command[:3], ["codex", "--profile", "sns-langfuse"])
        self.assertEqual(command[-len(arguments):], arguments)
        self.assertEqual(command.count("-c"), 2)
        override = next(item for item in command if item.startswith("otel.span_attributes="))
        self.assertTrue(override.startswith("otel.span_attributes={"))
        self.assertTrue(override.endswith("}"))
        self.assertIn('"session.id"="run-\\"quoted\\""', override)
        self.assertIn('"user.id"="developer\\\\name"', override)
        self.assertIn('"langfuse.trace.metadata.team"="SNS"', override)
        self.assertIn('"langfuse.environment"="development"', override)
        self.assertIn('"langfuse.trace.metadata.jira_key"="RGWEALTH-634"', override)
        self.assertFalse(any(item.startswith("otel.span_attributes.") for item in command))
        self.assertFalse(any("Authorization" in item or "SECRET_KEY" in item for item in command))
        self.assertEqual(arguments, ["-C", "/tmp/project with spaces", "prompt $(do-not-run)"])

    def test_empty_jira_is_not_added(self):
        self.assertFalse(any("jira_key" in item for item in self.command([])))

    def test_native_environment_is_a_safely_escaped_scalar_override(self):
        command = self.command([], tracing_environment='pilot-"quoted"\\name')
        self.assertIn('otel.environment="pilot-\\"quoted\\"\\\\name"', command)

    def test_content_command_uses_plugin_profile_and_environment_metadata(self):
        self.assertEqual(
            self.command(["-C", "/tmp/project"], full_content=True),
            ["codex", "--profile", "sns-langfuse-content", "-C", "/tmp/project"],
        )

    def test_content_mode_blocks_historical_session_variants(self):
        for arguments in (
            ["resume"], ["fork"], ["exec", "resume", "task-id"],
            ["--last"], ["--resume", "task-id"], ["--fork", "task-id"],
            ["--resume=task-id"], ["--fork=task-id"], ["--last=true"],
        ):
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(ValueError, "brand-new task"):
                    self.command(arguments, full_content=True)

    def test_native_mode_does_not_impose_content_backfill_restrictions(self):
        self.assertEqual(self.command(["resume", "--last"])[-2:], ["resume", "--last"])

    def test_required_identity_fields_are_not_silently_empty(self):
        for values in ({"run_id": " "}, {"developer_id": ""}):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    self.command([], **values)


if __name__ == "__main__":
    unittest.main()
