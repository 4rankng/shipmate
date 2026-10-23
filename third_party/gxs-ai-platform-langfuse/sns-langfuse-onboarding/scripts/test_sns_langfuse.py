import json
import io
import os
from pathlib import Path
import tempfile
import unittest
import urllib.parse
from unittest.mock import patch

import sns_langfuse as app


class SettingsTests(unittest.TestCase):
    def settings_file(self, directory, text):
        path = Path(directory) / 'sns.env'
        path.write_text(text)
        path.chmod(0o600)
        return path

    def test_blank_template_never_authenticates(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.settings_file(d, app.TEMPLATE)
            with self.assertRaisesRegex(ValueError, 'Fill both'):
                app.load_settings(path)

    def test_env_is_data_not_executable_shell(self):
        with tempfile.TemporaryDirectory() as d:
            sentinel = Path(d) / 'should-not-exist'
            path = self.settings_file(d, 'LANGFUSE_PUBLIC_KEY="pk-test"\nLANGFUSE_SECRET_KEY="$(touch ' + str(sentinel) + ')"\n')
            with self.assertRaises(ValueError):
                app.load_settings(path)
            self.assertFalse(sentinel.exists())

    def test_host_cannot_redirect_keys(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.settings_file(d, 'LANGFUSE_BASE_URL="https://unexpected.example"\n')
            with self.assertRaisesRegex(ValueError, 'staging host'):
                app.load_settings(path, require_keys=False)

    def test_world_readable_key_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.settings_file(d, app.TEMPLATE)
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'private'):
                app.load_settings(path, require_keys=False)

    def test_unknown_variables_cannot_change_process_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.settings_file(d, 'NODE_OPTIONS="--require attacker.js"\n')
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                app.load_settings(path, require_keys=False)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.settings = {'LANGFUSE_PUBLIC_KEY': 'pk-test', 'LANGFUSE_SECRET_KEY': 'sk-test',
                         'LANGFUSE_BASE_URL': app.BASE_URL, 'LANGFUSE_HOST': app.BASE_URL,
                         'LANGFUSE_TRACING_ENVIRONMENT': 'development', 'SNS_DEVELOPER_ID': 'tester'}

    def test_default_codex_does_not_upload_transcripts(self):
        env, who = app.runtime_env(self.settings, 'codex', False, 'run-123', inherited={'TRACE_TO_LANGFUSE': 'true'})
        self.assertEqual('false', env['TRACE_TO_LANGFUSE'])
        self.assertEqual('tester', who)
        self.assertEqual(app.BASE_URL, env['LANGFUSE_CODEX_BASE_URL'])

    def test_native_codex_uses_sdk_environment_headers_without_profile_interpolation(self):
        inherited = {'OTEL_EXPORTER_OTLP_HEADERS': 'existing-log-header=keep',
                     'OTEL_EXPORTER_OTLP_LOGS_ENDPOINT': 'https://logs.example/v1/logs',
                     'SNS_LANGFUSE_AUTHORIZATION': 'placeholder-stale'}
        env, _ = app.runtime_env(self.settings, 'codex', False, 'run-123', inherited=inherited)
        headers = dict(item.split('=', 1) for item in env['OTEL_EXPORTER_OTLP_TRACES_HEADERS'].split(','))
        self.assertEqual(urllib.parse.unquote(headers['Authorization']), app.basic_authorization(self.settings))
        self.assertEqual(headers['x-langfuse-ingestion-version'], '4')
        self.assertEqual(env['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'], app.BASE_URL + '/api/public/otel/v1/traces')
        self.assertEqual(env['OTEL_EXPORTER_OTLP_HEADERS'], inherited['OTEL_EXPORTER_OTLP_HEADERS'])
        self.assertEqual(env['OTEL_EXPORTER_OTLP_LOGS_ENDPOINT'], inherited['OTEL_EXPORTER_OTLP_LOGS_ENDPOINT'])
        self.assertNotIn('SNS_LANGFUSE_AUTHORIZATION', env)
        command = app.codex_command([], full_content=False, run_id='run-123', developer_id='tester')
        self.assertNotIn(app.basic_authorization(self.settings), str(command))
        self.assertNotIn('sk-test', str(command))

    def test_content_mode_is_rejected_before_mutating_native_routing(self):
        inherited = {'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT': 'https://existing.example/v1/traces',
                     'OTEL_EXPORTER_OTLP_TRACES_HEADERS': 'existing-header=keep'}
        original = dict(inherited)
        with self.assertRaisesRegex(ValueError, 'metadata-only'):
            app.runtime_env(self.settings, 'codex', True, 'run-123', inherited=inherited)
        self.assertEqual(inherited, original)

    def test_native_codex_refuses_conflicting_trace_destinations(self):
        for key in ('OTEL_EXPORTER_OTLP_ENDPOINT', 'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, 'existing OTel'):
                    app.runtime_env(self.settings, 'codex', False, 'run-123',
                                    inherited={key: 'https://existing.example/v1/traces'})

    def test_copilot_content_flags_are_consistent(self):
        for full in (False,):
            env, _ = app.runtime_env(self.settings, 'copilot', full, 'run-123', 'RGWEALTH-634', inherited={})
            self.assertEqual(str(full).lower(), env['COPILOT_OTEL_CAPTURE_CONTENT'])
            self.assertEqual(str(full).lower(), env['OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT'])
            self.assertTrue(env['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'].endswith('/otel/v1/traces'))
            self.assertIn('x-langfuse-ingestion-version=4', env['OTEL_EXPORTER_OTLP_HEADERS'])

    def test_existing_other_exporter_is_not_silently_replaced(self):
        with self.assertRaisesRegex(ValueError, 'existing OTel'):
            app.runtime_env(self.settings, 'copilot', False, 'run-123', inherited={'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4318'})

    def test_signal_specific_exporter_is_not_silently_replaced(self):
        inherited = {'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT': 'https://existing.example/v1/traces'}
        for agent in ('copilot', 'vscode'):
            with self.subTest(agent=agent):
                with self.assertRaisesRegex(ValueError, 'existing OTel'):
                    app.runtime_env(self.settings, agent, False, 'run-123', inherited=inherited)
        self.assertEqual(inherited['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'], 'https://existing.example/v1/traces')

    def test_matching_signal_specific_exporter_can_be_reused(self):
        endpoint = app.BASE_URL + '/api/public/otel/v1/traces'
        env, _ = app.runtime_env(self.settings, 'copilot', False, 'run-123',
                                 inherited={'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT': endpoint + '/'})
        self.assertEqual(env['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'], endpoint)

    def test_copilot_developer_attribute_is_encoded_without_replacing_existing_attributes(self):
        settings = dict(self.settings, SNS_DEVELOPER_ID='developer@example.com,team=other')
        env, developer = app.runtime_env(settings, 'copilot', False, 'run-123',
            inherited={'OTEL_RESOURCE_ATTRIBUTES': 'existing.attribute=keep'})
        attributes = dict(item.split('=', 1) for item in env['OTEL_RESOURCE_ATTRIBUTES'].split(','))
        self.assertEqual(attributes['existing.attribute'], 'keep')
        self.assertEqual(attributes['sns.team'], 'SNS')
        self.assertEqual(urllib.parse.unquote(attributes['sns.developer_id']), developer)
        self.assertNotIn('team', attributes)

    def test_codex_metadata_has_jira_and_run_without_keys(self):
        env, _ = app.runtime_env(self.settings, 'codex', False, 'run-123', 'RGWEALTH-634', inherited={})
        metadata = json.loads(env['LANGFUSE_CODEX_METADATA'])
        self.assertEqual('RGWEALTH-634', metadata['jira_key'])
        self.assertEqual('run-123', metadata['run_id'])
        self.assertNotIn('sk-test', env['LANGFUSE_CODEX_METADATA'])

    def test_api_failure_does_not_echo_secret_bearing_diagnostics(self):
        failed = type('Result', (), {'returncode': 1, 'stderr': 'Authorization: sk-test', 'stdout': ''})()
        with patch('sns_langfuse.subprocess.run', return_value=failed):
            with self.assertRaises(ValueError) as failure:
                app.langfuse_cli(self.settings, 'projects', 'list')
        self.assertNotIn('sk-test', str(failure.exception))


class LauncherTests(unittest.TestCase):
    def test_full_content_is_rejected_before_credentials_or_process_launch(self):
        for agent in ('codex', 'copilot', 'vscode'):
            with self.subTest(agent=agent), patch('sns_langfuse.load_settings') as load, \
                    patch('sns_langfuse.run_with_usage') as launch:
                with self.assertRaisesRegex(ValueError, 'metadata-only'):
                    app.main(['run', agent, '--full-content'])
                load.assert_not_called()
                launch.assert_not_called()

    def test_init_respects_codex_home_without_changing_default_codex_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_home = home / 'custom-codex'
            with patch.dict(os.environ, {'CODEX_HOME': str(codex_home)}, clear=True), \
                    patch('sns_langfuse.Path.home', return_value=home), \
                    patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(app.main(['init']), 0)
            self.assertTrue((codex_home / 'sns-langfuse.config.toml').is_file())
            self.assertFalse((codex_home / 'sns-langfuse-content.config.toml').exists())
            self.assertFalse((home / '.codex').exists())

    def test_run_uses_custom_codex_directory_and_configured_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_home = home / 'custom-codex'
            settings = {'LANGFUSE_PUBLIC_KEY': 'pk-test', 'LANGFUSE_SECRET_KEY': 'sk-test',
                        'LANGFUSE_BASE_URL': app.BASE_URL, 'LANGFUSE_HOST': app.BASE_URL,
                        'LANGFUSE_TRACING_ENVIRONMENT': 'pilot', 'SNS_DEVELOPER_ID': 'tester'}
            with patch.dict(os.environ, {'CODEX_HOME': str(codex_home)}, clear=True), \
                    patch('sns_langfuse.Path.home', return_value=home), \
                    patch('sns_langfuse.load_settings', return_value=settings), \
                    patch('sns_langfuse.shutil.which', return_value='/test/codex'), \
                    patch('sns_langfuse.run_with_usage', return_value=0) as launch, \
                    patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(app.main(['run', 'codex']), 0)
            self.assertTrue((codex_home / 'sns-langfuse.config.toml').is_file())
            self.assertFalse((home / '.codex').exists())
            arguments, env = launch.call_args.args[:2]
            self.assertIn('otel.environment="pilot"', arguments)
            self.assertEqual(env['CODEX_HOME'], str(codex_home))


if __name__ == '__main__':
    unittest.main()
