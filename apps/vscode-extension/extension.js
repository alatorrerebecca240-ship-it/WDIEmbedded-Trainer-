const vscode = require('vscode');
const path = require('path');
const { TrainerBackend } = require('./src/backend');
const { LessonCatalog } = require('./src/catalog');
const { LessonTreeProvider, STATUS_NAMES, QUESTION_TYPE_NAMES, LANGUAGE_NAMES } = require('./src/tree');
const { LessonDashboard } = require('./src/dashboard');
const { TestingIntegration } = require('./src/testing');
const { PackageManager } = require('./src/packages');

async function exists(uri) {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch (_) {
    return false;
  }
}

async function findProjectRoot() {
  for (const folder of vscode.workspace.workspaceFolders || []) {
    if (await exists(vscode.Uri.joinPath(folder.uri, 'trainer.py'))) {
      return folder.uri;
    }
  }
  return (vscode.workspace.workspaceFolders || [])[0]?.uri;
}

async function activate(context) {
  const showHelp = async () => {
    const helpUri = vscode.Uri.joinPath(context.extensionUri, 'docs', 'usage.md');
    await vscode.commands.executeCommand('markdown.showPreview', helpUri);
  };
  context.subscriptions.push(vscode.commands.registerCommand('embeddedTrainer.help', showHelp));

  const rootUri = await findProjectRoot() || vscode.Uri.joinPath(context.globalStorageUri, 'practice');
  await vscode.workspace.fs.createDirectory(rootUri);
  const packUri = vscode.Uri.joinPath(context.globalStorageUri, 'knowledge');
  await vscode.workspace.fs.createDirectory(packUri);
  const output = vscode.window.createOutputChannel('Embedded Trainer');
  const diagnostics = vscode.languages.createDiagnosticCollection('embeddedTrainer');
  const bundledEngine = vscode.Uri.joinPath(context.extensionUri, 'runtime', 'trainer.py');
  const enginePath = await exists(bundledEngine) ? bundledEngine.fsPath : path.resolve(context.extensionUri.fsPath, '..', '..', 'trainer.py');
  const backend = new TrainerBackend(rootUri, output, diagnostics, { enginePath, packHome: packUri.fsPath });
  const catalog = new LessonCatalog(rootUri, backend);
  const treeProvider = new LessonTreeProvider(catalog);
  const treeView = vscode.window.createTreeView('embeddedTrainer.lessons', {
    treeDataProvider: treeProvider,
    showCollapseAll: true
  });
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 30);
  statusBar.command = 'embeddedTrainer.progress';
  statusBar.name = 'Embedded Trainer 进度';
  statusBar.show();

  let dashboard;
  let testing;
  let refreshing;

  const refresh = async () => {
    if (refreshing) {
      return refreshing;
    }
    refreshing = (async () => {
      await catalog.reload();
      treeProvider.refresh();
      if (testing) {
        testing.sync(catalog.lessons);
      }
      const passed = catalog.lessons.filter((lesson) => catalog.status(lesson.id).status === 'passed').length;
      statusBar.text = `$(mortar-board) Trainer ${passed}/${catalog.lessons.length}`;
      statusBar.tooltip = `已通过 ${passed} 个课程，共 ${catalog.lessons.length} 个`;
      treeView.badge = { value: passed, tooltip: `已通过 ${passed}/${catalog.lessons.length}` };
      if (dashboard && dashboard.lesson) {
        const latest = catalog.get(dashboard.lesson.id);
        if (latest) {
          dashboard.update(latest, catalog.status(latest.id));
        }
      }
    })().finally(() => {
      refreshing = undefined;
    });
    return refreshing;
  };

  const resolveLesson = async (input) => {
    let id;
    if (typeof input === 'string') {
      id = input;
    } else if (input && input.lesson) {
      id = input.lesson.id;
    } else if (input && typeof input.id === 'string') {
      id = input.id;
    }
    if (id) {
      return catalog.get(id);
    }
    const selected = await vscode.window.showQuickPick(
      catalog.lessons.map((lesson) => ({
        label: lesson.title,
        description: lesson.id,
        detail: `${QUESTION_TYPE_NAMES[lesson.questionType] || lesson.questionType} · ${LANGUAGE_NAMES[lesson.language] || lesson.language} · ${STATUS_NAMES[catalog.status(lesson.id).status] || catalog.status(lesson.id).status}`,
        lesson
      })),
      { placeHolder: '选择一个课程' }
    );
    return selected && selected.lesson;
  };

  const ensureStarted = async (lesson, token) => {
    const exerciseUri = vscode.Uri.joinPath(rootUri, 'exercises', lesson.id);
    if (await exists(exerciseUri)) {
      return exerciseUri;
    }
    const result = await backend.run(['start', lesson.id], { token });
    if (result.code !== 0) {
      throw new Error(result.output || `无法创建课程 ${lesson.id}`);
    }
    await refresh();
    return exerciseUri;
  };

  const openSource = async (lesson) => {
    const exerciseUri = await ensureStarted(lesson);
    const entries = await vscode.workspace.fs.readDirectory(exerciseUri);
    const editableExtensions = new Set(['.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp']);
    const source = entries
      .filter(([name, type]) => type === vscode.FileType.File && editableExtensions.has(path.extname(name).toLowerCase()))
      .map(([name]) => name)
      .sort((left, right) => {
        const leftIsSource = /\.(c|cc|cpp|cxx)$/i.test(left) ? 0 : 1;
        const rightIsSource = /\.(c|cc|cpp|cxx)$/i.test(right) ? 0 : 1;
        return leftIsSource - rightIsSource || left.localeCompare(right);
      })[0];
    if (!source) {
      throw new Error(`课程 ${lesson.id} 没有可编辑的 C/C++ 文件。`);
    }
    const document = await vscode.workspace.openTextDocument(vscode.Uri.joinPath(exerciseUri, source));
    await vscode.window.showTextDocument(document, { preview: false });
  };

  const executeLesson = async (lessonId, token) => {
    const lesson = catalog.get(lessonId);
    if (!lesson) {
      return { code: -1, output: `未知课程：${lessonId}`, duration: 0 };
    }
    try {
      await ensureStarted(lesson, token);
      await vscode.workspace.saveAll(false);
      diagnostics.clear();
      const result = await backend.run(['check', lesson.id], { token, collectDiagnostics: true });
      await refresh();
      dashboard.update(lesson, catalog.status(lesson.id), {
        result: { ok: result.code === 0, text: result.output.trim() }
      });
      return result;
    } catch (error) {
      return { code: -1, output: error instanceof Error ? error.message : String(error), duration: 0 };
    }
  };

  testing = new TestingIntegration(context, executeLesson);

  const showDashboard = async (input) => {
    const lesson = await resolveLesson(input);
    if (lesson) {
      dashboard.show(lesson, catalog.status(lesson.id));
    }
  };

  const startLesson = async (input) => {
    const lesson = await resolveLesson(input);
    if (!lesson) {
      return;
    }
    if (!['programming', 'debugging'].includes(lesson.questionType)) {
      dashboard.show(lesson, catalog.status(lesson.id));
      return;
    }
    try {
      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: `准备课程：${lesson.title}`, cancellable: false },
        () => ensureStarted(lesson)
      );
      await openSource(lesson);
      await refresh();
      dashboard.show(lesson, catalog.status(lesson.id));
    } catch (error) {
      vscode.window.showErrorMessage(error instanceof Error ? error.message : String(error));
    }
  };

  const showHint = async (input) => {
    const lesson = await resolveLesson(input);
    if (!lesson || !lesson.hints || lesson.hints.length === 0) {
      return;
    }
    const selected = await vscode.window.showQuickPick(
      lesson.hints.map((hint, index) => ({ label: `提示 ${index + 1}`, detail: index === 0 ? '信息最少' : '逐步增加信息', hint })),
      { placeHolder: '选择提示级别，建议从提示 1 开始' }
    );
    if (selected) {
      dashboard.show(lesson, catalog.status(lesson.id), { hint: selected.hint });
    }
  };

  const openInstructions = async (input) => {
    const lesson = await resolveLesson(input);
    if (lesson) {
      if (lesson.statementUri) {
        await vscode.commands.executeCommand('markdown.showPreview', lesson.statementUri);
      } else {
        dashboard.show(lesson, catalog.status(lesson.id));
      }
    }
  };

  const runDoctor = async () => {
    const result = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: '检查 Embedded Trainer 环境', cancellable: false },
      () => backend.run(['doctor'])
    );
    output.show(true);
    if (result.code === 0) {
      vscode.window.showInformationMessage('训练环境检查通过。');
    } else {
      vscode.window.showErrorMessage('训练环境检查未通过，请查看“Embedded Trainer”输出。');
    }
  };

  const showProgress = async () => {
    const selected = await vscode.window.showQuickPick(
      catalog.lessons.map((lesson) => {
        const progress = catalog.status(lesson.id);
        return {
          label: `${progress.status === 'passed' ? '$(pass-filled)' : progress.status === 'in-progress' ? '$(edit)' : '$(circle-large-outline)'} ${lesson.title}`,
          description: STATUS_NAMES[progress.status] || progress.status,
          detail: `${QUESTION_TYPE_NAMES[lesson.questionType] || lesson.questionType} · ${lesson.id} · 已评测 ${progress.attempts || 0} 次`,
          lesson
        };
      }),
      { placeHolder: '学习进度——选择课程以打开详情' }
    );
    if (selected) {
      dashboard.show(selected.lesson, catalog.status(selected.lesson.id));
    }
  };

  const checkLesson = async (input) => {
    const lesson = await resolveLesson(input);
    if (!lesson) {
      return;
    }
    if (!['programming', 'debugging'].includes(lesson.questionType)) {
      dashboard.show(lesson, catalog.status(lesson.id));
      return;
    }
    const result = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `评测：${lesson.title}`, cancellable: true },
      (_, token) => testing.runLesson(lesson.id, token)
    );
    await refresh();
    dashboard.show(lesson, catalog.status(lesson.id), {
      result: { ok: result && result.code === 0, text: result ? result.output.trim() : '评测已取消' }
    });
    if (result && result.code === 0) {
      const action = await vscode.window.showInformationMessage(`课程“${lesson.title}”已通过！`, '查看学习进度');
      if (action === '查看学习进度') {
        await showProgress();
      }
    } else if (result) {
      const action = await vscode.window.showWarningMessage(`课程“${lesson.title}”尚未通过。`, '查看评测输出', '查看提示');
      if (action === '查看评测输出') {
        output.show(true);
      } else if (action === '查看提示') {
        await showHint(lesson.id);
      }
    }
  };

  const submitQuiz = async (lesson, answer) => {
    const result = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: `提交：${lesson.title}`, cancellable: false },
      () => backend.run(['submit', lesson.id, '--answer', JSON.stringify(answer)])
    );
    await refresh();
    dashboard.show(lesson, catalog.status(lesson.id), {
      result: { ok: result.code === 0, text: result.output.trim() }
    });
    if (result.code === 0) {
      vscode.window.showInformationMessage('回答正确！');
    } else {
      const action = await vscode.window.showWarningMessage('回答不正确，再想一想。', '查看提示');
      if (action === '查看提示') {
        await showHint(lesson.id);
      }
    }
  };

  dashboard = new LessonDashboard(async (message, lesson) => {
    if (message.command === 'start') {
      await startLesson(lesson.id);
    } else if (message.command === 'check') {
      await checkLesson(lesson.id);
    } else if (message.command === 'hint') {
      await showHint(lesson.id);
    } else if (message.command === 'instructions') {
      await openInstructions(lesson.id);
    } else if (message.command === 'help') {
      await showHelp();
    } else if (message.command === 'submit') {
      await submitQuiz(lesson, message.answer);
    }
  });

  const packages = new PackageManager(context, backend, refresh);
  context.subscriptions.push(
    output,
    diagnostics,
    treeView,
    statusBar,
    vscode.commands.registerCommand('embeddedTrainer.refresh', refresh),
    vscode.commands.registerCommand('embeddedTrainer.dashboard', showDashboard),
    vscode.commands.registerCommand('embeddedTrainer.start', startLesson),
    vscode.commands.registerCommand('embeddedTrainer.check', checkLesson),
    vscode.commands.registerCommand('embeddedTrainer.hint', showHint),
    vscode.commands.registerCommand('embeddedTrainer.instructions', openInstructions),
    vscode.commands.registerCommand('embeddedTrainer.doctor', runDoctor),
    vscode.commands.registerCommand('embeddedTrainer.progress', showProgress),
    vscode.commands.registerCommand('embeddedTrainer.packages', () => packages.manage()),
    vscode.commands.registerCommand('embeddedTrainer.updatePackages', () => packages.update()),
    vscode.commands.registerCommand('embeddedTrainer.importPackage', async () => {
      try { await packages.offlineImport(); } catch (error) { vscode.window.showErrorMessage(error.message); }
    })
  );

  const lessonWatcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(rootUri.fsPath, 'content/**/lesson.json')
  );
  const questionBankWatcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(rootUri.fsPath, 'content/**/question-bank.json')
  );
  const progressWatcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(rootUri.fsPath, '.trainer/progress.json')
  );
  const sourceWatcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(rootUri.fsPath, 'knowledge/packs/**/*.json'));
  const configWatcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(rootUri.fsPath, 'trainer-packs.json'));
  const packWatcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(packUri.fsPath, 'installed.json'));
  const safeRefresh = () => refresh().catch((error) => output.appendLine(`题库刷新失败，保留旧列表：${error.message}`));
  for (const watcher of [lessonWatcher, questionBankWatcher, progressWatcher, sourceWatcher, configWatcher, packWatcher]) {
    watcher.onDidCreate(safeRefresh);
    watcher.onDidChange(safeRefresh);
    watcher.onDidDelete(safeRefresh);
    context.subscriptions.push(watcher);
  }

  await safeRefresh();
  packages.start();

  const guideKey = 'usageGuideShownVersion';
  const currentVersion = context.extension.packageJSON.version;
  if (context.globalState.get(guideKey) !== currentVersion) {
    await context.globalState.update(guideKey, currentVersion);
    const action = await vscode.window.showInformationMessage(
      'Embedded Trainer 已准备好，全程可以在 VS Code 界面内使用。',
      '打开使用说明'
    );
    if (action === '打开使用说明') {
      await showHelp();
    }
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
