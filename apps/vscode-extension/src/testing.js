const vscode = require('vscode');
const { toCrlf } = require('./backend');

class TestingIntegration {
  constructor(context, executeLesson) {
    this.executeLesson = executeLesson;
    this.controller = vscode.tests.createTestController('embeddedTrainerTests', 'Embedded Trainer');
    context.subscriptions.push(this.controller);
    this.profile = this.controller.createRunProfile(
      '运行课程评测',
      vscode.TestRunProfileKind.Run,
      (request, token) => this.runRequest(request, token),
      true
    );
  }

  sync(lessons) {
    const items = lessons.filter((lesson) => ['programming', 'debugging'].includes(lesson.questionType)).map((lesson) => {
      const item = this.controller.createTestItem(lesson.id, lesson.title, lesson.statementUri);
      item.description = `${lesson.language.toUpperCase()} · ${lesson.difficulty}`;
      return item;
    });
    this.controller.items.replace(items);
  }

  getItem(id) {
    return this.controller.items.get(id);
  }

  async runLesson(id, externalToken) {
    const item = this.getItem(id);
    if (!item) {
      throw new Error(`测试资源管理器中没有课程 ${id}`);
    }
    const request = new vscode.TestRunRequest([item]);
    return this.runRequest(request, externalToken, true);
  }

  async runRequest(request, token, returnFirstResult = false) {
    const run = this.controller.createTestRun(request, 'Embedded Trainer 评测');
    const selected = request.include ? [...request.include] : [];
    if (!request.include) {
      this.controller.items.forEach((item) => selected.push(item));
    }
    let firstResult;
    for (const item of selected) {
      if (token && token.isCancellationRequested) {
        run.skipped(item);
        continue;
      }
      run.enqueued(item);
      run.started(item);
      const result = await this.executeLesson(item.id, token);
      firstResult = firstResult || result;
      if (result.output) {
        run.appendOutput(toCrlf(result.output), undefined, item);
      }
      if (result.code === 0) {
        run.passed(item, result.duration);
      } else if (result.code === -1) {
        run.errored(item, new vscode.TestMessage(result.output || '无法启动训练核心'), result.duration);
      } else {
        run.failed(item, new vscode.TestMessage(result.output || '评测未通过'), result.duration);
      }
    }
    run.end();
    return returnFirstResult ? firstResult : undefined;
  }
}

module.exports = { TestingIntegration };
