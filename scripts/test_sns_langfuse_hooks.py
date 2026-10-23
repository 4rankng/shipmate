import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sns_langfuse_hooks as hooks


class MetadataHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.sent = []
        self.clock = 1000.0
        self.client = 'codex'
        self.transcript = self.home / '.codex/sessions/fresh.jsonl'
        self.transcript.parent.mkdir(parents=True)
        self.transcript.write_text('')
        self.settings = self.home / '.config/langfuse/hooks.json'
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(json.dumps({'clients': {'codex': {'enabled': True, 'user_id': 'test.engineer'},
                                                       'claude': {'enabled': True, 'user_id': 'test.engineer'}}}))
        self.settings.chmod(0o600)

    def event(self, name, **fields):
        data = dict(session_id='fresh-session', hook_event_name=name,
                    transcript_path=str(self.transcript), model=fields.pop('model', 'gpt-6.1-sol'), **fields)
        with patch.dict(os.environ, {}, clear=True):
            return hooks.handle_event(self.client, data, home=self.home, now=self.clock, send=self.sent.append)

    def append(self, record):
        if self.client == 'claude': record.setdefault('sessionId', 'fresh-session')
        with self.transcript.open('a') as stream:
            stream.write(json.dumps(record) + '\n')

    def tokens(self, total, last=None):
        def usage(n): return dict(input_tokens=n, cached_input_tokens=n // 2,
            cache_write_input_tokens=0, output_tokens=n // 10, reasoning_output_tokens=0, total_tokens=n + n // 10)
        self.append({'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
            'total_token_usage': usage(total), 'last_token_usage': usage(total if last is None else last)}}})

    def start(self):
        self.event('SessionStart', source='startup')
        self.event('UserPromptSubmit', prompt='PRIVATE-PROMPT')
        self.clock += 2

    def attrs(self):
        spans = self.sent[-1]['resourceSpans'][0]['scopeSpans'][0]['spans']
        return [dict((a['key'], a['value'].get('stringValue', a['value'].get('intValue'))) for a in s['attributes']) for s in spans]

    def test_claude_transcript_created_after_prompt_is_fresh_only(self):
        self.client = 'claude'
        self.transcript = self.home / '.claude/projects/fresh/fresh-session.jsonl'
        self.transcript.parent.mkdir(parents=True)
        self.start()
        self.assertFalse(self.transcript.exists())
        usage = dict(input_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0, output_tokens=2)
        self.append({'type': 'assistant', 'message': {'id': 'new', 'model': 'claude-sonnet-4-6', 'usage': usage}})
        self.append({'type': 'assistant', 'sessionId': 'other-session', 'message': {'id': 'old', 'usage': usage}})
        self.event('Stop')
        self.assertEqual(self.attrs()[-1]['gen_ai.usage.input_tokens'], '10')
        self.event('Stop'); self.assertEqual(len(self.sent), 1)

    def test_disabled_is_inert_without_credentials(self):
        self.settings.unlink()
        self.start(); self.tokens(100); self.event('Stop')
        self.assertEqual(self.sent, [])

    def test_codex_fresh_delta_cache_math_dedup_and_no_content_export(self):
        self.tokens(200)  # before the startup cursor: never exported
        self.start(); self.tokens(300, last=100)
        self.append({'type': 'response_item', 'payload': {'content': 'PRIVATE-RESPONSE', 'arguments': 'PRIVATE-TOOL'}})
        self.event('Stop', last_assistant_message='PRIVATE-LAST')
        text = json.dumps(self.sent)
        for marker in ['PRIVATE-PROMPT', 'PRIVATE-RESPONSE', 'PRIVATE-TOOL', 'PRIVATE-LAST', str(self.home)]:
            self.assertNotIn(marker, text)
        generation = self.attrs()[-1]
        self.assertEqual(generation['gen_ai.usage.input_tokens'], '50')
        self.assertEqual(generation['gen_ai.usage.cache_read_input_tokens'], '50')
        self.assertEqual(generation['gen_ai.usage.output_tokens'], '10')
        self.assertNotIn('langfuse.observation.cost_details', generation)
        self.event('Stop'); self.assertEqual(len(self.sent), 1)

    def test_resume_fork_and_replaced_or_truncated_transcript_are_excluded(self):
        for source in ['resume', 'fork', 'clear']:
            self.event('SessionStart', source=source); self.tokens(100); self.event('Stop')
        self.assertEqual(self.sent, [])
        self.start(); self.tokens(100)
        replacement = self.transcript.with_suffix('.new'); replacement.write_text(self.transcript.read_text())
        replacement.replace(self.transcript)
        self.event('Stop'); self.assertEqual(self.sent, [])
        self.start(); self.transcript.write_text(''); self.event('Stop'); self.assertEqual(self.sent, [])

    def test_tool_pair_ignores_arguments_results_and_deduplicates(self):
        self.start()
        self.event('PreToolUse', tool_use_id='tool-1', tool_name='Read', tool_input={'path': 'PRIVATE-PATH'})
        self.clock += 1
        self.event('PostToolUse', tool_use_id='tool-1', tool_name='Read', tool_response='PRIVATE-RESULT')
        self.event('PostToolUse', tool_use_id='tool-1', tool_name='Read')
        self.tokens(100); self.event('Stop')
        spans = self.sent[0]['resourceSpans'][0]['scopeSpans'][0]['spans']
        self.assertEqual(sum(s['name'] == 'codex.tool' for s in spans), 1)
        self.assertNotIn('PRIVATE-', json.dumps(self.sent))

    def test_claude_groups_repeated_message_usage_without_double_counting_cache(self):
        self.client = 'claude'
        self.transcript = self.home / '.claude/projects/fresh.jsonl'
        self.transcript.parent.mkdir(parents=True); self.transcript.write_text('')
        self.start()
        message = {'id': 'msg-1', 'model': 'claude-sonnet-4-6', 'usage': {
            'input_tokens': 20, 'cache_read_input_tokens': 80, 'cache_creation_input_tokens': 10, 'output_tokens': 5},
            'content': 'PRIVATE-CONTENT'}
        self.append({'type': 'assistant', 'message': message}); self.append({'type': 'assistant', 'message': message})
        self.event('Stop')
        a = self.attrs()[-1]
        self.assertEqual(a['gen_ai.usage.input_tokens'], '20')
        self.assertEqual(a['gen_ai.usage.cache_read_input_tokens'], '80')
        self.assertEqual(a['gen_ai.usage.cache_creation_input_tokens'], '10')
        self.assertEqual(a['gen_ai.usage.output_tokens'], '5')
        self.assertNotIn('PRIVATE-CONTENT', json.dumps(self.sent))

    def test_identity_or_opt_in_revision_changes_require_a_new_session(self):
        for field, value in [('user_id', 'another.engineer'), ('generation', 'new-opt-in')]:
            self.start(); self.tokens(100)
            data = json.loads(self.settings.read_text()); data['clients']['codex'][field] = value
            self.settings.write_text(json.dumps(data))
            self.event('Stop')
            self.assertEqual(self.sent, [])

    def test_unknown_schema_and_mixed_models_never_invent_model_or_usage(self):
        self.start()
        for model in ['gpt-6-sol', 'gpt-6.1-sol']:
            self.append({'type': 'turn_context', 'payload': {'model': model}})
        self.append({'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': 'PRIVATE-USAGE'}}})
        self.event('Stop')
        a = self.attrs()[-1]
        self.assertNotIn('gen_ai.request.model', a)
        self.assertFalse(any(k.startswith('gen_ai.usage.') for k in a))
        self.assertNotIn('PRIVATE-USAGE', json.dumps(self.sent))

    def test_unsafe_and_oversized_transcripts_never_publish(self):
        self.start()
        self.append({'type': 'response_item', 'payload': 'x' * (hooks.LIMIT + 1)})
        self.event('Stop'); self.assertEqual(self.sent, [])
        self.transcript.write_text('')
        self.start()
        target = self.home / 'other.jsonl'; target.write_text('{}')
        self.transcript.unlink(); self.transcript.symlink_to(target)
        with self.assertRaises(ValueError): self.event('Stop')
        self.assertEqual(self.sent, [])

    def test_observed_concurrent_config_change_is_not_overwritten(self):
        path = self.home / 'settings.json'; path.write_text('{"theme":"original"}')
        original_sync = hooks.os.fsync
        changed = []
        def concurrent(fd):
            original_sync(fd)
            if not changed:
                changed.append(True); path.write_text('{"theme":"external"}')
        with patch.object(hooks.os, 'fsync', side_effect=concurrent):
            with self.assertRaises(ValueError):
                hooks.mutate_json(path, lambda data: data.update(theme='managed'))
        self.assertEqual(json.loads(path.read_text()), {'theme': 'external'})

    def test_interrupted_disable_is_inert_and_interrupted_initial_install_does_not_enable(self):
        config = self.home / '.claude/settings.json'; config.parent.mkdir(parents=True); config.write_text('{}')
        mutate = hooks.mutate_json
        def fail_config(path, *args, **kwargs):
            if path == config: raise OSError('synthetic interruption')
            return mutate(path, *args, **kwargs)
        with patch.object(hooks, 'mutate_json', side_effect=fail_config):
            with self.assertRaises(OSError): hooks.configure('claude', False, 'test.engineer', self.home)
        self.assertFalse(json.loads(self.settings.read_text())['clients']['claude']['enabled'])
        with patch.object(hooks, 'mutate_json', side_effect=fail_config):
            with self.assertRaises(OSError): hooks.configure('claude', True, 'test.engineer', self.home)
        self.assertFalse(json.loads(self.settings.read_text())['clients']['claude']['enabled'])

    def test_install_disable_preserve_existing_settings_and_are_idempotent(self):
        config = self.home / '.claude/settings.json';config.parent.mkdir(parents=True)
        original = {'theme': 'dark', 'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo keep'}]}]}}
        config.write_text(json.dumps(original))
        hooks.configure('claude', True, 'test.engineer', self.home)
        with patch.object(hooks.sys, 'executable', '/different/python3'):
            hooks.configure('claude', True, 'test.engineer', self.home)
        data = json.loads(config.read_text())
        self.assertEqual(data['theme'], 'dark')
        for event in hooks.EVENTS:
            matches = [h for group in data['hooks'][event] for h in group['hooks'] if 'sns_langfuse_hooks.py' in h.get('command', '')]
            self.assertEqual(len(matches), 1)
        hooks.configure('claude', False, 'test.engineer', self.home)
        self.assertEqual(json.loads(config.read_text()), original)

    def test_config_refuses_symlink_and_preserves_source_on_replace_failure(self):
        target = self.home / 'victim.json'; target.write_text('{}')
        config = self.home / '.claude/settings.json';config.parent.mkdir(parents=True);config.symlink_to(target)
        with self.assertRaises(ValueError): hooks.configure('claude', True, 'test.engineer', self.home)
        self.assertEqual(target.read_text(), '{}')
        config.unlink(); config.write_text('{"theme":"dark"}')
        with patch.object(hooks.os, 'replace', side_effect=OSError('PRIVATE-ERROR')):
            with self.assertRaises(OSError): hooks.configure('claude', True, 'test.engineer', self.home)
        self.assertEqual(json.loads(config.read_text()), {'theme': 'dark'})

@unittest.skipUnless(os.environ.get('SNS_SIMULATION_URL'), 'opt-in local Postman HTTP simulation')
class HookHTTPSimulationTests(unittest.TestCase):
    def test_real_exporter_success_partial_rejection_http_error_and_redirect(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            keys = home / '.config/langfuse/sns.env';keys.parent.mkdir(parents=True)
            keys.write_text('\n'.join([
                'LANGFUSE_BASE_URL=' + hooks.BASE_URL, 'LANGFUSE_HOST=' + hooks.BASE_URL,
                'LANGFUSE_TRACING_ENVIRONMENT=development', 'LANGFUSE_PUBLIC_KEY=pk-lf-test-only',
                'LANGFUSE_SECRET_KEY=sk-lf-test-only']))
            keys.chmod(0o600)
            state = {'started': 1000, 'turn': 1, 'turn_started': 1001, 'completed_tools': []}
            for service, fails in [('simulate-ok', False), ('simulate-partial', True),
                                   ('simulate-error', True), ('simulate-redirect', True)]:
                payload = hooks.otlp_payload('codex', 'fresh-simulation', 'test.engineer', state, 1002, None, set())
                payload['resourceSpans'][0]['resource']['attributes'][0]['value']['stringValue'] = service
                with patch.object(hooks, 'BASE_URL', os.environ['SNS_SIMULATION_URL']):
                    if fails:
                        with self.assertRaises(Exception): hooks.send_payload(payload, home)
                    else:
                        hooks.send_payload(payload, home)
