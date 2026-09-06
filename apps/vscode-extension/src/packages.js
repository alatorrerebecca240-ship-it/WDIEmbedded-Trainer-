const vscode = require('vscode');

class PackageManager {
  constructor(context, backend, refresh) {
    this.context = context;
    this.backend = backend;
    this.refresh = refresh;
    this.busy = false;
  }

  config() { return vscode.workspace.getConfiguration('embeddedTrainer'); }

  async run(args) {
    const result = await this.backend.run(['packs', ...args], { silent: true });
    if (result.code !== 0) throw new Error(result.output || '知识包操作失败');
    return JSON.parse(result.stdout);
  }

  async addSource() {
    const url = await vscode.window.showInputBox({ title: '添加可信题库清单', prompt: '填写你信任的 GitHub Pages catalog.json HTTPS 地址。此设置可通过 VS Code Settings Sync 同步。', validateInput: (value) => {
      try { const u = new URL(value); return u.protocol === 'https:' && u.hostname.endsWith('.github.io') && !u.username && !u.password && !u.hash && (!u.port || u.port === '443') ? undefined : '需要 GitHub Pages HTTPS 地址'; }
      catch { return '请输入有效 URL'; }
    } });
    if (!url) return;
    const approved = await vscode.window.showWarningMessage(`信任题库来源 ${new URL(url).hostname}？校验值只能验证文件完整性，不能保证发布者或代码安全。`, { modal: true }, '添加来源');
    if (!approved) return;
    const sources = this.config().get('catalogUrls', []);
    if (!sources.includes(url)) await this.config().update('catalogUrls', [...sources, url], vscode.ConfigurationTarget.Global);
  }

  async browse() {
    const sources = this.config().get('catalogUrls', []);
    if (!sources.length) return this.addSource();
    const source = sources.length === 1 ? sources[0] : await vscode.window.showQuickPick(sources, { placeHolder: '选择题库来源' });
    if (!source) return;
    const available = await this.run(['updates', '--catalog', source]);
    const chosen = await vscode.window.showQuickPick(available.packages.map((item) => ({ label: item.title || item.id, description: `${item.version}${item.installed ? ' · 已安装 ' + item.installed : ''}`, detail: `${item.id}${available.offline ? ' · 使用缓存清单' : ''}`, item })), { placeHolder: '选择安装的知识包（仅下载数据，不执行代码）' });
    if (!chosen) return;
    await this.run(['sync', '--catalog', source, '--id', chosen.item.id]);
    const enabled = this.config().get('enabledPackages', []);
    const subscription = `${source}#${chosen.item.id}`;
    if (!enabled.includes(subscription)) await this.config().update('enabledPackages', [...enabled, subscription], vscode.ConfigurationTarget.Global);
    await this.refresh();
    vscode.window.showInformationMessage(`已安装 ${chosen.item.id} ${chosen.item.version}；编程代码须另行确认信任。`);
  }

  async update(background = false) {
    if (this.busy) return;
    const sources = this.config().get('catalogUrls', []);
    if (!sources.length) {
      if (!background) vscode.window.showInformationMessage('尚未配置题库清单，请先在“管理知识包”中添加来源。');
      return;
    }
    this.busy = true;
    await this.context.globalState.update('packagesLastCheck', Date.now());
    let changed = 0;
    try {
      const enabled = this.config().get('enabledPackages', []);
      for (const source of sources) {
        const result = await this.run(['sync', '--catalog', source]);
        changed += result.installed.length;
        // Explicit subscriptions synced from another computer can bootstrap missing packages.
        for (const item of result.packages.filter((p) => !p.installed && enabled.includes(`${source}#${p.id}`))) {
          await this.run(['sync', '--catalog', source, '--id', item.id]);
          changed += 1;
        }
      }
      await this.context.globalState.update('packagesLastCheck', Date.now());
      if (changed) {
        await this.refresh();
        vscode.window.showInformationMessage(`已更新 ${changed} 个知识包，旧版本及练习代码保留。`);
      } else if (!background) vscode.window.showInformationMessage('没有可更新的知识包；网络不可用时使用已缓存的清单和题库。');
    } catch (error) {
      // Offline operation is expected; keep the previous catalog and avoid recurring popups.
      this.backend.output.appendLine(`知识包更新未完成，保留旧版本：${error.message}`);
      if (!background) vscode.window.showWarningMessage(error.message);
    } finally { this.busy = false; }
  }

  async offlineImport() {
    const paths = await vscode.window.showOpenDialog({ canSelectMany: false, filters: { '知识包 ZIP': ['zip'] } });
    if (!paths || !paths.length) return;
    const sha = await vscode.window.showInputBox({ title: '校验离线知识包', prompt: '粘贴从可信发布页或 .sha256 文件获取的 SHA-256（不是自动从待导入 ZIP 推算）', validateInput: (value) => /^[a-fA-F0-9]{64}$/.test(value.trim()) ? undefined : '需要 64 位十六进制校验值' });
    if (!sha) return;
    const result = await this.run(['install', paths[0].fsPath, '--sha256', sha.trim().toLowerCase()]);
    await this.refresh();
    vscode.window.showInformationMessage(`离线导入完成：${result.id} ${result.version}`);
  }

  async selectInstalled() {
    const index = await this.run(['list']);
    const selected = await vscode.window.showQuickPick(Object.entries(index.active).map(([id, version]) => ({ label: id, description: `${version}${index.pinned[id] ? ' · 已暂停更新' : ''}`, id, version })), { placeHolder: '选择已安装知识包' });
    return selected && { ...selected, index };
  }

  async rollback() {
    const pack = await this.selectInstalled();
    if (!pack) return;
    const release = await vscode.window.showQuickPick(Object.keys(pack.index.versions[pack.id]).filter((v) => v !== pack.version), { placeHolder: '选择保留的版本，回退后暂停此包自动更新' });
    if (!release) return;
    await this.run(['rollback', pack.id, release]);
    await this.refresh();
    vscode.window.showInformationMessage(`已回退到 ${release} 并暂停此包更新；已有练习仍固定到创建时版本。`);
  }

  async trust() {
    const pack = await this.selectInstalled();
    if (!pack) return;
    const sha = pack.index.versions[pack.id][pack.version].sha256;
    const action = await vscode.window.showWarningMessage(`允许 ${pack.id} ${pack.version} 的 C/C++ 源码和测试在本机执行？它们不是沙箱程序，可能访问你账号可访问的文件。仅对已审查且信任的发布者授权。新版本需要重新授权。`, { modal: true }, '信任此版本的代码');
    if (!action) return;
    await this.run(['trust', pack.id, '--sha256', sha, '--trust-code']);
    await this.refresh();
  }

  async manage() {
    const operations = [
      ['浏览并安装知识包', () => this.browse()], ['检查并更新题库', () => this.update()],
      ['添加题库清单来源', () => this.addSource()], ['离线导入 ZIP', () => this.offlineImport()],
      ['回退到已保留版本', () => this.rollback()], ['信任知识包代码', () => this.trust()],
      ['恢复某个包的自动更新', async () => { const p = await this.selectInstalled(); if (p) await this.run(['unpin', p.id]); }],
      ['打开版本与缓存目录', () => vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(this.backend.packHome))]
    ];
    const chosen = await vscode.window.showQuickPick(operations.map(([label, run]) => ({ label, run })), { placeHolder: '知识包管理（学习进度不会上传到公开题库）' });
    if (chosen) {
      try { await chosen.run(); }
      catch (error) { vscode.window.showErrorMessage(error.message); }
    }
  }

  start() {
    const tick = () => {
      if (!this.config().get('autoUpdatePacks', true)) return;
      const hours = Math.max(6, this.config().get('updateIntervalHours', 24));
      if (Date.now() - this.context.globalState.get('packagesLastCheck', 0) >= hours * 3600000) void this.update(true);
    };
    const initial = setTimeout(tick, 10000);
    const timer = setInterval(tick, 3600000);
    this.context.subscriptions.push({ dispose: () => { clearTimeout(initial); clearInterval(timer); } });
  }
}

module.exports = { PackageManager };
