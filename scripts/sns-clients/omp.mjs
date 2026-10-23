import { createReporter } from './metadata.mjs';

// OMP 18.11.0 ExtensionAPI. Explicit -e loading; not a native-OTLP replacement.
export default function snsOMP(pi, reporter = createReporter('omp')) {
  if (!reporter.active) return;
  let session;
  const tools = new Map(), messages = new WeakMap();
  function start(ctx) {
    session = undefined; tools.clear();
    // Never read/export historical messages. Only the entry types are inspected.
    if (ctx.sessionManager.getEntries().some(entry => entry.type === 'message')) return;
    session = ctx.sessionManager.getSessionId();
    const now = Date.now();
    reporter.record({ kind: 'session', session, id: session, start: now, end: now });
  }
  pi.on('session_start', (_event, ctx) => start(ctx));
  pi.on('session_switch', (event, ctx) => { session = undefined; if (event.reason === 'new') start(ctx); });
  pi.on('session_before_branch', () => { session = undefined; });
  pi.on('tool_result', event => {
    if (!session || event.toolName !== 'read' || event.isError !== false) return;
    // Inspect only the resource identifier locally, never the returned instructions.
    // Restrict evidence to explicit instruction URIs, not arbitrary file paths.
    const path = event.input?.path;
    if (typeof path !== 'string' || (!path.endsWith('/SKILL.md') && path.slice('skill://'.length).includes('/'))) return;
    const uri = typeof path === 'string' ? path.replace(/\/SKILL\.md$/, '') : '';
    const match = /^skill:\/\/([A-Za-z0-9][A-Za-z0-9._:@+\-]*(?:\/[A-Za-z0-9][A-Za-z0-9._:@+\-]*)?)$/.exec(uri);
    if (!match) return;
    const now = Date.now();
    reporter.record({ kind: 'skill', session, id: event.toolCallId, name: match[1],
      evidence: 'skill-instructions-read', start: now, end: now });
  });
  pi.on('message_start', event => { if (event.message?.role === 'assistant') messages.set(event.message, Date.now()); });
  pi.on('message_end', event => {
    const m = event.message;
    if (!session || m?.role !== 'assistant' || typeof m.timestamp !== 'number') return;
    // Detached message_end snapshots may not share message_start identity. In that
    // case use the client's message timestamp, not an invented request start.
    const end = Date.now(), start = messages.get(m) ?? m.timestamp;
    reporter.record({ kind: 'generation', session, id: m.responseId ?? String(m.timestamp),
      start, end, model: m.model, provider: m.provider,
      input: m.usage?.input, output: m.usage?.output,
      cacheRead: m.usage?.cacheRead, cacheWrite: m.usage?.cacheWrite,
      cost: m.usage?.cost?.total, failed: ['error', 'aborted'].includes(m.stopReason) });
  });
  pi.on('tool_execution_start', event => { if (session && tools.size < 1000) tools.set(event.toolCallId, Date.now()); });
  pi.on('tool_execution_end', event => {
    const start = tools.get(event.toolCallId); tools.delete(event.toolCallId);
    if (!session || start === undefined) return;
    reporter.record({ kind: 'tool', session, id: event.toolCallId, tool: event.toolName,
      start, end: Date.now(), failed: event.isError });
  });
  pi.on('agent_end', () => reporter.flush());
  pi.on('session_shutdown', () => reporter.flush());
}
