import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createReporter, readCredentials } from './metadata.mjs';
import { mkdtempSync, writeFileSync, chmodSync, symlinkSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import omp from './omp.mjs';
import { setupOpenCode } from './opencode.mjs';
import { createHash } from 'node:crypto';

function fixture(client = 'omp', response = { ok: true, json: async () => ({}) }) {
  const uploads = [], warnings = [];
  const reporter = createReporter(client, {
    env: { SNS_LANGFUSE_CLIENT: client, SNS_LANGFUSE_USER_ID: 'test.engineer' },
    credentials: () => ({ LANGFUSE_PUBLIC_KEY: 'pk-lf-test-only', LANGFUSE_SECRET_KEY: 'sk-lf-test-only' }),
    fetch: async (url, request) => { uploads.push({ url, ...request }); return response; },
    warn: () => warnings.push('incomplete'),
  });
  return { reporter, uploads, warnings };
}
const sample = { session: 'fresh-session-1', id: 'event-1', kind: 'generation',
  start: 1000, end: 2000, model: 'provider/model', provider: 'provider', input: 10, output: 4 };
const attrs = upload => Object.fromEntries(JSON.parse(upload.body).resourceSpans[0].scopeSpans[0].spans[0]
  .attributes.map(a => [a.key, a.value.stringValue ?? a.value.intValue]));

test('skill sessions match SNS usage v1 contract, not event invocation counts', async () => {
  const { reporter, uploads } = fixture('opencode');
  const r = { kind: 'skill', session: 'new-session', id: 'activation-1', name: 'shipmate:run',
    evidence: 'skill-activated', start: 1000, end: 1000, text: 'PRIVATE-SKILL' };
  reporter.record(r); reporter.record({ ...r, id: 'activation-2', start: 2000, end: 2000 });
  reporter.record({ ...r, session: 'another-session' });
  reporter.record({ ...r, name: '/private/SKILL.md', evidence: 'inventory' });
  await reporter.flush();
  assert.equal(uploads.length, 2);
  const a = attrs(uploads[0]);
  assert.equal(a['langfuse.observation.metadata.sns_usage_version'], '1');
  assert.equal(a['langfuse.observation.metadata.kind'], 'skill');
  assert.equal(a['langfuse.observation.metadata.unit'], 'session');
  assert.equal(a['langfuse.observation.metadata.agent'], 'opencode');
  assert.equal(a['langfuse.observation.type'], 'event');
  const span = JSON.parse(uploads[0].body).resourceSpans[0].scopeSpans[0].spans[0];
  const digest = createHash('sha256').update(JSON.stringify(['sns-session-usage-v1', 'opencode', r.session, 'skill', r.name])).digest('hex');
  assert.equal(span.traceId, digest.slice(0, 32));
  assert.equal(span.spanId, digest.slice(32, 48));
  assert.equal(span.name, r.name);
  assert.equal(span.parentSpanId, undefined);
  assert.ok(!uploads[0].body.includes('PRIVATE-SKILL'));
});

test('OMP successful instruction reads only; never content, paths, inventory or failed reads', async () => {
  const { reporter, uploads } = fixture(), hooks = {};
  omp({ on: (name, fn) => { hooks[name] = fn; } }, reporter);
  hooks.session_start({}, { sessionManager: { getEntries: () => [], getSessionId: () => 'omp-skills' } });
  const read = { toolName: 'read', toolCallId: 'read-1', isError: false, input: { path: 'skill://shipmate/run/SKILL.md' } };
  Object.defineProperty(read, 'content', { get() { throw new Error('instructions read'); } });
  hooks.tool_result(read); hooks.tool_result({ ...read, toolCallId: 'read-2' });
  for (const path of ['/private/SKILL.md', 'skill://foo/references', 'skill://foo/references/design.md', 'skill://foo/../secret'])
    hooks.tool_result({ ...read, input: { path } });
  hooks.tool_result({ ...read, input: { path: 'skill://other' }, isError: true });
  await hooks.agent_end();
  assert.equal(uploads.length, 2);
  assert.equal(attrs(uploads[1])['langfuse.observation.metadata.evidence'], 'skill-instructions-read');
});

test('OpenCode explicit skill activation ignores text and history, deduplicates repeated activation', async () => {
  const { reporter, uploads } = fixture('opencode');
  const d = { sessionID: 'oc-skills', id: 'skill-1', name: 'shipmate:run',
    get text() { throw new Error('skill content read'); } };
  const event = { type: 'session.skill.activated', created: 1000, data: d };
  const events = [event, { type: 'session.created', created: 900, data: { sessionID: d.sessionID } }, event, event];
  const dispose = await setupOpenCode({ event: { async *subscribe() { yield* events; } } }, reporter);
  await dispose();
  assert.equal(uploads.length, 2);
  assert.equal(attrs(uploads[1])['langfuse.observation.metadata.evidence'], 'skill-activated');
});

test('credential reader accepts private data only and rejects symlinks/public permissions', () => {
  const directory = mkdtempSync(join(tmpdir(), 'sns-keys-'));
  try {
    const file = join(directory, 'fixture.env');
    writeFileSync(file, 'LANGFUSE_BASE_URL=https://langfuse.stg.dakota.com.sg\n' +
      'LANGFUSE_HOST=https://langfuse.stg.dakota.com.sg\nLANGFUSE_TRACING_ENVIRONMENT=development\n' +
      'LANGFUSE_PUBLIC_KEY=pk-lf-test-only\nLANGFUSE_SECRET_KEY=sk-lf-test-only\n', { mode: 0o600 });
    assert.equal(readCredentials(file).LANGFUSE_TRACING_ENVIRONMENT, 'development');
    chmodSync(file, 0o644); assert.throws(() => readCredentials(file));
    chmodSync(file, 0o600);
    symlinkSync(file, join(directory, 'link')); assert.throws(() => readCredentials(join(directory, 'link')));
  } finally { rmSync(directory, { recursive: true }); }
});

test('ordinary clients are inert and do not read credentials', async () => {
  const reporter = createReporter('omp', { env: {}, credentials: () => { throw new Error('unexpected'); } });
  assert.equal(reporter.active, false);
  reporter.record(sample); await reporter.flush();
  assert.equal(await setupOpenCode({}, { active: false }), undefined);
  omp({ on() { throw new Error('registered without opt-in'); } }, { active: false });
});

test('allowlisted metadata only, stable IDs, real usage and user attribution', async () => {
  const { reporter, uploads } = fixture();
  reporter.record({ ...sample, cost: 0.125, cacheRead: 5, inputText: 'PRIVATE-PROMPT',
    output: 4, result: 'PRIVATE-RESULT', error: 'PRIVATE-ERROR', arbitrary: { secret: 'PRIVATE-KEY' } });
  reporter.record(sample); await reporter.flush();
  assert.equal(uploads.length, 1);
  assert.equal(attrs(uploads[0])['langfuse.user.id'], 'test.engineer');
  assert.equal(attrs(uploads[0])['langfuse.environment'], 'development');
  assert.equal(attrs(uploads[0])['gen_ai.usage.input_tokens'], '10');
  assert.equal(attrs(uploads[0])['langfuse.observation.cost_details'], '{"total":0.125}');
  assert.ok(!uploads[0].body.includes('PRIVATE-'));
  assert.ok(!uploads[0].body.includes('sk-lf-'));
  assert.equal(uploads[0].redirect, 'error');
  assert.equal(uploads[0].url, 'https://langfuse.stg.dakota.com.sg/api/public/otel/v1/traces');
});

test('unknown tokens/cost remain absent, not zero; malformed records are skipped', async () => {
  const { reporter, uploads } = fixture();
  reporter.record({ ...sample, input: undefined, output: NaN, cost: undefined });
  reporter.record({ ...sample, id: 'invalid', end: -1 });
  reporter.record({ ...sample, id: 'invalid2', session: 'line\nbreak' });
  await reporter.flush();
  assert.equal(uploads.length, 1);
  assert.equal(attrs(uploads[0])['gen_ai.usage.input_tokens'], undefined);
  assert.equal(attrs(uploads[0])['langfuse.observation.cost_details'], undefined);
});

test('failed uploads and OTLP partial rejection are advisory, with no error-body logging', async () => {
  for (const response of [{ ok: false }, { ok: true, json: async () => ({ partialSuccess: { rejectedSpans: 1 } }) }]) {
    const { reporter, warnings } = fixture('omp', response);
    reporter.record(sample); await reporter.flush();
    assert.deepEqual(warnings, ['incomplete']);
  }
});

test('zero cost does not claim free usage and thrown transport errors never escape', async () => {
  const { reporter, uploads } = fixture();
  reporter.record({ ...sample, cost: 0 }); await reporter.flush();
  assert.equal(attrs(uploads[0])['langfuse.observation.cost_details'], undefined);
  const warnings = [];
  const broken = createReporter('omp', { env: { SNS_LANGFUSE_CLIENT: 'omp', SNS_LANGFUSE_USER_ID: 'engineer' },
    credentials: () => { throw new Error('PRIVATE-CREDENTIAL'); }, warn: () => warnings.push('incomplete') });
  broken.record(sample); await broken.flush();
  assert.deepEqual(warnings, ['incomplete']);
});

test('in-flight uploads are bounded and overflow reports incomplete coverage', async () => {
  const { reporter, warnings, uploads } = fixture();
  for (let i = 0; i < 25; i++) reporter.record({ ...sample, id: 'event-' + i });
  await reporter.flush();
  assert.equal(uploads.length, 20);
  assert.deepEqual(warnings, ['incomplete']);
});

test('OMP hooks capture assistant/tool metadata, ignore history and stop on resume', async () => {
  const { reporter, uploads } = fixture(), hooks = {};
  omp({ on: (name, fn) => { hooks[name] = fn; } }, reporter);
  const ctx = { sessionManager: { getEntries: () => [], getSessionId: () => 'omp-session' } };
  hooks.session_start({}, ctx);
  const message = { role: 'assistant', timestamp: Date.now(), model: 'model', provider: 'provider',
    usage: { input: 5, output: 6 }, get content() { throw new Error('content read'); } };
  hooks.message_end({ message });
  hooks.tool_execution_start({ toolCallId: 'call-1' });
  hooks.tool_execution_end({ toolCallId: 'call-1', toolName: 'read', isError: true,
    get result() { throw new Error('result read'); } });
  await hooks.agent_end();
  assert.equal(uploads.length, 3);
  hooks.session_switch({ reason: 'resume' }, ctx);
  hooks.message_end({ message }); await hooks.agent_end();
  assert.equal(uploads.length, 3);
  hooks.session_start({}, { sessionManager: { ...ctx.sessionManager, getEntries: () => [{ type: 'message' }] } });
  hooks.message_end({ message }); await hooks.session_shutdown();
  assert.equal(uploads.length, 3);
});

test('OpenCode v2 consumes only fresh events and never reads content/error/input', async () => {
  const { reporter, uploads } = fixture('opencode');
  const base = { sessionID: 'oc-session', assistantMessageID: 'message-1' };
  const ended = { type: 'session.step.ended', created: 2000, data: { ...base, tokens: { input: 3, output: 4 }, cost: 0.1,
    get content() { throw new Error('content read'); } } };
  const events = [ended,
    { type: 'session.created', created: 900, data: { sessionID: base.sessionID } },
    { type: 'session.step.started', created: 1000, data: { ...base, started: 1000, model: { id: 'model', providerID: 'provider' } } },
    ended, ended,
    { type: 'session.tool.input.started', created: 2100, data: { ...base, id: 'call-1', name: 'read' } },
    { type: 'session.tool.called', created: 2200, data: { ...base, id: 'call-1', get input() { throw new Error('input read'); } } },
    { type: 'session.tool.failed', created: 2300, data: { ...base, id: 'call-1', get error() { throw new Error('error read'); } } },
  ];
  const dispose = await setupOpenCode({ event: { async *subscribe() { yield* events; } } }, reporter);
  await dispose();
  assert.equal(uploads.length, 3);
  assert.equal(attrs(uploads[1])['langfuse.observation.type'], 'generation');
  assert.equal(attrs(uploads[2])['langfuse.observation.type'], 'tool');
});

test('OpenCode v2 flushes pending uploads on execution completion and location shutdown', async () => {
  let flushes = 0;
  const reporter = { active: true, record() {}, async flush() { flushes++; } };
  const ctx = { event: { async *subscribe() {
    yield { type: 'session.created', created: 1, data: { sessionID: 'fresh-flush' } };
    yield { type: 'session.execution.succeeded', created: 2, data: { sessionID: 'fresh-flush' } };
    assert.equal(flushes, 1, 'finish uploads before consuming shutdown');
    yield { type: 'location.shutdown', created: 3, data: {} };
    assert.equal(flushes, 2, 'shutdown drains uploads even without a sessionID');
  } } };
  const dispose = await setupOpenCode(ctx, reporter);
  await dispose();
  assert.equal(flushes, 3);
});

test('OpenCode awaited prompt admission recovers a missed created event and rejects old/child sessions', async () => {
  const records = [];
  let prompt;
  let disposed = false;
  const now = Date.now();
  const headers = {
    fresh: { time: { created: now + 100 } },
    old: { time: { created: now - 10000 } },
    child: { time: { created: now + 100 }, parentID: 'parent' },
  };
  const cleanup = await setupOpenCode({
    event: { async *subscribe() {} },
    session: { async hook(name, handler) { assert.equal(name, 'prompt'); prompt = handler;
      return { async dispose() { disposed = true; } }; },
      async get({ sessionID }) { return headers[sessionID]; },
    },
  }, { active: true, record: r => records.push(r), async flush() {} });
  const event = id => ({ sessionID: id, get prompt() { throw new Error('prompt read'); } });
  await prompt(event('old')); await prompt(event('child')); await prompt(event('fresh')); await prompt(event('fresh'));
  assert.deepEqual(records.map(r => r.session), ['fresh']);
  await cleanup(); assert.equal(disposed, true);
});
