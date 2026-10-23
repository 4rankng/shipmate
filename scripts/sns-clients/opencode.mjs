import { createReporter } from './metadata.mjs';

// OpenCode 2 Promise plugin contract: id + setup, with a live subscription.
// No session.context queries, historical replay, or conversation transforms.
export async function setupOpenCode(ctx, reporter = createReporter('opencode')) {
  if (!reporter.active) return;
  const sessions = new Set(), steps = new Map(), tools = new Map();
  const launch = Number(process.env.SNS_LANGFUSE_STARTED_AT_MS);
  const started = Number.isFinite(launch) && launch > 0 && launch <= Date.now() ? launch : Date.now();
  function admit(id, time) {
    if (sessions.has(id) || sessions.size >= 1000) return;
    sessions.add(id);
    reporter.record({ kind: 'session', session: id, id, start: time, end: time });
  }
  const controller = new AbortController();
  const consume = (async () => {
    for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
      const d = event.data;
      const time = typeof event.created === 'number' ? event.created : Date.parse(event.created);
      if (event.type === 'location.shutdown') await reporter.flush();
      if (!d) continue;
      if (event.type === 'session.created' && !d.parentID) {
        if (sessions.size >= 1000) continue;
        admit(d.sessionID, time);
      }
      if (!sessions.has(d.sessionID)) continue;
      if (event.type === 'session.skill.activated') reporter.record({ kind: 'skill',
        session: d.sessionID, id: d.id, name: d.name, evidence: 'skill-activated', start: time, end: time });
      const key = `${d.sessionID}:${d.assistantMessageID}`;
      if (event.type === 'session.step.started' && steps.size < 1000)
        steps.set(key, { start: d.started, model: d.model });
      if (['session.step.ended', 'session.step.failed'].includes(event.type)) {
        const step = steps.get(key); steps.delete(key);
        if (step) reporter.record({ kind: 'generation', session: d.sessionID, id: d.assistantMessageID,
          start: step.start, end: time, model: step.model?.id, provider: step.model?.providerID,
          input: d.tokens?.input, output: d.tokens?.output,
          cacheRead: d.tokens?.cache?.read, cacheWrite: d.tokens?.cache?.write,
          cost: d.cost, failed: event.type === 'session.step.failed' });
      }
      const toolKey = `${key}:${d.id}`;
      if (event.type === 'session.tool.input.started' && tools.size < 1000)
        tools.set(toolKey, { name: d.name });
      if (event.type === 'session.tool.called') {
        const tool = tools.get(toolKey); if (tool) tool.start = time;
      }
      if (['session.tool.success', 'session.tool.failed'].includes(event.type)) {
        const tool = tools.get(toolKey); tools.delete(toolKey);
        if (tool?.start !== undefined) reporter.record({ kind: 'tool', session: d.sessionID, id: d.id,
          start: tool.start, end: time, tool: tool.name, failed: event.type === 'session.tool.failed' });
      }
      if (['session.execution.succeeded', 'session.execution.failed', 'session.idle'].includes(event.type))
        await reporter.flush();
    }
  })().catch(() => { if (!controller.signal.aborted) console.error('SNS event subscription ended; coverage is incomplete.'); });
  // Await registration before admitting prompts. The event subscription can miss
  // session.created during startup; read only this live session's header, never context.
  const admission = ctx.session?.hook ? await ctx.session.hook('prompt', async event => {
    if (sessions.has(event.sessionID)) return;
    try {
      const info = await ctx.session.get({ sessionID: event.sessionID });
      if (!info.parentID && typeof info.time?.created === 'number' && info.time.created >= started)
        admit(event.sessionID, info.time.created);
    } catch { console.error('SNS session admission unavailable; coverage is incomplete.'); }
  }) : undefined;
  return async () => {
    await admission?.dispose(); controller.abort(); await consume; await reporter.flush();
  };
}

export default { id: 'sns-langfuse-metadata', setup: ctx => setupOpenCode(ctx) };
