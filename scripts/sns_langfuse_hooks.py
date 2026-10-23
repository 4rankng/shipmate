#!/usr/bin/env python3
"""Opt-in, fresh-session metadata hooks for Codex desktop/CLI and Claude Code."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile
import time
import urllib.request
import uuid

from sns_langfuse_codex import BASE_URL, read_keys

EVENTS = ('SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Stop', 'SessionEnd')
LIMIT = 4 * 1024 * 1024
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:@/+\-]{0,199}\Z')
COUNTERS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens')


def valid(value):
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value))


def safe_path(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('Symlinked SNS path')
    if path.exists():
        info = path.stat()
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode):
            raise ValueError('SNS files must be regular files owned by you')


def identity(path):
    safe_path(path)
    if not path.exists():
        return None
    info = path.stat()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def private_directory(path):
    # Never change permissions on unrelated ancestors.
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlinked SNS directory')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid():
        raise ValueError('SNS directory must be owned by you')


def atomic_json(path, data, expected, original, mode=0o600):
    private_directory(path.parent)
    fd, temporary = tempfile.mkstemp(prefix='.sns-hooks-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if identity(path) != expected or (path.read_bytes() if path.exists() else None) != original:
            raise ValueError('Configuration changed concurrently; no replacement made')
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def mutate_json(path, change, private=False):
    private_directory(path.parent)
    lock = path.with_name(path.name + '.sns-lock')
    safe_path(lock)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        before = identity(path)
        original = path.read_bytes() if before else None
        if before and private and path.stat().st_mode & 0o077:
            raise ValueError('SNS opt-in/state files must be owner-only')
        data = json.loads(original) if original else {}
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object')
        result = change(data)
        mode = stat.S_IMODE(path.stat().st_mode) if before and not private else 0o600
        atomic_json(path, data, before, original, mode)
        return result


def settings_path(home):
    return home / '.config/langfuse/hooks.json'


def native_home(client, home):
    variable, fallback = ('CODEX_HOME', '.codex') if client == 'codex' else ('CLAUDE_CONFIG_DIR', '.claude')
    return Path(os.environ.get(variable, str(home / fallback))).absolute()


def configure(client, enabled, user, home=None):
    home = (home or Path.home()).resolve()
    if not valid(user):
        raise ValueError('Use a nonempty user identifier')
    target = home / '.local/share/sns-langfuse/hooks/sns_langfuse_hooks.py'
    command = ' '.join(map(shlex.quote, [sys.executable, str(target), 'event', '--client', client]))
    config = native_home(client, home) / ('hooks.json' if client == 'codex' else 'settings.json')
    safe_path(config)  # Reject unsafe settings before any installation work.
    def opt_in(data):
        clients = data.setdefault('clients', {})
        clients[client] = {'enabled': enabled, 'user_id': user, 'generation': uuid.uuid4().hex}
    if not enabled:
        mutate_json(settings_path(home), opt_in, private=True)
    else:
        private_directory(target.parent)
        # Stable helpers are independent of branch/cache lifetime. No credential copy.
        for filename in ('sns_langfuse_hooks.py', 'sns_langfuse_codex.py'):
            path = target.parent / filename
            safe_path(path)
            source = Path(__file__).with_name(filename).read_bytes()
            fd, temporary = tempfile.mkstemp(prefix='.sns-helper-', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(source); stream.flush(); os.fsync(stream.fileno())
                os.chmod(temporary, 0o700); os.replace(temporary, path)
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
    def update(data):
        hooks = data.setdefault('hooks', {})
        if not isinstance(hooks, dict): raise ValueError('Invalid hook configuration')
        for event in EVENTS:
            groups = hooks.get(event, [])
            if not isinstance(groups, list): raise ValueError('Invalid hook groups')
            kept = []
            for group in groups:
                handlers = group.get('hooks', [])
                if not isinstance(handlers, list): raise ValueError('Invalid hook handlers')
                def owned(handler):
                    try:
                        return shlex.split(handler.get('command', ''))[1:] == [str(target), 'event', '--client', client]
                    except ValueError:
                        return False
                remaining = [h for h in handlers if not owned(h)]
                if remaining:
                    kept.append({**group, 'hooks': remaining})
                elif not handlers:
                    kept.append(group)
            if enabled:
                kept.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 6}]})
            if kept: hooks[event] = kept
            else: hooks.pop(event, None)
    mutate_json(config, update)
    if enabled:
        mutate_json(settings_path(home), opt_in, private=True)  # Enable only after hook config succeeds.
    return config


def transcript_path(client, event, home):
    path = Path(event.get('transcript_path') or '')
    root = native_home(client, home) / ('sessions' if client == 'codex' else 'projects')
    if not path.is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Transcript must be inside the selected client session directory')
    safe_path(path)
    return path


def open_transcript(client, event, home):
    path = transcript_path(client, event, home)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    stream = os.fdopen(fd, 'rb')
    info = os.fstat(stream.fileno())
    if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode):
        stream.close(); raise ValueError('Unsafe transcript')
    return path, stream, info


def numbers(values, fields):
    if not isinstance(values, dict) or any(type(values.get(k)) is not int or values[k] < 0 for k in fields):
        return None
    return {k: values[k] for k in fields}


def usage_records(client, records, state):
    models, totals = set(), None
    if client == 'codex':
        summed = dict.fromkeys(COUNTERS, 0)
        previous = state.get('usage_total')
        for record in records:
            payload = record.get('payload', {})
            if record.get('type') == 'turn_context' and valid(payload.get('model')):
                models.add(payload['model'])
            if record.get('type') != 'event_msg' or payload.get('type') != 'token_count': continue
            info = payload.get('info') or {}
            total = numbers(info.get('total_token_usage'), COUNTERS)
            last = numbers(info.get('last_token_usage'), COUNTERS)
            if total is None or last is None: continue
            baseline = previous if previous is not None else {k: total[k] - last[k] for k in COUNTERS}
            if any(baseline[k] < 0 or total[k] < baseline[k] for k in COUNTERS):
                raise ValueError('Usage counter reset')
            for key in COUNTERS: summed[key] += total[key] - baseline[key]
            previous = total; totals = summed
        if previous is not None: state['usage_total'] = previous
        if totals is not None:
            if totals['cached_input_tokens'] + totals['cache_write_input_tokens'] > totals['input_tokens']:
                raise ValueError('Invalid cache subset')
            totals = {'input_tokens': totals['input_tokens'] - totals['cached_input_tokens'] - totals['cache_write_input_tokens'],
                      'cache_read_input_tokens': totals['cached_input_tokens'],
                      'cache_creation_input_tokens': totals['cache_write_input_tokens'], 'output_tokens': totals['output_tokens']}
    else:
        messages = {}
        fields = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens')
        for record in records:
            if record.get('type') != 'assistant': continue
            message = record.get('message') or {}
            usage = numbers(message.get('usage'), fields)
            if valid(message.get('id')) and usage is not None:
                messages[message['id']] = usage
                if valid(message.get('model')): models.add(message['model'])
        if messages: totals = {k: sum(m[k] for m in messages.values()) for k in fields}
    return totals, models


def otlp_payload(client, session, user, state, now, usage, models):
    def digest(value, length): return hashlib.sha256(value.encode()).hexdigest()[:length]
    trace = digest(client + ':' + session, 32)
    root = digest(session + ':root', 16)
    common = {'langfuse.user.id': user, 'langfuse.session.id': session,
              'langfuse.environment': 'development', 'langfuse.trace.name': client + '.session',
              'langfuse.trace.metadata.team': 'SNS', 'langfuse.observation.metadata.capture': 'metadata-only',
              'langfuse.observation.metadata.client': client}
    def span(name, key, start, end, attributes, parent=None):
        result = dict(traceId=trace, spanId=key, name=name, kind=1,
            startTimeUnixNano=str(int(start * 1e9)), endTimeUnixNano=str(int(end * 1e9)),
            attributes=[{'key': k, 'value': {'intValue': str(v)} if type(v) is int else {'stringValue': v}}
                        for k, v in {**common, **attributes}.items()])
        if parent: result['parentSpanId'] = parent
        return result
    rows = [span(client + '.session', root, state['started'], now, {'langfuse.observation.type': 'span'})]
    for tool in state.get('completed_tools', []):
        rows.append(span(client + '.tool', digest(session + ':tool:' + tool['id'], 16), tool['start'], tool['end'],
                         {'langfuse.observation.type': 'tool', 'gen_ai.tool.name': tool['name']}, root))
    attrs = {'langfuse.observation.type': 'generation', 'langfuse.observation.metadata.aggregation': 'turn'}
    if usage is not None:
        attrs.update({'gen_ai.usage.' + key: value for key, value in usage.items()})
    if not models and valid(state.get('model')): models.add(state['model'])
    if len(models) == 1: attrs['gen_ai.request.model'] = next(iter(models))
    rows.append(span(client + '.turn', digest(session + ':turn:' + str(state['turn']), 16), state['turn_started'], now, attrs, root))
    return {'resourceSpans': [{'resource': {'attributes': [{'key': 'service.name', 'value': {'stringValue': 'sns-' + client + '-hooks'}}]},
                              'scopeSpans': [{'scope': {'name': 'sns-metadata-hooks', 'version': '1'}, 'spans': rows}]}]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Telemetry redirects are not allowed')


def send_payload(payload, home):
    keys = read_keys(home / '.config/langfuse/sns.env')
    auth = base64.b64encode((keys['LANGFUSE_PUBLIC_KEY'] + ':' + keys['LANGFUSE_SECRET_KEY']).encode()).decode()
    request = urllib.request.Request(BASE_URL + '/api/public/otel/v1/traces', data=json.dumps(payload).encode(),
        headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json', 'x-langfuse-ingestion-version': '4'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=3) as response:
        result = json.loads(response.read(65536))
    if int(result.get('partialSuccess', {}).get('rejectedSpans', 0)):
        raise ValueError('Partial telemetry rejection')


def handle_event(client, event, home=None, now=None, send=None):
    home = (home or Path.home()).resolve(); now = time.time() if now is None else now
    settings = settings_path(home)
    if not settings.exists(): return
    safe_path(settings)
    if settings.stat().st_mode & 0o077: raise ValueError('SNS opt-in must be owner-only')
    config = json.loads(settings.read_text()).get('clients', {}).get(client, {})
    if config.get('enabled') is not True or not valid(config.get('user_id')): return
    session, name = event.get('session_id'), event.get('hook_event_name')
    if not valid(session) or name not in EVENTS: return
    state_path = home / '.local/state/sns-langfuse/hooks' / (hashlib.sha256((client + ':' + session).encode()).hexdigest() + '.json')
    def process(state):
        if name == 'SessionStart':
            source = event.get('source')
            if source == 'compact': return
            state.clear()
            if source != 'startup': return
            state.update(armed=True, started=now, turn=0, tools={}, completed_tools=[],
                         opt_in=config.get('generation'), user_id=config['user_id'])
            if event.get('transcript_path'):
                path = transcript_path(client, event, home)
                if path.exists():
                    path, stream, info = open_transcript(client, event, home)
                    stream.close(); state.update(path=str(path), file_id=[info.st_dev, info.st_ino], cursor=info.st_size)
                elif client == 'claude' and path.name == session + '.jsonl':
                    # Claude creates the fresh transcript after the prompt hook. Remember
                    # only this exact path observed absent at startup, never an archive.
                    state['pending_path'] = str(path)
            return
        if not state.get('armed'): return
        if state.get('opt_in') != config.get('generation') or state.get('user_id') != config['user_id']:
            state['armed'] = False; return
        if name == 'SessionEnd': state['armed'] = False; return
        if name == 'UserPromptSubmit':
            state['turn'] += 1; state['turn_started'] = now
            state['tools'] = {}; state['completed_tools'] = []
            state['model'] = event.get('model') if valid(event.get('model')) else None
            if not state.get('path'):
                path = transcript_path(client, event, home)
                if str(path) == state.get('pending_path'):
                    return  # bind only at Stop; all accepted rows must match this session
                path, stream, info = open_transcript(client, event, home)
                stream.close(); state.update(path=str(path), file_id=[info.st_dev, info.st_ino], cursor=info.st_size)
            return
        if not state.get('turn_started') or state.get('processed_turn') == state['turn']: return
        call_id = event.get('tool_use_id')
        if name == 'PreToolUse' and valid(call_id) and valid(event.get('tool_name')) and len(state['tools']) < 1000:
            state['tools'].setdefault(call_id, {'id': call_id, 'name': event['tool_name'], 'start': now})
        elif name == 'PostToolUse' and valid(call_id):
            tool = state['tools'].pop(call_id, None)
            if tool is not None and now >= tool['start'] and len(state['completed_tools']) < 1000:
                state['completed_tools'].append({**tool, 'end': now})
        elif name == 'Stop':
            path, stream, info = open_transcript(client, event, home)
            pending = state.get('pending_path')
            if pending:
                if str(path) != pending or info.st_mtime < state['started']:
                    stream.close(); state['armed'] = False; return
                state.update(path=str(path), file_id=[info.st_dev, info.st_ino], cursor=0)
                state.pop('pending_path')
            with stream:
                if str(path) != state.get('path') or [info.st_dev, info.st_ino] != state.get('file_id') or info.st_size < state['cursor']:
                    state['armed'] = False; return
                if info.st_size - state['cursor'] > LIMIT:
                    state['armed'] = False; return
                stream.seek(state['cursor']); data = stream.read(LIMIT + 1)
            records = []
            for line in data.splitlines():
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        if client == 'claude' and (row.get('sessionId') != session or row.get('isSidechain')):
                            continue
                        records.append(row)
                except ValueError: continue
            usage, models = usage_records(client, records, state)
            payload = otlp_payload(client, session, config['user_id'], state, now, usage, models)
            # Advance even on upload failure: no historical backfill/retry archive.
            state['cursor'] = info.st_size; state['processed_turn'] = state['turn']
            state['tools'] = {}; state['completed_tools'] = []
            return payload
    payload = mutate_json(state_path, process, private=True)
    if payload is not None:
        (send or (lambda p: send_payload(p, home)))(payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'disable', 'event'))
    parser.add_argument('--client', required=True, choices=('codex', 'claude'))
    parser.add_argument('--user-id', default=None)
    args = parser.parse_args(argv)
    try:
        if args.action == 'event':
            raw = sys.stdin.buffer.read(LIMIT + 1)
            if len(raw) <= LIMIT: handle_event(args.client, json.loads(raw))
        else:
            import getpass
            path = configure(args.client, args.action == 'install', args.user_id or getpass.getuser())
            print('Updated managed SNS metadata hooks:', path)
            if args.action == 'install': print('Review native hook trust, then start a fresh session. Ingestion is not yet verified.')
    except Exception:
        print('SNS metadata hook incomplete; no content or error details were logged.', file=sys.stderr)
        if args.action != 'event': return 1
    if args.action == 'event': print('{}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
