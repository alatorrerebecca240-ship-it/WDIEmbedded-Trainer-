const vscode = require('vscode');
const fs = require('node:fs');
const path = require('node:path');
const { defaults, manifest } = require('./environment');

async function checkEnvironment(runtime, backend, refresh) {
  if (runtime.busy) { vscode.window.showInformationMessage('环境检查或安装正在进行，请等待当前操作完成。'); return; }
  runtime.busy = true;
  const config = vscode.workspace.getConfiguration('embeddedTrainer');
  const finish = async () => {
    const result = await backend.run(['doctor']);
    await refresh();
    if (!result.code) vscode.window.showInformationMessage('训练环境检查通过，可以开始学习。');
    else vscode.window.showWarningMessage('环境已检查，请查看输出中的题库或配置问题；无需因此重复安装环境。');
  };
  try {
    const report = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: '检查训练环境', cancellable: false },
      () => runtime.detect(config.get('pythonPath', 'python'), backend.rootUri.fsPath));
    backend.output.show(true);
    const missing = !report.python || !report.c || !report.cpp;
    if (missing || !report.boost) {
      if (process.platform !== 'win32' || process.arch !== 'x64') {
        if (missing) vscode.window.showWarningMessage('离线自动安装仅支持 Windows x64。请根据输出手动补齐环境。');
        else await finish();
        return;
      }
      const choice = await vscode.window.showWarningMessage(missing
        ? '检测到 Python 或 C/C++ 编译环境缺失或不可用，可从配套离线安装包自动补齐。'
        : 'Python 和 C/C++ 自检通过。部分拓展题需要 Boost 头文件，可从配套包补充。基础题可以直接学习。',
        '从离线包自动安装', '暂不安装');
      if (choice !== '从离线包自动安装') { if (!missing) await finish(); return; }
      const selected = await vscode.window.showOpenDialog({ canSelectFiles: false, canSelectFolders: true, canSelectMany: false,
        openLabel: '选择已解压的离线安装包', title: '选择整体离线包根目录，或其中的 environment 文件夹' });
      if (!selected?.length) { if (!missing) await finish(); return; }
      const root = selected[0].fsPath;
      const folder = fs.existsSync(path.join(root, 'environment')) ? path.join(root, 'environment') : root;
      const target = defaults();
      const instructions = [!report.python && `Python ${manifest.python.version} → ${target.python}`,
        (!report.c || !report.cpp) && `C/C++ 编译器 → ${target.compiler}`, !report.boost && `Boost 头文件 → ${target.boost}`].filter(Boolean).join('\n');
      const confirmation = await vscode.window.showWarningMessage(`将安装缺失组件：\n${instructions}\n\n请预留至少 6 GB 空间。只安装到当前用户目录，不修改系统 PATH、不覆盖已有环境。安装程序将执行本地软件；请确认离线包来自可信带教或发布者。`,
        { modal: true }, '确认并按默认路径安装');
      if (confirmation !== '确认并按默认路径安装') { if (!missing) await finish(); return; }
      await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: '离线安装训练环境', cancellable: false },
        progress => runtime.install(folder, report, message => progress.report({ message })));
      // Only persist usable paths after the same checks used for existing environments.
      const verified = await runtime.detect(config.get('pythonPath', 'python'), backend.rootUri.fsPath);
      if (!verified.python || !verified.c || !verified.cpp) throw Error('安装程序已退出，但环境复检尚未通过。请查看输出；不要重复卸载或删除环境。');
    }
    await finish();
  } catch (error) {
    backend.output.appendLine(error.message || String(error));
    vscode.window.showErrorMessage(error.message || String(error));
  } finally { runtime.busy = false; }
}
module.exports = { checkEnvironment };
