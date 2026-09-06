"""Readable review evidence. This module never executes code or grants approval."""

from collections import Counter
import json
import re
from pathlib import Path
from urllib.parse import quote

from .common import PROGRAMMING, PackError, inside
from .format import fingerprint, load_pack


def fenced(text, language="text"):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, indent=2)
    fence = "`" * max(3, 1 + max((len(x) for x in re.findall(r"`+", text)), default=0))
    return f"{fence}{language}\n{text}\n{fence}\n"


def render_review(root, report, repository=None, commit=None, workspace=None):
    root = Path(root).resolve()
    manifest, questions = load_pack(root)
    sha = fingerprint(root)
    if report.get("packId") != manifest["id"] or report.get("contentSha256") != sha:
        raise PackError("Audit report does not match this exact package source")
    if repository is not None or commit is not None:
        if not (isinstance(repository, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
                and isinstance(commit, str) and re.fullmatch(r"[a-f0-9]{40}", commit)):
            raise PackError("Review links require a GitHub repository and full commit SHA")
    required = {q["id"] for q in questions if q["questionType"] in PROGRAMMING | {"code-reading"}}
    verified = report.get("referenceVerified", [])
    docker_passed = (report.get("passed") is True and report.get("runner") == "docker"
                     and not report.get("errors") and set(verified) == required)
    status = "Docker 验证通过，等待人工审核" if docker_passed else "未取得完整 Docker 通过证据，不可批准发布"
    lines = ["# 知识包人工审核材料", "", status, "",
             f"包：`{manifest['id']}@{manifest['version']}`", "",
             f"内容 SHA-256：`{sha}`", "",
             f"题目数量：{len(questions)}；需执行验证：{len(required)}；报告已验证：{len(verified)}。", "",
             "题型统计：", fenced(dict(sorted(Counter(q['questionType'] for q in questions).items())))]
    if commit:
        lines.extend([f"对应提交：`{commit}`", ""])
    lines.extend(["## 人工审核关口", "",
                  "本文件是自动生成的待审材料，不代表版权、教育内容或发布批准。机器测试不能证明题意正确或代码无缺陷。", "",
                  "- [ ] 检查题干、答案、解析、难度及适用范围。",
                  "- [ ] 检查编程题参考实现、测试边界及是否符合题目约定。",
                  "- [ ] 确认来源声明和许可证，并保留所需版权文本。",
                  "- [ ] 核对 Actions 提交和内容指纹后，由具名审核者明确批准该快照。", "",
                  "## 机器报告", "", fenced({key: report.get(key) for key in
                    ('runner', 'passed', 'errors', 'warnings', 'referenceVerified')}),
                  "## 逐题核对", ""])

    def asset(path):
        path = Path(path)
        if repository:
            relative = path.resolve().relative_to(Path(workspace).resolve()).as_posix()
            return f"[查看源文件](https://github.com/{repository}/blob/{commit}/{quote(relative, safe='/')})"
        return fenced(str(path))

    for q in questions:
        lines.extend([f"### {q['id']}", "", fenced(q['title']),
                      fenced({k: q.get(k) for k in ('track', 'questionType', 'difficulty', 'knowledge', 'prerequisites')}),
                      "来源与授权：", fenced(q.get("origin", {}))])
        if q["questionType"] in PROGRAMMING:
            lesson = q["_lessonDir"]
            statement = inside(lesson, q["statement"])
            lines.extend(["题目：", fenced(statement.read_text(encoding="utf-8"), "markdown")])
            for directory in (q.get("reference", "reference"), "tests"):
                source = inside(lesson, directory)
                for file in sorted(source.rglob("*")):
                    if file.is_file():
                        lines.extend([f"{directory} / {file.name}", "", asset(file), "",
                                      fenced(file.read_text(encoding="utf-8"), "cpp" if q["language"] == "cpp" else "c")])
        else:
            quiz = q["quiz"]
            lines.extend(["题干：", fenced(quiz["prompt"])])
            if quiz.get("code"):
                lines.extend(["代码：", fenced(quiz["code"], "cpp" if q["language"] == "cpp" else "c")])
            for option in quiz.get("options", []):
                lines.append(fenced(f"{option['id']}: {option['text']}"))
            if q["questionType"] in {"single-choice", "true-false"}:
                lines.extend(["参考答案：", fenced(quiz["answer"])])
            else:
                for i, blank in enumerate(quiz["blanks"], 1):
                    lines.extend([f"填空 {i} 的可接受答案：", fenced(blank["answers"])])
            lines.extend(["解析：", fenced(quiz["explanation"])])
    return "\n".join(lines) + "\n"
