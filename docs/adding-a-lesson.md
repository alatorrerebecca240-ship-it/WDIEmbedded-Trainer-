# 添加课程和题目

0.6.0 推荐将新题加入独立知识包，格式与发布步骤见 [知识包工作流](knowledge-pack-workflow.md)。当前 `trainer-packs.json` 已关闭旧 `content/` 的加载；以下旧格式说明仅供兼容参考，不能通过修改旧目录扩充当前正式列表。

现在支持 `programming`（编程）、`debugging`（纠错）、`single-choice`（单选）、`true-false`（判断）、`fill-blank`（填空）和 `code-reading`（代码阅读）。所有题目都使用 `schemaVersion: 1`，并拥有全局唯一 `id`。发布时还需要明确授权、保留来源、可验证的参考答案与人工审核。

## 添加编程题

在 `content/<track>/<slug>/` 下创建：

```text
lesson.json
README.md
starter/
tests/
```

`starter/` 是复制给学习者的初始代码，`tests/` 是评测代码。最小清单示例：

```json
{
  "$schema": "../../../schemas/lesson.schema.json",
  "schemaVersion": 1,
  "id": "embedded.uart.parser-01",
  "title": "解析串口数据帧",
  "track": "embedded",
  "language": "c",
  "questionType": "programming",
  "difficulty": "beginner",
  "summary": "实现一个无动态内存的串口帧解析器。",
  "prerequisites": [],
  "knowledge": ["uart", "state-machine"],
  "target": "simulator",
  "starter": "starter",
  "statement": "README.md",
  "build": {
    "standard": "c11",
    "sources": ["parser.c"],
    "tests": ["test_parser.c"],
    "includeDirs": ["."],
    "timeoutSeconds": 5
  },
  "hints": ["先画出状态转移图。"],
  "origin": { "type": "self-authored", "license": "project-license" }
}
```

初始代码应当可以编译，但至少有一项测试失败。提示应逐级增加信息量，最后一级也不应直接给出完整答案。

## 添加客观题

`language` 支持 `c`、`cpp` 和 `text`。Linux、ROS 2 等非特定编程语言的知识题使用 `text`，插件显示为“基础知识”；编程题只允许 `c` 或 `cpp`。题库内容和课程目录仍使用同一格式，后续无需引入数据库即可扩题。

同一方向的大量客观题适合集中放在 `content/<track>/question-bank.json`：

```json
{
  "$schema": "../../schemas/question-bank.schema.json",
  "schemaVersion": 1,
  "defaults": {
    "schemaVersion": 1,
    "track": "embedded",
    "language": "c",
    "target": "simulator",
    "prerequisites": [],
    "origin": { "type": "self-authored", "license": "project-license" }
  },
  "questions": []
}
```

`defaults` 会先与每道题合并，题目自身字段优先。适合把同一路线重复的 `track`、`language`、`target`、`prerequisites` 和 `origin` 集中配置，后续扩题只需填写差异字段。合并后，每道题都需要具有 `id`、`title`、`track`、`language`、`questionType`、`difficulty`、`summary`、`prerequisites`、`knowledge`、`target`、`hints` 和 `origin`。

单选题的 `quiz` 示例：

```json
{
  "prompt": "哪个运算符用于判断两个值相等？",
  "options": [
    { "id": "A", "text": "=" },
    { "id": "B", "text": "==" }
  ],
  "answer": "B",
  "explanation": "== 执行相等比较，= 执行赋值。"
}
```

判断题把 `quiz.answer` 写成 JSON 布尔值 `true` 或 `false`。填空题使用：

```json
{
  "prompt": "sizeof 的结果类型是 ____。",
  "blanks": [
    {
      "label": "类型名",
      "answers": ["size_t"],
      "caseSensitive": true
    }
  ],
  "explanation": "sizeof 返回 size_t。"
}
```

`answers` 可列出多个等价答案；默认忽略答案首尾空白与大小写。对 C 标识符和符号建议设置 `caseSensitive: true`。

Bash 命令、环境变量和 ROS 2 标识符也应按实际规则设置大小写；填空题建议只留一个命令名或符号，避免因整条命令的等价空格或引号写法误判。涉及系统与版本的题目请明确适用范围，给出官方参考，并说明知识题不会自动执行题干中的命令。

## 检查

```text
trainer validate
trainer smoke
python -m unittest discover -s tests -v
node --test apps/vscode-extension/tests/foundations.test.js
```

`validate` 检查字段、路径、ID 和答案配置；`smoke` 还会编译所有编程题的初始代码，并确认其初始测试处于失败状态。VS Code 插件会监视 `lesson.json` 和 `question-bank.json`，保存后自动刷新课程列表。
