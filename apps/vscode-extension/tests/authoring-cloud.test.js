const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const Module = require('node:module');
const { test, beforeEach } = require('node:test');
let notices, requests, commands, writes, state, authCalls;
const token = 'fixture-private-token';
const sha = 'a'.repeat(40);
const repo = 'alatorrerebecca240-ship-it/WDIEmbedded-Trainer-';
const uri = (fsPath) => ({ fsPath });
const vscode = {
  Uri: { file: uri },
  workspace: { getConfiguration: () => ({ get: (_, value) => value }), fs: {
    createDirectory: async () => {}, writeFile: async (file, data) => writes.push({ file, data })
  } },
  authentication: { getSession: async (...args) => { authCalls.push(args); return { accessToken: token }; } },
  window: {
    showWarningMessage: async (message, options) => { notices.push(message); return options?.modal ? '允许云端验证' : undefined; },
    showInformationMessage: async (message) => { notices.push(message); }
  },
  commands: { executeCommand: async () => {} }
};
let AuthoringCloud, requestRaw, repository, WORKFLOW_PATH;
const original = Module._load;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : original.call(this, name, ...args); };
  ({ AuthoringCloud, requestRaw, repository, WORKFLOW_PATH } = require('../src/authoring-cloud'));
} finally { Module._load = original; }
beforeEach(() => { notices = []; requests = []; commands = []; writes = []; state = {}; authCalls = []; });
const response = (value, status = 200, headers = {}) => ({ status, headers, body: Buffer.from(value === null ? '' : JSON.stringify(value)) });

function create(transport, timers) {
  const context = { globalStorageUri: uri('/private-extension-storage'), subscriptions: [], workspaceState: { get: (k, fallback) => state[k] ?? fallback, update: async (k, v) => { state[k] = v; } } };
  const backend = { rootUri: uri('/workspace'), run: async (args) => {
    commands.push(args);
    const value = args[1] === 'inbox-plan' ? { pipelineVersion: 1, requestId: args[3], entries: [{ id: 'fixture', contentSha256: 'b'.repeat(64) }] }
      : { counts: { ready: 1, 'validation-failed': 1 } };
    return { code: 0, stdout: JSON.stringify(value) };
  } };
  const cloud = new AuthoringCloud(context, backend, async (url, options) => {
    requests.push({ url, options });
    return transport(url, options);
  }, timers);
  return cloud;
}
function dispatchTransport(url, options) {
  if (url.endsWith('/dispatches')) return response({ workflow_run_id: 42 });
  if (url.endsWith('/commits/main')) return response({ sha });
  return response({ id: 7, path: WORKFLOW_PATH, state: 'active' });
}
function runFor(job, changes = {}) {
  return { id: 42, head_sha: sha, path: WORKFLOW_PATH, workflow_id: 7, event: 'workflow_dispatch',
    display_title: `trainer-review-${job.requestId}`, head_repository: { full_name: repo }, status: 'completed', conclusion: 'success', ...changes };
}

test('one dispatch sends public plan only and never persists credentials or publishes', async () => {
  const cloud = create(dispatchTransport);
  await cloud.dispatch();
  const posts = requests.filter((v) => v.options.method === 'POST');
  assert.equal(posts.length, 1);
  assert.equal(posts[0].options.body.ref, 'main');
  assert.equal(authCalls[0][0], 'github');
  assert.deepEqual(authCalls[0][1], ['repo']);
  assert.ok(!JSON.stringify(state).includes(token));
  assert.ok(!JSON.stringify(commands).includes(token));
  assert.ok(!JSON.stringify(posts[0].options.body).includes('/workspace'));
  assert.equal(cloud.jobs()[0].runId, 42);
  assert.ok(!requests.some((v) => /releases|git\/refs/.test(v.url)));
});

test('missing workflow leaves drafts alone and does not queue or blindly dispatch', async () => {
  const cloud = create(() => response({}, 404));
  await assert.rejects(cloud.dispatch(), /尚未部署/);
  assert.equal(commands.length, 0);
  assert.equal(cloud.jobs().length, 0);
  assert.equal(cloud.busy, false);
});

test('ambiguous POST failure is saved for reconciliation, never automatically reposted', async () => {
  const cloud = create((url, options) => {
    if (url.endsWith('/dispatches')) throw new Error('response lost');
    return dispatchTransport(url, options);
  });
  await assert.rejects(cloud.dispatch(), /response lost/);
  assert.equal(cloud.jobs().length, 1);
  assert.equal(cloud.jobs()[0].done, false);
  assert.ok(!commands.some((v) => v[1] === 'inbox-fail'));
});

test('artifact is bound to run, verified by SHA and downloaded without forwarding token', async () => {
  const cloud = create(dispatchTransport);
  await cloud.dispatch();
  const job = cloud.jobs()[0];
  const archive = Buffer.from('synthetic zip bytes: Python validates the real ZIP format');
  const digest = crypto.createHash('sha256').update(archive).digest('hex');
  cloud.transport = async (url, options) => {
    requests.push({ url, options });
    if (url.includes('/artifacts?')) return response({ artifacts: [{ id: 9, name: `trainer-review-${job.requestId}`,
      expired: false, size_in_bytes: archive.length, digest: `sha256:${digest}` }] });
    if (url.endsWith('/artifacts/9/zip')) return response(null, 302, { location: 'https://fixture.blob.core.windows.net/report?sig=fixture' });
    if (url.startsWith('https://fixture.blob.')) { assert.equal(options, undefined); return { status: 200, body: archive }; }
    return response(runFor(job));
  };
  await cloud.pollJob(job, token);
  assert.equal(writes.length, 1);
  assert.ok(writes[0].file.fsPath.includes('private-extension-storage'));
  assert.ok(commands.some((v) => v[1] === 'inbox-results' && v.includes(digest)));
  assert.equal(cloud.jobs()[0].done, true);
  assert.ok(!JSON.stringify(state).includes(token));
});

test('wrong workflow head fails closed without downloading or approving', async () => {
  const cloud = create(dispatchTransport);
  await cloud.dispatch();
  const job = cloud.jobs()[0];
  cloud.transport = async () => response(runFor(job, { head_sha: 'b'.repeat(40) }));
  await cloud.pollJob(job, token);
  assert.equal(writes.length, 0);
  assert.ok(commands.some((v) => v[1] === 'inbox-fail'));
  assert.ok(!commands.some((v) => v[1] === 'inbox-results'));
});

test('queued jobs stay quiet, and timer is disposed on extension shutdown', async () => {
  const cloud = create(dispatchTransport);
  await cloud.dispatch();
  const job = cloud.jobs()[0];
  const before = notices.length;
  cloud.transport = async () => response(runFor(job, { status: 'in_progress', conclusion: null }));
  await cloud.poll(true);
  assert.equal(notices.length, before);
  assert.equal(authCalls.at(-1)[2].silent, true);
  cloud.start();
  cloud.context.subscriptions.forEach((v) => v.dispose());
});

test('transport rejects arbitrary hosts, plaintext and cross-host authorization before network', async () => {
  assert.throws(() => repository('../repo'), /格式/);
  for (const [url, options] of [
    ['http://api.github.com/', {}], ['https://evil.invalid/', {}],
    ['https://fixture.blob.core.windows.net/report', { token }], ['https://api.github.com:8443/', { token }]
  ]) await assert.rejects(requestRaw(url, options), /拒绝/);
});

function fakeTimers() {
  const pending = new Map(); let id = 0;
  return { pending, setTimeout(fn, delay) { pending.set(++id, { fn, delay }); return id; },
    clearTimeout(key) { pending.delete(key); } };
}

test('polls every 15 seconds only while pending and stops on completion or disposal', async () => {
  const timers = fakeTimers();
  const cloud = create(dispatchTransport, timers);
  cloud.start(); cloud.start();
  assert.equal(timers.pending.size, 0);
  assert.equal(cloud.context.subscriptions.length, 1);
  await cloud.dispatch();
  assert.equal(timers.pending.size, 1);
  assert.equal([...timers.pending.values()][0].delay, 15000);
  const job = cloud.jobs()[0];
  cloud.transport = async () => response(runFor(job, { conclusion: 'cancelled' }));
  await cloud.poll(true);
  assert.equal(timers.pending.size, 0);
  assert.equal(cloud.jobs()[0].done, true);
  cloud.context.subscriptions.forEach((v) => v.dispose());
  cloud.transport = dispatchTransport;
  await cloud.dispatch();
  assert.equal(timers.pending.size, 0);
});

test('rate limits back off including manual refresh; success restores normal polling', async () => {
  const timers = fakeTimers();
  const cloud = create(dispatchTransport, timers);
  cloud.start(); await cloud.dispatch();
  let reads = 0;
  cloud.transport = async () => { reads++; return response({}, 429, { 'retry-after': '120' }); };
  await cloud.poll(true);
  assert.ok([...timers.pending.values()][0].delay >= 119000);
  assert.equal(cloud.jobs()[0].done, false);
  await cloud.poll(false);
  assert.equal(reads, 1);
  assert.ok(!commands.some((v) => v[1] === 'inbox-fail'));
  cloud.retryAt = 0;
  cloud.transport = async () => response(runFor(cloud.jobs()[0], { status: 'in_progress' }));
  await cloud.poll(true);
  assert.equal(cloud.failures, 0);
  assert.equal([...timers.pending.values()][0].delay, 15000);
  cloud.context.subscriptions.forEach((v) => v.dispose());
});

test('transient network failures back off without concurrent polls or duplicate dispatches', async () => {
  const timers = fakeTimers();
  const cloud = create(dispatchTransport, timers);
  cloud.start(); await cloud.dispatch();
  cloud.transport = async () => { throw new Error('offline'); };
  await Promise.all([cloud.poll(true), cloud.poll(true)]);
  assert.equal(cloud.failures, 1);
  assert.ok([...timers.pending.values()][0].delay >= 29000);
  assert.equal(requests.filter((v) => v.options.method === 'POST').length, 1);
  cloud.context.subscriptions.forEach((v) => v.dispose());
});
