const assert = require('node:assert/strict');
const Module = require('node:module');
const { test, beforeEach } = require('node:test');
let calls, messages, picks, consent, state, cloudCalls;
const vscode = {
  Uri: { file: (fsPath) => ({ fsPath }) }, ProgressLocation: { Notification: 1 },
  workspace: { workspaceFolders: [{}], fs: { stat: async () => {} } },
  window: {
    withProgress: async (_, run) => run({}, { isCancellationRequested: false }),
    showQuickPick: async (items) => { const pick = picks.shift(); return pick ? pick(items) : undefined; },
    showInputBox: async () => 'fixture-reviewer',
    showWarningMessage: async (s, options, button) => { messages.push(s); return options?.modal && consent ? button : undefined; },
    showInformationMessage: async (s) => messages.push(s), showErrorMessage: async (s) => messages.push(s)
  }
};
const original = Module._load;
let AuthoringManager;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : original.call(this, name, ...args); };
  ({ AuthoringManager } = require('../src/authoring'));
} finally { Module._load = original; }
beforeEach(() => { calls = []; messages = []; picks = []; consent = true; state = {}; cloudCalls = 0; });
function manager(results) {
  const context = { extensionUri: { fsPath: '/extension' }, workspaceState: {
    get: (k, value) => state[k] ?? value, update: async (k, v) => { state[k] = v; }
  } };
  const backend = { rootUri: { fsPath: '/workspace' }, run: async (args) => {
    calls.push(args); return { code: 0, stdout: JSON.stringify(results) };
  } };
  const m = new AuthoringManager(context, backend);
  m.cloud.dispatch = async () => { cloudCalls++; };
  m.cloud.poll = async () => {};
  return m;
}
test('get-new needs no selection dialogs and automatically offers cloud validation', async () => {
  const m = manager({ added: 2, adopted: 32, failed: 1, warnings: [], counts: { pending: 34 } });
  await m.getNew();
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].slice(0, 2), ['packs', 'inbox-get']);
  assert.equal(cloudCalls, 1);
  assert.equal(m.busy, false);
  assert.ok(messages[0].includes('失败 1'));
});
test('empty/newly deferred queue does not trigger cloud', async () => {
  await manager({ added: 0, adopted: 0, failed: 0, warnings: [], counts: {} }).getNew();
  assert.equal(cloudCalls, 0);
});
test('batch approval sends both explicit acknowledgements, never native/publish/trust', async () => {
  const m = manager({ completed: ['fixture'], failed: [] });
  picks = [(items) => { assert.ok(items.every((v) => !v.picked)); return items; }];
  await m.approveInbox([{ id: 'fixture', title: 'Fixture', key: 'c/fixture', status: 'ready' }]);
  assert.ok(calls[0].includes('--ack-content') && calls[0].includes('--ack-copyright'));
  for (const command of ['native', 'publish-bundle', 'trust', 'inbox-stage']) assert.ok(!calls[0].includes(command));
});
test('declining human review leaves the queue unapproved', async () => {
  consent = false; picks = [(items) => items];
  await manager({}).approveInbox([{ id: 'fixture', title: 'Fixture', key: 'c/fixture' }]);
  assert.equal(calls.length, 0);
});
test('central review exposes counts and requires separate publication preparation confirmation', async () => {
  const m = manager({ total: 3, items: [{ status: 'ready' }], counts: { ready: 1, checking: 2 } });
  picks = [(items) => items.find((v) => v.action === 'stage')];
  consent = false;
  await m.reviewInbox();
  assert.deepEqual(calls.map((v) => v[1]), ['inbox-list']);
  assert.equal(m.busy, false);
});
