const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const Module = require('node:module');
const { validateRoute, buildRoadmap, buildReport, markdownReport } = require('../src/roadmap-model');
const { CampStore } = require('../src/camp-store');
const { hintSteps } = require('../src/hints');
const builtin = require('../routes/lab-foundations.json');
const route = () => ({ ...structuredClone(builtin), stages: [{ ...structuredClone(builtin.stages[0]), required: ['fixture.one', 'fixture.two'], optional: ['fixture.extra'] }] });
const lessons = [{ id: 'fixture.one', title: 'First', questionType: 'programming' }, { id: 'fixture.two', title: 'Second' }, { id: 'fixture.extra', title: 'Optional' }];

test('bundled roadmap has 49 required questions; all references resolve to existing questions', async () => {
  validateRoute(builtin);
  const root = path.resolve(__dirname, '../../..');
  const foundation = JSON.parse(await fs.readFile(path.join(root, 'knowledge/packs/foundation.core/questions.json'), 'utf8'));
  const ids = new Set(foundation.questions.map((q) => q.id));
  for (const item of await fs.readdir(path.join(root, 'knowledge/approved'))) {
    if (!item.startsWith('review.exercism.')) continue;
    const pack = JSON.parse(await fs.readFile(path.join(root, 'knowledge/approved', item, 'questions.json'), 'utf8'));
    pack.questions.forEach((q) => ids.add(q.id));
  }
  assert.equal(builtin.stages.flatMap((s) => s.required).length, 49);
  for (const stage of builtin.stages) for (const id of [...stage.required, ...stage.optional]) assert.ok(ids.has(id), id);
});

test('missing questions never count as passed; optional work does not block stages', () => {
  const r = route();
  const progress = { 'fixture.one': { status: 'passed', attempts: 2 }, 'fixture.two': { status: 'passed' } };
  const notebook = { routes: { [r.id]: { stages: { [r.stages[0].id]: { reflection: 'I can explain it.', confirmed: true, routeVersion: r.version } } } } };
  assert.equal(buildRoadmap(r, lessons, progress, notebook).completedStages, 1);
  const missing = buildRoadmap(r, lessons.slice(0, 1), progress, notebook);
  assert.equal(missing.passed, 1); assert.equal(missing.missing, 1); assert.equal(missing.completedStages, 0);
  const changedVersion = buildRoadmap({ ...r, version: '1.1.0' }, lessons, progress, notebook);
  assert.equal(changedVersion.stages[0].reflection, 'I can explain it.');
  assert.equal(changedVersion.stages[0].selfChecked, false);
});

test('continue and review derive from in-memory results; report never includes quiz answers or machine paths', () => {
  const r = route();
  const model = buildRoadmap(r, lessons.map((q) => ({ ...q, manifestPath: '/private/path', quiz: { answer: 'SECRET' } })),
    { 'fixture.two': { status: 'in-progress', attempts: 3 } }, { routes: { [r.id]: { lastLessonId: 'fixture.two', stages: {} } } });
  assert.equal(model.next.id, 'fixture.two'); assert.equal(model.review.length, 1);
  const report = buildReport(model);
  assert.ok(!JSON.stringify(report).includes('/private')); assert.ok(!JSON.stringify(report).includes('SECRET'));
  assert.equal(report.stages[0].mentorReview, 'not-recorded');
  report.stages[0].reflection = '<script>alert(1)</script> [click](command:delete)';
  assert.ok(!markdownReport(report).includes('<script>'));
  assert.ok(!markdownReport(report).includes('[click](command:delete)'));
});

test('route validation rejects duplicates, prototype keys and empty stages', () => {
  for (const mutate of [r => r.stages[0].required.push('fixture.one'), r => r.stages[0].id = '__proto__',
    r => r.stages = [], r => r.stages[0].minutes = -1, r => r.id = 'constructor']) {
    const r = route(); mutate(r); assert.throws(() => validateRoute(r));
  }
});

test('note writes are serialized, preserve old grades, and reject corrupt or unconfirmed empty state', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'trainer-camp-test-'));
  try {
    const store = new CampStore(root), r = route();
    await fs.mkdir(path.join(root, '.trainer'));
    const grades = path.join(root, '.trainer/progress.json');
    await fs.writeFile(grades, '{"old":"unchanged"}');
    await Promise.all([store.remember(r, 'fixture.two'), store.saveReflection(r, r.stages[0].id, 'A useful explanation', true)]);
    const data = await store.read();
    assert.equal(data.routes[r.id].lastLessonId, 'fixture.two');
    assert.equal(data.routes[r.id].stages[r.stages[0].id].confirmed, true);
    assert.equal(await fs.readFile(grades, 'utf8'), '{"old":"unchanged"}');
    await assert.rejects(store.remember(r, 'unknown'));
    await assert.rejects(store.saveReflection(r, r.stages[0].id, '', true));
    await fs.writeFile(store.file, '{broken');
    await assert.rejects(store.saveReflection(r, r.stages[0].id, 'new', false));
    assert.equal(await fs.readFile(store.file, 'utf8'), '{broken');
    await fs.writeFile(store.file + '.lock', 'another process');
    await assert.rejects(store.remember(r, 'fixture.one'), /另一个窗口/);
    assert.equal(await fs.readFile(store.file + '.lock', 'utf8'), 'another process');
  } finally { await fs.rm(root, { recursive: true, force: true }); }
});

test('hint layers retain original hints and do not expose reference answers', () => {
  const steps = hintSteps({ questionType: 'single-choice', hints: ['original hint'], quiz: { answer: 'SECRET' } });
  assert.equal(steps.length, 3); assert.equal(steps[1].text, 'original hint');
  assert.ok(!JSON.stringify(steps).includes('SECRET'));
});

const vscode = { ViewColumn: { Active: 1 }, window: { errors: [], showErrorMessage(e) { this.errors.push(e); } } };
const originalLoad = Module._load;
let renderRoadmap, CampDashboard;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : originalLoad.call(this, name, ...args); };
  ({ renderRoadmap, CampDashboard } = require('../src/roadmap'));
} finally { Module._load = originalLoad; }

test('roadmap escapes all data, uses nonce CSP and accessible responsive controls', () => {
  const r = route(), hostile = '</script><img src=x onerror="attack()">';
  r.title = hostile; r.stages[0].example = hostile; r.stages[0].checkpoint = hostile;
  const model = buildRoadmap(r, [{ ...lessons[0], title: hostile }]);
  model.stages[0].reflection = hostile;
  const html = renderRoadmap(model, 'view-token');
  assert.ok(!html.includes(hostile)); assert.ok(html.includes('&lt;/script&gt;'));
  assert.equal((html.match(/<script /g) || []).length, 1);
  assert.ok(!html.includes('unsafe-inline')); assert.ok(html.includes('data-unavailable="true"'));
  for (const marker of ['aria-live="polite"', 'max-width: 600px', 'vscode-high-contrast', 'prefers-reduced-motion', 'maxlength="6000"']) assert.ok(html.includes(marker));
});

test('roadmap host rejects stale/unknown messages and prevents duplicate writes', async () => {
  let finish, writes = 0;
  const camp = new CampDashboard({}, { fsPath: '/project' }, { get: () => lessons[0] }, async () => {});
  camp.viewId = 'current'; camp.route = route(); camp.refresh = async () => {};
  camp.store = { saveReflection() { writes++; return new Promise((resolve) => { finish = resolve; }); } };
  const posted = [];
  camp.panel = { webview: { postMessage: (m) => posted.push(m) } };
  for (const message of [null, {}, { viewId: 'old', command: 'save' }, { viewId: 'current', command: 'eval' }]) await camp.handleMessage(message);
  assert.equal(writes, 0);
  const pending = camp.handleMessage({ viewId: 'current', command: 'save' });
  await camp.handleMessage({ viewId: 'current', command: 'save' });
  assert.equal(writes, 1);
  finish(); await pending; assert.equal(camp.pending, false);
  assert.equal(posted.at(-1).busy, false);
});
