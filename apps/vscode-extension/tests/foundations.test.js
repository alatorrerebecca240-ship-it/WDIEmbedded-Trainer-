// Filesystem-backed catalog and render checks; no VS Code installation required.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const Module = require('node:module');
const { test } = require('node:test');
const root = path.resolve(__dirname, '../../..');
const uri = (fsPath) => ({ fsPath });

async function findFiles(directory, basename) {
  const result = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const name = path.join(directory, entry.name);
    if (entry.isDirectory()) result.push(...await findFiles(name, basename));
    else if (entry.name === basename) result.push(uri(name));
  }
  return result;
}

const vscode = {
  TreeItem: class { constructor(label) { this.label = label; } },
  ThemeIcon: class {}, ThemeColor: class {}, MarkdownString: class {},
  EventEmitter: class { fire() {} },
  TreeItemCollapsibleState: { Expanded: 2, Collapsed: 1, None: 0 },
  RelativePattern: class { constructor(base, pattern) { this.base = base; this.pattern = pattern; } },
  Uri: { file: uri, joinPath: (base, ...parts) => uri(path.join(base.fsPath, ...parts)) },
  workspace: {
    fs: { readFile: (item) => fs.readFile(item.fsPath) },
    findFiles: (pattern) => findFiles(path.join(pattern.base, 'content'), path.posix.basename(pattern.pattern))
  }
};
const originalLoad = Module._load;
let LessonCatalog, LessonTreeProvider, LessonDashboard;
try {
  Module._load = function (name, ...args) { return name === 'vscode' ? vscode : originalLoad.call(this, name, ...args); };
  ({ LessonCatalog } = require('../src/catalog'));
  ({ LessonTreeProvider } = require('../src/tree'));
  ({ LessonDashboard } = require('../src/dashboard'));
} finally {
  Module._load = originalLoad;
}

test('new tracks merge defaults, group four types and render knowledge labels', async () => {
  const catalog = new LessonCatalog(uri(root));
  await catalog.reload();
  const tree = new LessonTreeProvider(catalog);
  const tracks = tree.getChildren(tree.getChildren().find((item) => item.contextValue === 'library-root'));
  for (const [id, title] of [['linux-basics', 'Linux 基础'], ['ros2-basics', 'ROS 2 基础']]) {
    const track = tracks.find((item) => item.track === id);
    assert.equal(track.label, title);
    assert.equal(track.lessons.length, 32);
    const types = tree.getChildren(track);
    assert.deepEqual(types.map((item) => item.questionType), ['programming', 'single-choice', 'true-false', 'fill-blank']);
    assert.deepEqual(types.map((item) => item.lessons.length), [2, 12, 9, 9]);
    for (const group of types) {
      for (const item of tree.getChildren(group)) {
        const lesson = item.lesson;
        const dashboard = new LessonDashboard(() => {});
        dashboard.lesson = lesson;
        const html = dashboard.render();
        assert.ok(html.includes(title));
        if (lesson.questionType === 'programming') {
          assert.ok(html.includes('data-command="check"'));
          assert.ok(!html.includes('id="quiz-form"'));
        } else {
          assert.equal(lesson.language, 'text');
          assert.ok(item.description.startsWith('基础知识 ·'));
          assert.ok(html.includes('<span class="chip">基础知识</span>'));
          assert.ok(html.includes('id="quiz-form"'));
          assert.ok(!html.includes('data-command="check"'));
          assert.ok(!html.includes(lesson.quiz.explanation), 'do not leak explanations before submission');
        }
      }
    }
  }
  const dashboard = new LessonDashboard(() => {});
  dashboard.lesson = catalog.get('linux.shell.redirect-fill-01');
  assert.ok(dashboard.render().includes('2&gt;____'));
  dashboard.lesson = catalog.get('linux.shell.append-choice-01');
  assert.ok(dashboard.render().includes('&gt;&gt;'));
});
