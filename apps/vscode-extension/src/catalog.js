const vscode = require('vscode');
const path = require('path');

async function readJson(uri, fallback = undefined) {
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    return JSON.parse(Buffer.from(bytes).toString('utf8'));
  } catch (error) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

class LessonCatalog {
  constructor(rootUri, backend) {
    this.rootUri = rootUri;
    this.lessons = [];
    this.progress = {};
    this.backend = backend;
  }

  async reload() {
    if (this.backend) {
      const result = await this.backend.run(['catalog'], { silent: true });
      if (result.code !== 0) throw new Error(result.output || '题库读取失败，保留当前列表。');
      const data = JSON.parse(result.stdout);
      const lessons = data.lessons.map((lesson) => ({ ...lesson,
        manifestUri: vscode.Uri.file(lesson.manifestPath),
        statementUri: lesson.statement ? vscode.Uri.file(path.join(lesson.lessonDir, lesson.statement)) : undefined
      }));
      lessons.sort((a, b) => a.id.localeCompare(b.id));
      this.lessons = lessons;
      this.progress = data.progress;
      return lessons;
    }
    // Legacy-only fallback for development consumers without a training backend.
    const lessonPattern = new vscode.RelativePattern(this.rootUri.fsPath, 'content/**/lesson.json');
    const bankPattern = new vscode.RelativePattern(this.rootUri.fsPath, 'content/**/question-bank.json');
    const [manifestUris, bankUris] = await Promise.all([
      vscode.workspace.findFiles(lessonPattern, '**/{node_modules,.git}/**'),
      vscode.workspace.findFiles(bankPattern, '**/{node_modules,.git}/**')
    ]);
    const lessons = [];
    for (const manifestUri of manifestUris) {
      const manifest = await readJson(manifestUri);
      const lessonDir = path.dirname(manifestUri.fsPath);
      lessons.push({
        ...manifest,
        manifestUri,
        lessonDir,
        statementUri: manifest.statement ? vscode.Uri.file(path.join(lessonDir, manifest.statement)) : undefined
      });
    }
    for (const bankUri of bankUris) {
      const bank = await readJson(bankUri);
      for (const question of bank.questions || []) {
        lessons.push({
          ...(bank.defaults || {}),
          ...question,
          manifestUri: bankUri,
          lessonDir: path.dirname(bankUri.fsPath),
          statementUri: undefined
        });
      }
    }
    lessons.sort((left, right) => left.id.localeCompare(right.id));
    this.lessons = lessons;
    this.progress = await readJson(vscode.Uri.joinPath(this.rootUri, '.trainer', 'progress.json'), {});
    return lessons;
  }

  async reloadProgress() {
    let data;
    try {
      data = await readJson(vscode.Uri.joinPath(this.rootUri, '.trainer', 'progress.json'));
    } catch (error) {
      // An absent file means no attempts; invalid JSON/permissions must retain
      // the last good state rather than silently resetting the user's progress.
      if (error.code !== 'FileNotFound' && error.code !== 'ENOENT') throw error;
      data = {};
    }
    const progress = data && typeof data === 'object' && !Array.isArray(data) ? data : {};
    if (JSON.stringify(progress) === JSON.stringify(this.progress)) return false;
    this.progress = progress;
    return true;
  }

  get(id) {
    return this.lessons.find((lesson) => lesson.id === id);
  }

  status(id) {
    return this.progress[id] || { status: 'not-started', attempts: 0 };
  }
}

module.exports = { LessonCatalog };
