const assert = require('node:assert/strict');
const { test } = require('node:test');
const { setTimeout: pause } = require('node:timers/promises');
const { RefreshQueue } = require('../src/refresh');

test('watcher burst coalesces; full dominates progress', async () => {
  const calls = [];
  const queue = new RefreshQueue(async (kind) => calls.push(kind), assert.fail, 5);
  for (let i = 0; i < 20; i++) queue.schedule('progress');
  queue.schedule('full');
  queue.schedule('progress');
  await pause(30);
  assert.deepEqual(calls, ['full']);
  queue.dispose();
});

test('event during in-flight refresh replays without concurrent loads', async () => {
  const calls = [];
  let release;
  const queue = new RefreshQueue(async (kind) => {
    calls.push(kind);
    if (calls.length === 1) await new Promise((resolve) => { release = resolve; });
  }, assert.fail);
  const first = queue.request('progress');
  await Promise.resolve();
  const second = queue.request('full');
  queue.request('progress');
  assert.deepEqual(calls, ['progress']);
  release();
  await Promise.all([first, second]);
  assert.deepEqual(calls, ['progress', 'full']);
  queue.dispose();
});

test('explicit refresh consumes pending watcher event; disposal cancels timer', async () => {
  const calls = [];
  const queue = new RefreshQueue(async (kind) => calls.push(kind), assert.fail, 5);
  queue.schedule('progress');
  await queue.request('progress');
  await pause(20);
  assert.deepEqual(calls, ['progress']);
  queue.schedule('full');
  queue.dispose();
  await pause(20);
  assert.deepEqual(calls, ['progress']);
});

test('a failed refresh does not poison future requests', async () => {
  let count = 0;
  const queue = new RefreshQueue(async () => { if (++count === 1) throw new Error('invalid pack'); }, assert.fail);
  await assert.rejects(queue.request(), /invalid pack/);
  await queue.request();
  assert.equal(count, 2);
  queue.dispose();
});
