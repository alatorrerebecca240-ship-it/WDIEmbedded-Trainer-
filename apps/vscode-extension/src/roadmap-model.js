// Pure data model. No Python process, question execution, network or VS Code API.
const BAD_KEYS = new Set(['__proto__', 'prototype', 'constructor']);
const validId = (value) => typeof value === 'string' && /^[a-z][a-z0-9.-]{0,119}$/.test(value) && !BAD_KEYS.has(value);
function text(value, max = 6000) { return typeof value === 'string' && value.trim().length > 0 && value.length <= max; }

function validateRoute(route) {
  if (!route || route.formatVersion !== 1 || !validId(route.id) || !/^\d+\.\d+\.\d+$/.test(route.version || '')
    || !text(route.title, 120) || !text(route.description, 1200)
    || !Array.isArray(route.stages) || !route.stages.length || route.stages.length > 30) throw new Error('路线文件格式不正确。');
  const stages = new Set(), questions = new Set();
  for (const stage of route.stages) {
    if (!stage || !validId(stage.id) || stages.has(stage.id) || !text(stage.title, 120)
      || !['summary', 'example', 'predict', 'checkpoint', 'projectStep'].every((k) => text(stage[k]))
      || !Number.isInteger(stage.minutes) || stage.minutes < 1 || stage.minutes > 1440
      || !Array.isArray(stage.concepts) || !stage.concepts.length || stage.concepts.length > 10 || !stage.concepts.every((v) => text(v))
      || !Array.isArray(stage.required) || !stage.required.length || !Array.isArray(stage.optional)
      || stage.required.length + stage.optional.length > 100) throw new Error('路线阶段格式不正确。');
    stages.add(stage.id);
    for (const id of [...stage.required, ...stage.optional]) {
      if (!validId(id) || questions.has(id)) throw new Error('路线包含重复或无效的题目 ID：' + id);
      questions.add(id);
    }
  }
  return route;
}

function buildRoadmap(route, lessons, progress = {}, notebook = {}) {
  validateRoute(route);
  const byId = new Map(lessons.map((lesson) => [lesson.id, lesson]));
  const state = notebook.routes?.[route.id] || {};
  const row = (id) => {
    const lesson = byId.get(id), result = progress[id] || {};
    return { id, title: lesson?.title || id, type: lesson?.questionType || '', missing: !lesson,
      needsTrust: Boolean(lesson?.needsTrust), status: lesson ? result.status || 'not-started' : 'missing',
      attempts: Number.isSafeInteger(result.attempts) && result.attempts > 0 ? result.attempts : 0 };
  };
  const stages = route.stages.map((stage) => {
    const required = stage.required.map(row), optional = stage.optional.map(row);
    const record = state.stages?.[stage.id] || {};
    const passed = required.filter((q) => q.status === 'passed').length;
    const selfChecked = record.routeVersion === route.version && record.confirmed === true && text(record.reflection, 6000);
    return { ...stage, required, optional, passed, selfChecked, reflection: record.reflection || '',
      complete: passed === required.length && selfChecked, missing: required.filter((q) => q.missing).length };
  });
  const required = stages.flatMap((s) => s.required), optional = stages.flatMap((s) => s.optional);
  const last = required.find((q) => q.id === state.lastLessonId && !q.missing && q.status !== 'passed');
  const next = last || required.find((q) => !q.missing && q.status !== 'passed');
  return { ...route, stages, requiredCount: required.length, optionalCount: optional.length,
    passed: required.filter((q) => q.status === 'passed').length, missing: required.filter((q) => q.missing).length,
    completedStages: stages.filter((s) => s.complete).length, next,
    review: required.filter((q) => !q.missing && q.status !== 'passed' && q.attempts > 0) };
}

function buildReport(model, now = new Date()) {
  return { formatVersion: 1, generatedAt: now.toISOString(),
    route: { id: model.id, version: model.version, title: model.title },
    privacy: '仅本地导出；不自动收集源代码、绝对路径或账号信息。报告包含自己填写的记录，分享前请检查。自查不代表带教验收。',
    summary: { required: model.requiredCount, passed: model.passed, missing: model.missing,
      optional: model.optionalCount, selfCheckedStages: model.stages.filter((s) => s.selfChecked).length },
    stages: model.stages.map((s) => ({ id: s.id, title: s.title, passed: s.passed, required: s.required.length,
      selfChecked: s.selfChecked, reflection: s.reflection, mentorReview: 'not-recorded',
      questions: [...s.required.map((q) => ({ ...q, required: true })), ...s.optional.map((q) => ({ ...q, required: false }))] })) };
}

function markdownReport(report) {
  const safe = (value) => String(value).replace(/[<>]/g, (c) => c === '<' ? '&lt;' : '&gt;').replace(/([\\`*_[\]#|])/g, '\\$1');
  return [`# ${safe(report.route.title)} · 学习报告`, '', `生成时间：${report.generatedAt}`, '', report.privacy,
    '', `必做题通过：${report.summary.passed}/${report.summary.required}；缺少题目：${report.summary.missing}。`,
    ...report.stages.flatMap((stage) => ['', `## ${safe(stage.title)}`, '',
      `练习通过 ${stage.passed}/${stage.required}；学习者自查：${stage.selfChecked ? '已记录' : '未完成'}；带教验收：未记录。`,
      '', '### 学习者记录', '', safe(stage.reflection || '尚未填写'), '', '### 题目明细', '',
      ...stage.questions.map((q) => `- ${q.required ? '必做' : '选做'} · ${safe(q.title)} (${q.id}) · ${q.status} · ${q.attempts} 次提交`)]), ''].join('\n');
}
module.exports = { validateRoute, buildRoadmap, buildReport, markdownReport, validId };
