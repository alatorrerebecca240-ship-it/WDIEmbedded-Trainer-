const vscode = require('vscode');
const path = require('node:path');
const { AuthoringCloud } = require('./authoring-cloud');

const STATUS = { pending: '等待云端验证', checking: '云端验证中', ready: '待人工审核', approved: '已人工审核',
  'import-failed': '导入失败', 'static-failed': '静态检查失败', 'validation-failed': '云端验证失败', changed: '内容已修改', deferred: '已暂缓' };

const WORKFLOW_URL = 'https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-/actions/workflows/exercism-pilot.yml';

class AuthoringManager {
  constructor(context, backend) {
    this.context = context;
    this.backend = backend;
    this.busy = false;
    this.root = backend.rootUri.fsPath;
    this.index = path.join(this.root, '.imports', 'exercism-index.json');
    this.cache = path.join(this.root, '.imports', 'exercism-cache');
    this.cloud = new AuthoringCloud(context, backend);
  }

  start() { this.cloud.start(); }

  async projectLicense() {
    const installed = path.join(this.context.extensionUri.fsPath, 'LICENSE.txt');
    try { await vscode.workspace.fs.stat(vscode.Uri.file(installed)); return installed; }
    catch { return path.join(this.context.extensionUri.fsPath, 'LICENSE'); }
  }

  async getNew() {
    if (this.busy) return vscode.window.showInformationMessage('题库维护正在进行，请稍候。');
    if (!vscode.workspace.workspaceFolders?.length) return vscode.window.showInformationMessage('请先打开题库工作文件夹。');
    this.busy = true;
    try {
      const result = await this.run(['inbox-get', '--project-license', await this.projectLicense()], '获取新题：自动筛选、去重并加入审核列表');
      vscode.window.showInformationMessage(`新增 ${result.added} 题，接管旧草稿 ${result.adopted} 题，导入失败 ${result.failed} 题。失败题保留待处理，不阻塞其他题。`);
      if (result.warnings.length) vscode.window.showWarningMessage(result.warnings[0]);
      if ((result.counts.pending || 0) > 0) await this.cloud.dispatch();
    } catch (error) { vscode.window.showWarningMessage(error.message); }
    finally { this.busy = false; }
  }

  async reviewInbox() {
    if (this.busy) return vscode.window.showInformationMessage('题库维护正在进行，请稍候。');
    if (!vscode.workspace.workspaceFolders?.length) return vscode.window.showInformationMessage('请先打开题库工作文件夹。');
    this.busy = true;
    try {
      await this.cloud.poll(false);
      const result = await this.run(['inbox-list'], '读取集中审核列表');
      const ready = result.items.filter((v) => v.status === 'ready');
      const chosen = await vscode.window.showQuickPick([
        { label: `浏览题目（${result.total}）`, action: 'browse', description: '查看题面、参考答案、测试、来源及待处理问题' },
        { label: `批量确认审核（${ready.length}）`, action: 'approve', description: '仅已通过云端验证的题；仍需人工核对内容与版权' },
        { label: '重新验证待处理题目', action: 'retry', description: '只处理待验证或失败题；保留原始上游空框架，不重复验证已就绪或已审核题' },
        { label: '准备发布已审核题目', action: 'stage', description: '确认后生成发布快照，不自动推送、打标签或发布' }
      ], { title: '集中审核', placeHolder: `待验证 ${result.counts.pending || 0} · 验证中 ${result.counts.checking || 0} · 待审核 ${ready.length} · 已审核 ${result.counts.approved || 0}` });
      if (!chosen) return;
      if (chosen.action === 'browse') await this.browseInbox(result.items);
      if (chosen.action === 'approve') await this.approveInbox(ready);
      if (chosen.action === 'retry') await this.cloud.dispatch();
      if (chosen.action === 'stage') {
        const choice = await vscode.window.showWarningMessage('将已人工审核且内容未改变的题目复制到 knowledge/approved？现有快照不会覆盖；正式发布仍使用 GitHub 的验证和发布审批流程。', { modal: true }, '准备发布快照');
        if (choice === '准备发布快照') {
          const staged = await this.run(['inbox-stage'], '准备已审核快照');
          vscode.window.showInformationMessage(`已准备 ${staged.staged.length} 个快照，${staged.failed.length} 个需处理。尚未推送或发布。`);
          if (staged.failed.length) vscode.window.showWarningMessage(staged.failed[0].error);
        }
      }
    } catch (error) { vscode.window.showErrorMessage(error.message); }
    finally { this.busy = false; }
  }

  async browseInbox(items) {
    if (!items.length) return vscode.window.showInformationMessage('暂无题目，请先点“获取新题”。');
    const entry = await vscode.window.showQuickPick(items.map((v) => ({ label: v.title, description: STATUS[v.status] || v.status,
      detail: `${v.key} · ${[...(v.errors || []), ...(v.warnings || [])].join('；') || '可查看题面、答案、测试与版权来源'}`, entry: v })),
      { title: '集中审核 · 题目列表', matchOnDescription: true, matchOnDetail: true, placeHolder: '输入状态、题名或知识方向筛选' });
    if (!entry) return;
    const q = entry.entry;
    const actions = [
      { label: '查看题目、答案和来源文件', action: 'files' },
      ...(q.status === 'ready' ? [{ label: '确认本题审核', action: 'approve' }] : []),
      ...(['deferred', 'import-failed', 'static-failed'].includes(q.status) ? [{ label: '恢复或允许重新获取', action: 'resume' }] : []),
      ...(q.status !== 'approved' ? [{ label: '暂缓这道题', action: 'defer' }] : [])
    ];
    const choice = await vscode.window.showQuickPick(actions, { title: `${q.title} · ${STATUS[q.status]}`, placeHolder: [...(q.errors || []), ...(q.warnings || [])].join('；') });
    if (!choice) return;
    if (choice.action === 'approve') return this.approveInbox([q]);
    if (choice.action === 'files') {
      const details = await this.run(['inbox-details', '--question', q.id], '打开题目审核资料');
      const file = await vscode.window.showQuickPick(details.files, { matchOnDescription: true, placeHolder: '先读题面，再检查 reference、tests 和 licenses；不会运行代码' });
      if (file) await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(vscode.Uri.file(file.path)), { preview: false });
    } else {
      await this.run(['inbox-decide', '--decision', choice.action, '--id', q.id], '更新题目审核状态');
      vscode.window.showInformationMessage(choice.action === 'resume' && !q.pack ? '已允许重新获取；再次点击“获取新题”即可重试。' : '审核状态已更新。');
    }
  }

  async approveInbox(ready) {
    if (!ready.length) return vscode.window.showInformationMessage('暂无可审核题目。云端验证未通过的题不能批准。');
    const selected = await vscode.window.showQuickPick(ready.map((v) => ({ label: v.title, description: v.key, entry: v, picked: false })),
      { canPickMany: true, title: '勾选已经人工核对的题目', placeHolder: '机器验证通过不代表内容正确或版权合规；只选你实际检查过的题目' });
    if (!selected?.length) return;
    const reviewer = await vscode.window.showInputBox({ title: '审核人', value: this.context.workspaceState.get('trainer.inbox.reviewer', ''),
      validateInput: (v) => v.trim() ? undefined : '请填写审核人姓名或账号。' });
    if (!reviewer) return;
    const choice = await vscode.window.showWarningMessage(`确认已人工核对这 ${selected.length} 道题的题干、答案、测试和许可证/署名？此次只记录审核，不代表发布或授予本机执行权限。`, { modal: true }, '确认内容与版权审核');
    if (choice !== '确认内容与版权审核') return;
    const result = await this.run(['inbox-decide', '--decision', 'approve', '--reviewer', reviewer,
      '--ack-content', '--ack-copyright', ...selected.flatMap((v) => ['--id', v.entry.id])], '记录人工审核（不发布）');
    await this.context.workspaceState.update('trainer.inbox.reviewer', reviewer);
    vscode.window.showInformationMessage(`已审核 ${result.completed.length} 题，${result.failed.length} 题需处理。`);
    if (result.failed.length) vscode.window.showWarningMessage(result.failed[0].error);
  }

  async run(args, title) {
    // Queue writes are transactional: do not kill the process while it owns the lock.
    const cancellable = !['inbox-get', 'inbox-decide', 'inbox-stage'].includes(args[0]);
    return vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title, cancellable }, async (_, token) => {
      const result = await this.backend.run(['packs', ...args], { token });
      if (token.isCancellationRequested) {
        const error = new Error('已取消；不会发布或启用草稿。已完成的下载保留为缓存。');
        error.cancelled = true;
        throw error;
      }
      if (result.code !== 0) throw new Error(result.output || '题库维护操作失败');
      return JSON.parse(result.stdout);
    });
  }

  async scan() {
    const mode = await vscode.window.showQuickPick([
      { label: '扫描 C 和 C++ 基础题', language: 'all' },
      { label: '仅扫描 C 基础题', language: 'c' },
      { label: '仅扫描 C++ 基础题', language: 'cpp' },
      { label: '使用上次扫描缓存（离线）', offline: true }
    ], { placeHolder: '读取官方仓库目录，不运行任何上游代码' });
    if (!mode) return;
    let catalog;
    const args = ['exercism-scan', '--output', this.index, '--cache', this.cache];
    try {
      catalog = await this.run([...args, ...(mode.offline ? ['--offline'] : ['--language', mode.language])], '扫描 Exercism 上游题目');
    } catch (error) {
      if (error.cancelled || mode.offline || !await vscode.window.showWarningMessage(`${error.message}\n可以尝试保留的旧目录。`, '使用旧缓存')) throw error;
      catalog = await this.run([...args, '--offline'], '读取上次成功扫描的目录');
    }
    await this.chooseAndImport(catalog);
  }

  async chooseAndImport(catalog) {
    const filter = await vscode.window.showQuickPick([
      { label: '推荐试点', mode: 'pilot', description: '优先选择已配置中文学习目标的基础母题' },
      { label: '全部入门题', mode: 'beginner' },
      { label: '全部扫描结果', mode: 'all', description: '非试点题可能需要额外适配' }
    ], { placeHolder: `扫描 ${catalog.count} 题，推荐 ${catalog.recommendedCount} 题${catalog.offline ? '（缓存）' : ''}` });
    if (!filter) return;
    const candidates = catalog.candidates.filter((q) => q.supported && (filter.mode === 'all' || (filter.mode === 'pilot' ? q.recommended : q.difficulty === 'beginner')));
    if (!candidates.length) return vscode.window.showInformationMessage('当前筛选没有可导入的题目。');
    const selected = await vscode.window.showQuickPick(candidates.map((q) => ({
      label: q.title, description: `${q.language === 'cpp' ? 'C++' : 'C'} · ${q.difficulty === 'beginner' ? '入门' : '进阶'} · ${q.key}`,
      detail: `${q.topics.join(' / ')} | 上游 ${q.commit.slice(0, 12)} | ${q.license}${q.frameworkLicense !== q.license ? ' + ' + q.frameworkLicense : ''}`,
      picked: filter.mode === 'pilot', question: q
    })), { canPickMany: true, matchOnDescription: true, matchOnDetail: true, placeHolder: '输入知识点筛选，勾选 1～50 题导入草稿；不会加入学习课程树' });
    if (!selected?.length) return;
    if (selected.length > 50) throw new Error('每批最多 50 题，请减少选择或分批导入。');
    const name = await vscode.window.showInputBox({ title: '草稿知识包名称', value: `exercism.pilot.${Date.now()}`,
      prompt: '保存到工作区 knowledge/drafts/，已有目录不会覆盖。',
      validateInput: (value) => /^[a-z0-9][a-z0-9.-]{0,70}$/.test(value) && !value.endsWith('.') && !/^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)/i.test(value) ? undefined : '使用小写字母、数字、点和连字符；不要使用 Windows 保留名称。' });
    if (!name) return;
    const approved = await vscode.window.showWarningMessage(`将 ${selected.length} 道题及测试、参考源码下载为草稿？不执行代码，不授予信任，不提交 Git，不自动审核或发布。`, { modal: true }, '导入草稿');
    if (approved !== '导入草稿') return;
    const destination = path.join(this.root, 'knowledge', 'drafts', name);
    let license = path.join(this.context.extensionUri.fsPath, 'LICENSE.txt');
    try { await vscode.workspace.fs.stat(vscode.Uri.file(license)); }
    catch { license = path.join(this.context.extensionUri.fsPath, 'LICENSE'); }
    const result = await this.run(['exercism-import', '--index', this.index, '--cache', this.cache, '--destination', destination,
      '--project-license', license,
      ...selected.flatMap((item) => ['--exercise', item.question.key])], `导入 ${selected.length} 道 Exercism 草稿`);
    await vscode.window.showInformationMessage(`已导入 ${result.questions} 道草稿。原题、初始接口及 Docker 验证仍需审核。`);
    await this.openManifest(destination);
  }

  async openManifest(folder) {
    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(path.join(folder, 'import-manifest.json')));
    await vscode.window.showTextDocument(document, { preview: false });
  }

  async selectDraft() {
    const root = vscode.Uri.file(path.join(this.root, 'knowledge', 'drafts'));
    let entries;
    try { entries = await vscode.workspace.fs.readDirectory(root); }
    catch { return vscode.window.showInformationMessage('当前工作区尚无导入草稿。'); }
    const selected = await vscode.window.showQuickPick(entries.filter(([, type]) => type === vscode.FileType.Directory)
      .map(([name]) => ({ label: name, folder: path.join(root.fsPath, name) })), { placeHolder: '选择未审核草稿；此菜单不执行参考代码' });
    return selected?.folder;
  }

  async report() {
    const folder = await this.selectDraft();
    if (!folder) return;
    const report = path.join(this.root, '.trainer', 'authoring', `${path.basename(folder)}.audit.json`);
    const result = await this.backend.run(['packs', 'audit', folder, '--runner', 'none', '--report', report]);
    // Exit 1 is the expected gate for drafts awaiting Docker execution.
    if (![0, 1].includes(result.code)) throw new Error(result.output || '静态检查失败');
    const document = await vscode.workspace.openTextDocument(vscode.Uri.file(report));
    await vscode.window.showTextDocument(document, { preview: false });
    vscode.window.showInformationMessage('这是静态检查报告；缺少 Docker 执行证据时 passed=false 属于预期，不能据此批准发布。');
  }

  async manage() {
    if (this.busy) return vscode.window.showInformationMessage('题库维护操作正在进行，请稍候。');
    if (!vscode.workspace.workspaceFolders?.length) return vscode.window.showInformationMessage('请先打开用于维护题库的工作文件夹。');
    try {
      const chosen = await vscode.window.showQuickPick([
        { label: '获取新题', description: '自动筛选、去重、接管旧草稿并提交云端验证', run: () => this.getNew() },
        { label: '集中审核', description: '统一查看状态、处理失败题并批量确认审核', run: () => this.reviewInbox() },
        { label: '高级工具', description: '手动筛选导入、原始清单和静态报告', run: () => this.advanced() }
      ], { placeHolder: '日常只需“获取新题”和“集中审核”，不会自动发布' });
      if (chosen) await chosen.run();
    } catch (error) { vscode.window.showErrorMessage(error.message); }
    finally { this.busy = false; }
  }

  async advanced() {
    const chosen = await vscode.window.showQuickPick([
      { label: '手动筛选上游题目', run: () => this.scan() },
      { label: '查看旧导入清单', run: async () => { const folder = await this.selectDraft(); if (folder) await this.openManifest(folder); } },
      { label: '旧草稿静态报告', run: () => this.report() },
      { label: '打开原试点工作流', run: () => vscode.env.openExternal(vscode.Uri.parse(WORKFLOW_URL)) },
      { label: '使用说明', run: () => vscode.commands.executeCommand('embeddedTrainer.help') }
    ], { title: '高级维护工具' });
    if (chosen) { this.busy = true; try { await chosen.run(); } finally { this.busy = false; } }
  }
}

module.exports = { AuthoringManager };
