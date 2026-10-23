// Shared, dependency-free OTLP exporter. Never serialize incoming client events.
import { createHash } from 'node:crypto';
import { lstatSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const BASE = 'https://langfuse.stg.dakota.com.sg';
const identifier = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:@/+\-]{0,199}$/.test(value);
const number = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const hash = (value, length) => createHash('sha256').update(value).digest('hex').slice(0, length);

export function readCredentials(path = join(homedir(), '.config/langfuse/sns.env')) {
  const info = lstatSync(path);
  if (!info.isFile() || info.isSymbolicLink() || info.uid !== process.getuid() || (info.mode & 0o077))
    throw new Error('SNS credential file must be owner-only and not a symlink');
  const values = {};
  for (const line of readFileSync(path, 'utf8').split(/\r?\n/)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    const split = line.indexOf('=');
    if (split < 1) throw new Error('Invalid SNS credential file');
    const key = line.slice(0, split).trim();
    let value = line.slice(split + 1).trim();
    if (Object.hasOwn(values, key)) throw new Error('Duplicate SNS setting');
    if (value.startsWith('"') || value.startsWith("'")) {
      if (value.at(-1) !== value[0]) throw new Error('Invalid SNS setting');
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  if (values.LANGFUSE_BASE_URL !== BASE || values.LANGFUSE_HOST !== BASE ||
      values.LANGFUSE_TRACING_ENVIRONMENT !== 'development' ||
      !/^pk-lf-\S+$/.test(values.LANGFUSE_PUBLIC_KEY ?? '') ||
      !/^sk-lf-\S+$/.test(values.LANGFUSE_SECRET_KEY ?? '')) throw new Error('Invalid SNS setup');
  return values;
}

export function createReporter(client, options = {}) {
  const env = options.env ?? process.env;
  const user = env.SNS_LANGFUSE_USER_ID;
  const active = env.SNS_LANGFUSE_CLIENT === client && identifier(user);
  const send = options.fetch ?? globalThis.fetch;
  const load = options.credentials ?? readCredentials;
  const warn = options.warn ?? (() => console.error('SNS metadata upload incomplete; verify tracking separately.'));
  const jobs = new Set();
  let warned = false;
  // Bounded deduplication for replayed client events; no transcripts or disk receipts.
  const seen = new Set();
  function incomplete() { if (!warned) { warned = true; warn(); } }
  function record(r) {
    if (!active || !identifier(r.session) || !identifier(r.id) ||
        !['session', 'generation', 'tool', 'skill'].includes(r.kind) ||
        !number(r.start) || !number(r.end) || r.end < r.start) return;
    if (r.kind === 'skill' && (!identifier(r.name) || !['skill-activated', 'skill-instructions-read'].includes(r.evidence))) return;
    const key = `${r.session}:${r.kind}:${r.kind === 'skill' ? r.name : r.id}`;
    if (seen.has(key)) return;
    if (jobs.size >= 20 || seen.size >= 100000) { incomplete(); return; }
    seen.add(key);
    const attrs = {
      'langfuse.user.id': user, 'langfuse.session.id': r.session,
      'langfuse.trace.name': `${client}.session`,
      'langfuse.observation.type': { session: 'span', generation: 'generation', tool: 'tool', skill: 'event' }[r.kind],
      'langfuse.environment': 'development',
      'langfuse.trace.metadata.team': 'SNS',
      'langfuse.observation.metadata.client': client,
      'langfuse.observation.metadata.capture': 'metadata-only',
    };
    if (r.kind === 'generation') {
      if (identifier(r.model)) attrs['gen_ai.request.model'] = r.model;
      if (identifier(r.provider)) attrs['gen_ai.provider.name'] = r.provider;
      for (const [field, attribute] of Object.entries({ input: 'input_tokens', output: 'output_tokens',
        cacheRead: 'cache_read_input_tokens', cacheWrite: 'cache_creation_input_tokens' })) {
        if (Number.isSafeInteger(r[field]) && r[field] >= 0) attrs[`gen_ai.usage.${attribute}`] = r[field];
      }
      // Client-reported USD only. A zero may mean missing pricing; omit it rather
      // than claiming free usage. No rate-card estimates are made here.
      if (number(r.cost) && r.cost > 0) attrs['langfuse.observation.cost_details'] = JSON.stringify({ total: r.cost });
    }
    if (r.kind === 'tool' && identifier(r.tool)) attrs['gen_ai.tool.name'] = r.tool;
    const usageIdentity = JSON.stringify(['sns-session-usage-v1', client, r.session, 'skill', r.name]);
    const digest = hash(usageIdentity, 64);
    const traceId = r.kind === 'skill' ? digest.slice(0, 32) : hash(`${client}:${r.session}`, 32);
    if (r.kind === 'skill') Object.assign(attrs, {
      'user.id': user, 'langfuse.trace.name': 'SNS skill usage',
      'langfuse.observation.metadata.sns_usage_version': '1',
      'langfuse.observation.metadata.kind': 'skill',
      'langfuse.observation.metadata.unit': 'session',
      'langfuse.observation.metadata.agent': client,
      'langfuse.observation.metadata.evidence': r.evidence,
      'langfuse.observation.metadata.source_trace_id': hash(`${client}:${r.session}`, 32),
      'langfuse.observation.metadata.source_span_id': hash(`${r.session}:session:${r.session}`, 16),
    });
    const span = {
      traceId, spanId: r.kind === 'skill' ? digest.slice(32, 48) : hash(key, 16),
      name: r.kind === 'skill' ? r.name : `${client}.${r.kind}`, kind: 1,
      startTimeUnixNano: String(BigInt(Math.trunc(r.start)) * 1000000n),
      endTimeUnixNano: String(BigInt(Math.trunc(r.end)) * 1000000n + (r.kind === 'skill' ? 1n : 0n)),
      attributes: Object.entries(attrs).map(([key, value]) => ({ key, value:
        typeof value === 'number' ? { intValue: String(value) } : { stringValue: value } })),
      status: { code: r.failed === true ? 2 : 1 },
    };
    if (!['session', 'skill'].includes(r.kind)) span.parentSpanId = hash(`${r.session}:session:${r.session}`, 16);
    const body = JSON.stringify({ resourceSpans: [{ resource: { attributes: [
      { key: 'service.name', value: { stringValue: `sns-${client}` } },
    ] }, scopeSpans: [{ scope: { name: 'sns-metadata', version: '1' }, spans: [span] }] }] });
    const job = Promise.resolve().then(async () => {
      const keys = load();
      const auth = Buffer.from(`${keys.LANGFUSE_PUBLIC_KEY}:${keys.LANGFUSE_SECRET_KEY}`).toString('base64');
      const response = await send(`${BASE}/api/public/otel/v1/traces`, {
        method: 'POST', redirect: 'error', signal: AbortSignal.timeout(5000),
        headers: { Authorization: `Basic ${auth}`, 'Content-Type': 'application/json', 'x-langfuse-ingestion-version': '4' }, body,
      });
      if (!response.ok) throw new Error('Upload failed');
      // HTTP 200 can still contain OTLP partialSuccess; never report that as complete.
      const result = await response.json();
      if (Number(result.partialSuccess?.rejectedSpans ?? 0) > 0) throw new Error('Upload incomplete');
    }).catch(incomplete).finally(() => { jobs.delete(job); });
    jobs.add(job);
  }
  return { active, record, flush: () => Promise.all([...jobs]) };
}
