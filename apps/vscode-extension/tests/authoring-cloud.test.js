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

function create(transport) {
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
  });
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
