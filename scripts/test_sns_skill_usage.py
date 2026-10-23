import tempfile
import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

import sns_skill_usage as usage


class SkillUsageTests(unittest.TestCase):
    def test_normal_clients_never_read_keys(self):
        with patch.object(usage, 'read_keys', side_effect=AssertionError('unexpected')):
            self.assertEqual(usage.publish('run', env={}), 'not-opted-in')
            self.assertEqual(usage.publish('run', env={'SNS_LANGFUSE_CLIENT': 'codex'}), 'missing-session-or-user')
            self.assertEqual(usage.publish('run', env={'SNS_LANGFUSE_CLIENT': 'codex', 'CODEX_THREAD_ID': '-' * 36,
                                                      'SNS_LANGFUSE_USER_ID': 'engineer'}), 'missing-session-or-user')

    def test_upload_failure_is_advisory_and_redacted(self):
        output = io.StringIO()
        with patch('sys.argv', ['sns_skill_usage.py', '--skill', 'run']), \
                patch.object(usage, 'publish', side_effect=ValueError('PRIVATE-KEY')), contextlib.redirect_stdout(output):
            self.assertEqual(usage.main(), 0)
        self.assertIn('incomplete', output.getvalue())
        self.assertNotIn('PRIVATE-KEY', output.getvalue())

    def test_explicit_entry_only_and_no_content(self):
        records = []
        class Sink:
            def __init__(self, *args): pass
            def publish(self, batch): records.extend(batch)
            def close(self): pass
        env = {'SNS_LANGFUSE_CLIENT': 'codex', 'SNS_LANGFUSE_USER_ID': 'test.engineer',
               'CODEX_THREAD_ID': '01a14327-a0f2-7f43-b81d-3b155ba23e2e', 'PROMPT': 'PRIVATE'}
        with patch.object(usage, 'read_keys', return_value={'LANGFUSE_PUBLIC_KEY': 'pk-test', 'LANGFUSE_SECRET_KEY': 'sk-test'}):
            self.assertEqual(usage.publish('review', env=env, sink_factory=Sink), 'recorded')
            with self.assertRaises(ValueError): usage.publish('installed-inventory', env=env, sink_factory=Sink)
        self.assertEqual([(r['kind'], r['name']) for r in records], [('skill', 'shipmate:review'), ('plugin', 'shipmate')])
        self.assertTrue(all(r['session_id'] == env['CODEX_THREAD_ID'] for r in records))
        self.assertNotIn('PRIVATE', str(records))
        self.assertTrue(all(r['source_trace_id'] == '' for r in records))

    def test_real_sink_deduplicates_repeated_entries_and_plugin_across_phases(self):
        import importlib.util
        path = Path(usage.__file__).resolve().parents[1] / 'third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/scripts/usage_sink.py'
        spec = importlib.util.spec_from_file_location('sink_fixture', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        bodies = []
        with tempfile.TemporaryDirectory() as tmp:
            def factory(keys, user, auth):
                return module.UsageSink(keys, user, auth, directory=Path(tmp), sender=lambda body, _: bodies.append(body))
            env = {'SNS_LANGFUSE_CLIENT': 'codex', 'SNS_LANGFUSE_USER_ID': 'test.engineer',
                   'CODEX_THREAD_ID': '01a14327-a0f2-7f43-b81d-3b155ba23e2e'}
            keys = {'LANGFUSE_PUBLIC_KEY': 'pk-test', 'LANGFUSE_SECRET_KEY': 'sk-test', 'LANGFUSE_TRACING_ENVIRONMENT': 'development'}
            with patch.object(usage, 'read_keys', return_value=keys):
                for skill in ['run', 'run', 'review']: usage.publish(skill, env=env, sink_factory=factory)
        spans = [b['resourceSpans'][0]['scopeSpans'][0]['spans'][0] for b in bodies]
        self.assertEqual([s['name'] for s in spans], ['shipmate:run', 'shipmate', 'shipmate:review'])
