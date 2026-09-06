const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { validId } = require('./roadmap-model');

class CampStore {
  constructor(root) { this.file = path.join(root, '.trainer', 'camp-progress.json'); this.queue = Promise.resolve(); }
  async read() {
    let raw;
    try {
      if ((await fs.stat(this.file)).size > 1024 * 1024) throw new Error('训练营记录过大，请先检查文件。');
      raw = await fs.readFile(this.file, 'utf8');
    } catch (error) { if (error.code === 'ENOENT') return { formatVersion: 1, routes: {} }; throw error; }
    const data = JSON.parse(raw);
    if (data?.formatVersion !== 1 || !data.routes || typeof data.routes !== 'object' || Array.isArray(data.routes)) throw new Error('训练营记录格式损坏；未覆盖原文件。');
    for (const [id, route] of Object.entries(data.routes)) {
      if (!validId(id) || !route || typeof route !== 'object' || Array.isArray(route) || !route.stages || typeof route.stages !== 'object' || Array.isArray(route.stages)) throw new Error('训练营记录格式损坏。');
      for (const [stageId, stage] of Object.entries(route.stages)) {
        if (!validId(stageId) || !stage || typeof stage.reflection !== 'string' || stage.reflection.length > 6000 || typeof stage.confirmed !== 'boolean') throw new Error('阶段自查记录格式损坏。');
      }
    }
    return data;
  }
  update(route, change) {
    const run = this.queue.then(async () => {
      await fs.mkdir(path.dirname(this.file), { recursive: true });
      const lock = this.file + '.lock';
      let handle;
      try { handle = await fs.open(lock, 'wx'); }
      catch (error) { if (error.code === 'EEXIST') throw new Error('另一个窗口正在保存训练营记录，请稍后重试。'); throw error; }
      const temp = this.file + '.' + crypto.randomBytes(8).toString('hex') + '.tmp';
      try {
        const data = await this.read();
        const state = data.routes[route.id] || { stages: {} };
        change(state);
        data.routes[route.id] = state;
        await fs.writeFile(temp, JSON.stringify(data, null, 2) + '\n', { flag: 'wx' });
        await fs.rename(temp, this.file);
        return data;
      } finally { await handle.close(); await fs.unlink(lock); await fs.unlink(temp).catch((e) => { if (e.code !== 'ENOENT') throw e; }); }
    });
    this.queue = run.catch(() => {});
    return run;
  }
  async saveReflection(route, stageId, reflection, confirmed) {
    if (!route.stages.some((s) => s.id === stageId) || typeof reflection !== 'string' || reflection.length > 6000 || typeof confirmed !== 'boolean') throw new Error('无效的阶段记录。');
    if (confirmed && !reflection.trim()) throw new Error('请先填写自查说明，再标记完成。');
    return this.update(route, (state) => { state.stages[stageId] = { reflection, confirmed, routeVersion: route.version, updatedAt: new Date().toISOString() }; });
  }
  async remember(route, lessonId) {
    if (!route.stages.some((s) => [...s.required, ...s.optional].includes(lessonId))) throw new Error('题目不在当前路线中。');
    return this.update(route, (state) => { state.lastLessonId = lessonId; });
  }
}
module.exports = { CampStore };
