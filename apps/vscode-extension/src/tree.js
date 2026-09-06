const vscode = require('vscode');

const TRACK_NAMES = {
  'c-basics': 'C 语言基础',
  'cpp-basics': 'C++ 基础',
  embedded: '嵌入式基础',
  'smart-car': '智能车竞赛',
  'electronic-design': '电子设计竞赛',
  'linux-basics': 'Linux 基础',
  'ros2-basics': 'ROS 2 基础'
};

const LANGUAGE_NAMES = { c: 'C', cpp: 'C++', text: '基础知识' };

const STATUS_NAMES = {
  'not-started': '未开始',
  'in-progress': '进行中',
  passed: '已通过'
};

const DIFFICULTY_NAMES = {
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高级',
  project: '项目'
};

const QUESTION_TYPE_NAMES = {
  programming: '编程题',
  'single-choice': '选择题',
  'true-false': '判断题',
  'fill-blank': '填空题',
  'code-reading': '代码阅读题',
  debugging: '纠错题'
};

class TrackItem extends vscode.TreeItem {
  constructor(track, lessons, passed) {
    super(TRACK_NAMES[track] || track, vscode.TreeItemCollapsibleState.Expanded);
    this.track = track;
    this.lessons = lessons;
    this.id = `track:${track}`;
    this.description = `${lessons.length} 题 · ${passed} 已通过`;
    this.contextValue = 'track';
    this.iconPath = new vscode.ThemeIcon({
      'c-basics': 'code', 'cpp-basics': 'symbol-class', embedded: 'circuit-board',
      'smart-car': 'dashboard', 'electronic-design': 'pulse',
      'linux-basics': 'terminal', 'ros2-basics': 'hubot'
    }[track] || 'library');
  }
}

class QuestionTypeItem extends vscode.TreeItem {
  constructor(questionType, lessons, passed) {
    super(QUESTION_TYPE_NAMES[questionType] || questionType, vscode.TreeItemCollapsibleState.Collapsed);
    this.questionType = questionType;
    this.lessons = lessons;
    this.id = `type:${lessons[0].track}:${questionType}`;
    this.description = `${lessons.length} 题 · ${passed} 已通过`;
    this.contextValue = 'question-type';
    this.iconPath = new vscode.ThemeIcon(
      questionType === 'programming' ? 'code' : questionType === 'single-choice' ? 'list-selection' : questionType === 'true-false' ? 'checklist' : 'symbol-key'
    );
  }
}

class LessonItem extends vscode.TreeItem {
  constructor(lesson, progress) {
    super(lesson.title, vscode.TreeItemCollapsibleState.None);
    this.lesson = lesson;
    this.id = `lesson:${lesson.id}`;
    this.progress = progress;
    const status = progress.status || 'not-started';
    this.description = `${LANGUAGE_NAMES[lesson.language] || lesson.language} · ${DIFFICULTY_NAMES[lesson.difficulty] || lesson.difficulty} · ${STATUS_NAMES[status] || status}`;
    this.tooltip = `${lesson.title}\n\n${lesson.summary}\n\n课程 ID：${lesson.id}`;
    this.contextValue = `lesson-${lesson.questionType}-${status}`;
    this.iconPath = new vscode.ThemeIcon(
      status === 'passed' ? 'pass-filled' : status === 'in-progress' ? 'edit' : lesson.questionType === 'programming' ? 'code' : 'question',
      status === 'passed' ? new vscode.ThemeColor('testing.iconPassed') : undefined
    );
    this.command = {
      command: 'embeddedTrainer.dashboard',
      title: '查看课程',
      arguments: [lesson.id]
    };
  }
}

class LessonTreeProvider {
  constructor(catalog) {
    this.catalog = catalog;
    this.changed = new vscode.EventEmitter();
    this.onDidChangeTreeData = this.changed.event;
  }

  refresh() {
    this.changed.fire(undefined);
  }

  getTreeItem(item) {
    return item;
  }

  getChildren(item) {
    if (item?.contextValue === 'camp-home') return [];
    if (item?.contextValue === 'library-root') return this.trackItems();
    if (item instanceof TrackItem) {
      const groups = new Map();
      for (const lesson of item.lessons) {
        const group = groups.get(lesson.questionType) || [];
        group.push(lesson);
        groups.set(lesson.questionType, group);
      }
      const order = ['programming', 'single-choice', 'true-false', 'fill-blank', 'code-reading', 'debugging'];
      return [...groups.entries()]
        .sort((left, right) => order.indexOf(left[0]) - order.indexOf(right[0]))
        .map(([questionType, lessons]) => new QuestionTypeItem(questionType, lessons, this.passedCount(lessons)));
    }
    if (item instanceof QuestionTypeItem) {
      return item.lessons.map((lesson) => new LessonItem(lesson, this.catalog.status(lesson.id)));
    }
    if (item) {
      return [];
    }
    const home = new vscode.TreeItem('新生训练营 · 路线图', vscode.TreeItemCollapsibleState.None);
    home.id = 'camp:home'; home.contextValue = 'camp-home'; home.description = '从 C 到嵌入式';
    home.iconPath = new vscode.ThemeIcon('milestone');
    home.command = { command: 'embeddedTrainer.roadmap', title: '打开训练路线' };
    const library = new vscode.TreeItem('完整题库', vscode.TreeItemCollapsibleState.Collapsed);
    library.id = 'library:root'; library.contextValue = 'library-root'; library.iconPath = new vscode.ThemeIcon('library');
    library.description = `${this.catalog.lessons.length} 题 · ${this.passedCount(this.catalog.lessons)} 已通过`;
    return [home, library];
  }

  trackItems() {
    const groups = new Map();
    for (const lesson of this.catalog.lessons) {
      const group = groups.get(lesson.track) || [];
      group.push(lesson);
      groups.set(lesson.track, group);
    }
    return [...groups.entries()].map(([track, lessons]) => new TrackItem(track, lessons, this.passedCount(lessons)));
  }

  passedCount(lessons) {
    return lessons.filter((lesson) => this.catalog.status(lesson.id).status === 'passed').length;
  }
}

module.exports = { LessonTreeProvider, LessonItem, STATUS_NAMES, DIFFICULTY_NAMES, TRACK_NAMES, QUESTION_TYPE_NAMES, LANGUAGE_NAMES };
