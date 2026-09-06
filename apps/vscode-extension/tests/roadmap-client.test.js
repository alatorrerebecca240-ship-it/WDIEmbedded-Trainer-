const assert = require('node:assert/strict');
const { test } = require('node:test');
const vm = require('node:vm');
const { roadmapClient } = require('../src/roadmap-client');

function fixture(saved) {
  const node = (more = {}) => ({ dataset: {}, listeners: {}, addEventListener(k, fn) { this.listeners[k] = fn; }, ...more });
  const note = node({ value: 'server note' }), check = node({ checked: false });
  const form = node({ dataset: { stageForm: 'first' }, querySelector: (s) => s === 'textarea' ? note : check, reportValidity: () => true });
  const lesson = node({ dataset: { command: 'lesson', lessonId: 'fixture.one' } });
  const absent = node({ dataset: { command: 'lesson', lessonId: 'missing', unavailable: 'true' }, disabled: true });
  const jump = node({ dataset: { stageTarget: 'stage-last' } });
  const details = [node({ id: 'stage-first', open: true }), node({ id: 'stage-last', open: false, scrollIntoView() { this.scrolled = true; } })];
  const status = { textContent: '' }, messages = [];
  const controls = [note, check, lesson, absent, jump];
  let state = saved;
  const document = { body: { dataset: { viewId: 'view', routeKey: 'fixture@1.0.0' }, setAttribute() {} },
    getElementById: (id) => id === 'camp-status' ? status : details.find((d) => d.id === id),
    querySelectorAll: (selector) => ({ 'button, textarea, input': controls, '[data-stage-form]': [form],
      '[data-command]': [lesson, absent], '[data-stage-target]': [jump], details,
      'details[open]': details.filter((d) => d.open) })[selector] || [] };
  const window = node({ scrollY: 0, scrollTo(_, y) { this.scrollY = y; } });
  vm.runInNewContext(`(${roadmapClient.toString()})();`, { document, window,
    requestAnimationFrame: (fn) => fn(), acquireVsCodeApi: () => ({ getState: () => saved,
      setState: (v) => { state = JSON.parse(JSON.stringify(v)); }, postMessage: (v) => messages.push(JSON.parse(JSON.stringify(v))) }) });
  return { note, check, form, lesson, absent, jump, details, window, messages, state: () => state,
    receive: (data) => window.listeners.message({ data }) };
}

test('roadmap restores unsaved notes and opened stages after a document refresh', () => {
  const first = fixture();
  first.note.value = 'not yet saved'; first.check.checked = true; first.form.listeners.input();
  first.jump.listeners.click();
  assert.equal(first.details[1].open, true); assert.equal(first.details[1].scrolled, true);
  first.window.scrollY = 250; first.window.listeners.scroll();
  const restored = fixture(first.state());
  assert.equal(restored.note.value, 'not yet saved'); assert.equal(restored.check.checked, true);
  assert.equal(restored.details[1].open, true); assert.equal(restored.window.scrollY, 250);
  const otherRoute = fixture({ ...first.state(), routeKey: 'other@1.0.0' });
  assert.equal(otherRoute.note.value, 'server note');
});

test('roadmap forms send typed values, prevent duplicate clicks and retain disabled missing questions', () => {
  const client = fixture();
  client.note.value = 'my explanation'; client.check.checked = true; client.form.listeners.input();
  client.form.listeners.submit({ preventDefault() {} });
  assert.deepEqual(client.messages.at(-1), { command: 'save', viewId: 'view', stageId: 'first', reflection: 'my explanation', confirmed: true });
  const count = client.messages.length;
  client.lesson.listeners.click(); assert.equal(client.messages.length, count);
  client.receive({ command: 'busy', busy: false });
  assert.equal(client.absent.disabled, true); assert.equal(client.lesson.disabled, false);
  client.receive({ command: 'saved', stageId: 'first' });
  assert.equal(client.state().drafts.first, undefined);
});
