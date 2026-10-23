#!/usr/bin/env python3
"""Publish an actual L3 entry in an opted-in Codex session, never an inventory."""
import argparse
import base64
import importlib.util
import os
from pathlib import Path
import re
import time
import uuid

from sns_langfuse_codex import read_keys


def publish(skill, env=None, home=None, sink_factory=None):
    env = os.environ if env is None else env
    if env.get('SNS_LANGFUSE_CLIENT') != 'codex':
        return 'not-opted-in'
    session, user = env.get('CODEX_THREAD_ID', ''), env.get('SNS_LANGFUSE_USER_ID', '')
    try:
        valid_session = str(uuid.UUID(session)) == session.lower()
    except ValueError:
        valid_session = False
    if not valid_session or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._@+-]{0,199}', user):
        return 'missing-session-or-user'
    if skill not in {'specify', 'run', 'review'}:
        raise ValueError('Only the actual public L3 entry is supported.')
    keys = read_keys((home or Path.home()) / '.config/langfuse/sns.env')
    if sink_factory is None:
        path = Path(__file__).resolve().parents[1] / 'third_party/gxs-ai-platform-langfuse/sns-langfuse-onboarding/scripts/usage_sink.py'
        spec = importlib.util.spec_from_file_location('sns_usage_sink', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sink_factory = module.UsageSink
    auth = 'Basic ' + base64.b64encode((keys['LANGFUSE_PUBLIC_KEY'] + ':' + keys['LANGFUSE_SECRET_KEY']).encode()).decode()
    sink = sink_factory(keys, user, auth)
    try:
        stamp = time.time_ns()
        sink.publish([dict(agent='codex', session_id=session, kind=kind, name=name,
                           evidence='l3-entrypoint', source_trace_id='', source_span_id='', observed_at_ns=stamp)
                      for kind, name in [('skill', 'shipmate:' + skill), ('plugin', 'shipmate')]])
    finally:
        sink.close()
    return 'recorded'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', required=True, choices=('specify', 'run', 'review'))
    args = parser.parse_args()
    try:
        result = publish(args.skill)
        if result == 'missing-session-or-user':
            print('SNS skill usage unavailable: current native session/user identity missing.')
    except Exception:
        # Telemetry failure is never an execution gate; do not log secrets or bodies.
        print('SNS skill usage upload incomplete; continue the task and verify tracking separately.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
