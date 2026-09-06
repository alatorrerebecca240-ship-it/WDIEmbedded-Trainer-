const vscode = require('vscode');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { validateRoute, buildRoadmap, buildReport, markdownReport } = require('./roadmap-model');
const { CampStore } = require('./camp-store');
const { roadmapClient } = require('./roadmap-client');
const builtin = validateRoute(require('../routes/lab-foundations.json'));
const styles = fs.readFileSync(path.join(__dirname, '../media/dashboard.css'), 'utf8') + '\n' + fs.readFileSync(path.join(__dirname, '../media/roadmap.css'), 'utf8');
const esc = (v) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
const action = (command, label, primary = false, id = '') => `<button type="button" class="${primary ? 'primary' : 'secondary'}" data-command="${command}"${id ? ` data-lesson-id="${esc(id)}"` : ''}>${esc(label)}</button>`;
const statusNames = { passed: '已通过', 'in-progress': '练习中', 'not-started': '未开始', missing: '未安装' };

function renderRoadmap(model, viewId) {
  const nonce = crypto.randomBytes(16).toString('hex');
  const current = model.stages.find((s) => !s.complete)?.id;
  const rows = (items) => `<ul class="lesson-rows">${items.map((q) => `<li class="lesson-row ${q.status === 'passed' ? 'passed' : ''}"><button type="button" data-command="lesson" data-lesson-id="${esc(q.id)}" ${q.missing ? 'disabled data-unavailable="true"' : ''}>${esc(q.title)}</button><small>${esc(statusNames[q.status] || '练习中')}${q.needsTrust ? ' · 待授权' : ''}</small></li>`).join('')}</ul>`;
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}';"><title>新生训练营路线图</title><style nonce="${nonce}">${styles}</style></head>
<body data-view-id="${esc(viewId)}" data-route-key="${esc(model.id + '@' + model.version)}"><div class="camp">
<header class="toolbar"><div class="brand">◇ <span>EMBEDDED <strong>TRAINER</strong></span></div><nav aria-label="训练营工具">${action('library', '完整题库')}${action('report', '导出学习报告')}${action('help', '使用说明')}</nav></header>
<main><div class="camp-kicker">LAB / CLUB · LEARNING ROADMAP</div><h1>${esc(model.title)}</h1><p class="camp-intro">${esc(model.description)}</p>
<div class="camp-metrics"><span><strong>${model.passed}/${model.requiredCount}</strong>必做题通过</span><span><strong>${model.completedStages}/${model.stages.length}</strong>练习与自查完成</span><span><strong>${model.optionalCount}</strong>选做拓展</span></div>
<nav class="route-overview" aria-label="全部阶段一览">${model.stages.map((s, i) => `<button type="button" data-stage-target="stage-${esc(s.id)}" class="${s.complete ? 'done' : ''}"><span>${s.complete ? '✓' : String(i + 1).padStart(2, '0')}</span>${esc(s.title)}</button>`).join('')}</nav>
<section class="camp-next" aria-label="下一步"><div><span class="camp-kicker">NEXT STEP</span><h2>${esc(model.next?.title || (model.missing ? '先补齐路线需要的题目' : model.completedStages === model.stages.length ? '主线完成，准备讲解你的项目' : '必做题已通过，继续阶段自查'))}</h2><p>${model.next ? '从上次未完成的练习继续，也可以自由选择下面的阶段。' : '通过测试和能解释代码是两件事。自查记录不会冒充带教验收。'}</p></div>${model.next ? action('lesson', '继续学习 →', true, model.next.id) : action(model.missing ? 'packages' : 'project', model.missing ? '管理知识包' : '打开项目指南', true)}</section>
${model.missing ? `<section class="trust-notice">当前缺少 ${model.missing} 道必做题；这些题不会被计为完成。${action('packages', '管理知识包')}</section>` : ''}
<div id="camp-status" class="camp-status" role="status" aria-live="polite"></div>
<div class="camp-grid"><ol class="route-list">${model.stages.map((stage, i) => `<li class="route-node ${stage.complete ? 'complete' : stage.id === current ? 'current' : ''}"><span class="node-number" aria-hidden="true">${stage.complete ? '✓' : String(i + 1).padStart(2, '0')}</span><details id="stage-${esc(stage.id)}" ${stage.id === current ? 'open' : ''}><summary><span class="stage-heading">${esc(stage.title)}</span><span class="stage-meta">${esc(stage.summary)}<br>预计 ${stage.minutes} 分钟 · 必做 ${stage.passed}/${stage.required.length} · 自查${stage.selfChecked ? '已记录' : '待完成'}<progress value="${stage.passed}" max="${stage.required.length}" aria-label="${esc(stage.title)}必做题进度"></progress></span></summary><div class="stage-body">
<h3>01 / 先理解概念</h3><ul>${stage.concepts.map((c) => `<li>${esc(c)}</li>`).join('')}</ul><pre tabindex="0" aria-label="概念示例代码"><code>${esc(stage.example)}</code></pre><p><strong>先预测，再验证：</strong>${esc(stage.predict)}</p>
<h3>02 / 完成必做练习</h3>${rows(stage.required)}<h3>选做拓展 · 不影响主线完成</h3>${rows(stage.optional)}
<h3>03 / 项目积累与阶段自查</h3><p>${esc(stage.projectStep)}</p><p>${esc(stage.checkpoint)}</p><form data-stage-form="${esc(stage.id)}"><label class="camp-note" for="note-${esc(stage.id)}">记录你的解释、测试结果或待求助问题（只保存在本机）</label><textarea id="note-${esc(stage.id)}" maxlength="6000" placeholder="不要只写“完成了”，试着解释原因或列出测试。">${esc(stage.reflection)}</textarea><label class="self-check"><input type="checkbox" ${stage.selfChecked ? 'checked' : ''}><span>我已完成上面的自查，并能向同伴说明；这不是带教验收。</span></label><button class="secondary" type="submit">保存自查记录</button></form>
</div></details></li>`).join('')}</ol>
<aside class="camp-side"><section><h2>怎样走这条路线</h2><ol><li>读概念，预测示例结果。</li><li>完成必做题，遇到困难逐层看提示。</li><li>用自己的话解释，记录边界测试。</li><li>把学到的模块带入模拟项目。</li></ol><p>没有周次和硬性解锁。预计用时仅供参考，可以跳转、补弱或重做。</p></section><section><h2>我的复习清单</h2><p>${model.review.length ? `${model.review.length} 道主线题已有提交但尚未通过。` : '目前没有已提交但未通过的主线题。'}</p>${model.review.slice(0, 4).map((q) => action('lesson', q.title, false, q.id)).join('')}</section><section><h2>最终小项目</h2><p>先用电脑模拟传感器输入，完成受限输出与状态切换；不要求立即购买或连接硬件。</p>${action('project', '模拟智能车项目指南')}${action('report', '导出给带教同学')}</section><section><h2>路线与题库分离</h2><p>路线只引用题目 ID。完整题库继续可用，Linux、ROS 2 和 C++ 可留作后续分支。</p>${action('export-route', '导出路线模板')}${action('packages', '管理知识包')}</section></aside></div></main>
<footer class="footer"><span>EMBEDDED TRAINER · CAMP EDITION</span><span>练习通过 ≠ 已掌握 · 讲清楚，才走得稳</span></footer></div><script nonce="${nonce}">(${roadmapClient.toString()})();</script></body></html>`;
}

class CampDashboard {
  constructor(context, rootUri, catalog, openLesson) {
    this.context = context; this.rootUri = rootUri; this.catalog = catalog; this.openLesson = openLesson;
    this.store = new CampStore(rootUri.fsPath); this.route = builtin; this.pending = false; this.generation = 0;
  }
  async loadRoute() {
    try {
      const file = path.join(this.rootUri.fsPath, 'trainer-roadmap.json');
      if ((await fsp.stat(file)).size > 256 * 1024) throw new Error('路线文件不能超过 256 KB。');
      this.route = validateRoute(JSON.parse(await fsp.readFile(file, 'utf8')));
    } catch (error) { if (error.code === 'ENOENT') this.route = builtin; else throw error; }
  }
  async show() {
    await this.loadRoute();
    // Read before replacing the panel so malformed notes are never silently reset.
    await this.store.read();
    if (!this.panel) {
      this.panel = vscode.window.createWebviewPanel('embeddedTrainer.roadmap', '新生训练营 · 路线图', vscode.ViewColumn.Active,
        { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] });
      this.panel.onDidDispose(() => { this.panel = undefined; this.generation++; });
      this.panel.webview.onDidReceiveMessage((message) => this.handleMessage(message));
    } else this.panel.reveal(vscode.ViewColumn.Active, true);
    await this.refresh();
  }
  async model() { return buildRoadmap(this.route, this.catalog.lessons, this.catalog.progress, await this.store.read()); }
  async refresh() {
    if (!this.panel) return;
    const generation = ++this.generation;
    const model = await this.model();
    if (!this.panel || generation !== this.generation) return;
    const signature = JSON.stringify(model);
    if (this.signature === signature && this.panel.webview.html) return;
    this.signature = signature; this.viewId = crypto.randomBytes(16).toString('hex');
    this.panel.webview.html = renderRoadmap(model, this.viewId);
  }
  async exportReport() {
    await this.loadRoute();
    const report = buildReport(await this.model());
    const destination = await vscode.window.showSaveDialog({ title: '保存学习报告（仅保存到你选择的位置）',
      defaultUri: vscode.Uri.joinPath(this.rootUri, '训练营学习报告.md'), filters: { Markdown: ['md'], JSON: ['json'] } });
    if (!destination) return;
    const content = destination.fsPath.toLowerCase().endsWith('.json') ? JSON.stringify(report, null, 2) + '\n' : markdownReport(report);
    await vscode.workspace.fs.writeFile(destination, Buffer.from(content));
    vscode.window.showInformationMessage('学习报告已保存；没有上传到网络。分享前请检查你自己填写的记录。');
  }
  async exportRoute() {
    const destination = await vscode.window.showSaveDialog({ title: '导出路线模板；放到目标项目根目录即可使用',
      defaultUri: vscode.Uri.joinPath(this.rootUri, 'trainer-roadmap.json'), filters: { JSON: ['json'] } });
    if (destination) await vscode.workspace.fs.writeFile(destination, Buffer.from(JSON.stringify(this.route, null, 2) + '\n'));
  }
  async handleMessage(message) {
    if (!message || message.viewId !== this.viewId) return;
    if (message.command === 'ready') { this.panel?.webview.postMessage({ command: 'busy', busy: this.pending }); return; }
    if (this.pending || !['lesson', 'save', 'report', 'export-route', 'library', 'help', 'packages', 'project'].includes(message.command)) return;
    this.pending = true; this.panel?.webview.postMessage({ command: 'busy', busy: true });
    try {
      if (message.command === 'lesson') {
        if (!this.catalog.get(message.lessonId)) throw new Error('题目尚未安装，请先管理知识包。');
        await this.store.remember(this.route, message.lessonId);
        await this.openLesson(message.lessonId);
      } else if (message.command === 'save') {
        await this.store.saveReflection(this.route, message.stageId, message.reflection, message.confirmed);
        this.panel?.webview.postMessage({ command: 'saved', stageId: message.stageId });
        await this.refresh();
      } else if (message.command === 'report') await this.exportReport();
      else if (message.command === 'export-route') await this.exportRoute();
      else if (message.command === 'project') await vscode.commands.executeCommand('markdown.showPreview', vscode.Uri.joinPath(this.context.extensionUri, 'docs', 'camp-project.md'));
      else await vscode.commands.executeCommand({ library: 'embeddedTrainer.library', help: 'embeddedTrainer.help', packages: 'embeddedTrainer.packages' }[message.command]);
    } catch (error) { this.panel?.webview.postMessage({ command: 'error', text: error.message }); vscode.window.showErrorMessage(error.message); }
    finally { this.pending = false; this.panel?.webview.postMessage({ command: 'busy', busy: false }); }
  }
  dispose() { this.panel?.dispose(); }
}
module.exports = { CampDashboard, renderRoadmap };
