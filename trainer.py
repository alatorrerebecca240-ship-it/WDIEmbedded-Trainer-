#!/usr/bin/env python3
"""Embedded Trainer command-line core."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trainerlib.common import PROGRAMMING, PackError, TYPES
from trainerlib.runtime import configured_lessons, store_for


ROOT = Path(os.environ.get("TRAINER_PROJECT_ROOT", str(Path(__file__).resolve().parent))).resolve()
CONTENT_ROOT = ROOT / "content"
EXERCISES_ROOT = ROOT / "exercises"
STATE_ROOT = ROOT / ".trainer"
BUILD_ROOT = STATE_ROOT / "build"
PROGRESS_FILE = STATE_ROOT / "progress.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class TrainerError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TrainerError(f"文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise TrainerError(f"JSON 格式错误：{path}:{exc.lineno}:{exc.colno} {exc.msg}") from exc


def relative_path_is_safe(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def discover_lessons() -> dict[str, dict[str, Any]]:
    lessons: dict[str, dict[str, Any]] = {}
    legacy_enabled, packages = configured_lessons(ROOT)

    def register(manifest: Any, manifest_path: Path) -> None:
        if not isinstance(manifest, dict):
            raise TrainerError(f"课程描述必须是对象：{manifest_path}")
        lesson_id = manifest.get("id")
        if not isinstance(lesson_id, str) or not lesson_id:
            raise TrainerError(f"课程缺少 id：{manifest_path}")
        if lesson_id in lessons:
            raise TrainerError(f"课程 ID 重复：{lesson_id}")
        manifest["_manifestPath"] = manifest_path
        manifest["_lessonDir"] = manifest_path.parent
        lessons[lesson_id] = manifest

    for manifest_path in sorted(CONTENT_ROOT.rglob("lesson.json")) if legacy_enabled else []:
        register(read_json(manifest_path), manifest_path)
    for bank_path in sorted(CONTENT_ROOT.rglob("question-bank.json")) if legacy_enabled else []:
        bank = read_json(bank_path)
        questions = bank.get("questions") if isinstance(bank, dict) else None
        if not isinstance(questions, list):
            raise TrainerError(f"题库缺少 questions 数组：{bank_path}")
        defaults = bank.get("defaults", {})
        if not isinstance(defaults, dict):
            raise TrainerError(f"题库 defaults 必须是对象：{bank_path}")
        for question in questions:
            if not isinstance(question, dict):
                raise TrainerError(f"题库中的题目必须是对象：{bank_path}")
            register({**defaults, **question}, bank_path)
    for question in packages:
        if question["id"] in lessons:
            raise TrainerError(f"知识包题目 ID 与已有题目冲突：{question['id']}")
        lessons[question["id"]] = question
    return lessons


def validate_lesson(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lesson_dir: Path = manifest["_lessonDir"]
    required = {
        "schemaVersion": int,
        "id": str,
        "title": str,
        "track": str,
        "language": str,
        "questionType": str,
        "difficulty": str,
        "summary": str,
        "prerequisites": list,
        "knowledge": list,
        "target": str,
        "hints": list,
    }
    for key, expected in required.items():
        value = manifest.get(key)
        if not isinstance(value, expected):
            errors.append(f"{key} 必须是 {expected.__name__}")

    if manifest.get("schemaVersion") != 1:
        errors.append("当前仅支持 schemaVersion=1")
    if manifest.get("language") not in {"c", "cpp", "text"}:
        errors.append("language 必须是 c、cpp 或 text（基础知识题）")
    question_type = manifest.get("questionType")
    supported_types = TYPES
    if question_type not in supported_types:
        errors.append("questionType 必须是 programming、debugging、single-choice、true-false、fill-blank 或 code-reading")
    lesson_id = manifest.get("id", "")
    if isinstance(lesson_id, str) and not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", lesson_id):
        errors.append("id 只能包含小写字母、数字、点和连字符")

    if question_type in PROGRAMMING:
        if manifest.get("language") not in {"c", "cpp"}:
            errors.append("编程题的 language 必须是 c 或 cpp")
        for field, expected in (("starter", str), ("statement", str), ("build", dict)):
            if not isinstance(manifest.get(field), expected):
                errors.append(f"编程题的 {field} 必须是 {expected.__name__}")
        for field in ("starter", "statement"):
            value = manifest.get(field)
            if isinstance(value, str):
                if not relative_path_is_safe(value):
                    errors.append(f"{field} 必须是安全的相对路径")
                elif not (lesson_dir / value).exists():
                    errors.append(f"{field} 指向的文件不存在：{value}")

        build = manifest.get("build")
        if isinstance(build, dict):
            for key in ("standard", "sources", "tests"):
                if key not in build:
                    errors.append(f"build 缺少 {key}")
            for key in ("sources", "tests", "includeDirs", "linkLibraries"):
                values = build.get(key, [])
                if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                    errors.append(f"build.{key} 必须是字符串数组")
                    continue
                for value in values:
                    if not relative_path_is_safe(value):
                        errors.append(f"build.{key} 包含不安全路径：{value}")
            starter = manifest.get("starter")
            if isinstance(starter, str):
                for source in build.get("sources", []):
                    if relative_path_is_safe(source) and not (lesson_dir / starter / source).exists():
                        errors.append(f"源码不存在：{source}")
            for test in build.get("tests", []):
                if relative_path_is_safe(test) and not (lesson_dir / "tests" / test).exists():
                    errors.append(f"测试不存在：{test}")
    elif question_type in supported_types:
        quiz = manifest.get("quiz")
        if not isinstance(quiz, dict):
            errors.append("非编程题必须包含 quiz 对象")
        else:
            if not isinstance(quiz.get("prompt"), str) or not quiz.get("prompt"):
                errors.append("quiz.prompt 必须是非空字符串")
            if not isinstance(quiz.get("explanation"), str) or not quiz.get("explanation"):
                errors.append("quiz.explanation 必须是非空字符串")
            if question_type == "single-choice":
                options = quiz.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    errors.append("单选题至少需要两个选项")
                else:
                    option_ids = [item.get("id") for item in options if isinstance(item, dict)]
                    if len(option_ids) != len(options) or len(set(option_ids)) != len(option_ids):
                        errors.append("单选题选项必须具有唯一 id")
                    if quiz.get("answer") not in option_ids:
                        errors.append("单选题 answer 必须对应一个选项 id")
            elif question_type == "true-false" and not isinstance(quiz.get("answer"), bool):
                errors.append("判断题 quiz.answer 必须是布尔值")
            elif question_type in {"fill-blank", "code-reading"}:
                blanks = quiz.get("blanks")
                if not isinstance(blanks, list) or not blanks:
                    errors.append("填空题至少需要一个 blank")
                else:
                    for index, blank in enumerate(blanks, start=1):
                        answers = blank.get("answers") if isinstance(blank, dict) else None
                        if not isinstance(answers, list) or not answers or not all(isinstance(item, str) for item in answers):
                            errors.append(f"第 {index} 个填空必须提供 answers 字符串数组")
    return errors


def get_lesson(lesson_id: str) -> dict[str, Any]:
    lessons = discover_lessons()
    try:
        return lessons[lesson_id]
    except KeyError as exc:
        raise TrainerError(f"未知课程：{lesson_id}。使用 `trainer list` 查看课程。") from exc


def compiler_from_vscode(language: str) -> str | None:
    config_path = ROOT / ".vscode" / "c_cpp_properties.json"
    if not config_path.exists():
        return None
    try:
        config = read_json(config_path)
        compiler = config.get("configurations", [{}])[0].get("compilerPath")
    except (TrainerError, AttributeError, IndexError, TypeError):
        return None
    if not isinstance(compiler, str) or not Path(compiler).exists():
        return None
    if language == "cpp":
        candidate = re.sub(r"gcc(\.exe)?$", r"g++\1", compiler, flags=re.IGNORECASE)
        if Path(candidate).exists():
            return candidate
    return compiler


def find_compiler(language: str) -> str | None:
    env_name = "TRAINER_CC" if language == "c" else "TRAINER_CXX"
    configured = os.environ.get(env_name)
    if configured:
        resolved = shutil.which(configured) or (configured if Path(configured).exists() else None)
        if resolved:
            return str(resolved)
    names = ["gcc", "clang", "cc"] if language == "c" else ["g++", "clang++", "c++"]
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return compiler_from_vscode(language)


def command_display(parts: list[str]) -> str:
    def quote(part: str) -> str:
        return f'"{part}"' if any(char.isspace() for char in part) else part

    return " ".join(quote(part) for part in parts)


def safe_name(lesson_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", lesson_id)


def cmake_source_list(manifest: dict[str, Any]) -> list[str]:
    build = manifest["build"]
    return list(build["sources"]) + [f".trainer-tests/{item}" for item in build["tests"]]


def write_workspace_files(target: Path, manifest: dict[str, Any]) -> None:
    project = safe_name(manifest["id"])
    build = manifest["build"]
    cmake_language = "C" if manifest["language"] == "c" else "CXX"
    standard_property = "C_STANDARD" if manifest["language"] == "c" else "CXX_STANDARD"
    standard_number = re.sub(r"\D", "", build["standard"])
    sources = "\n  ".join(cmake_source_list(manifest))
    includes = build.get("includeDirs", ["."])
    include_line = "\n".join(
        f'target_include_directories(lesson_check PRIVATE "${{CMAKE_CURRENT_SOURCE_DIR}}/{item}")'
        for item in includes
    )
    libraries = build.get("linkLibraries", [])
    portable_libraries = [item for item in libraries if item != "m"]
    library_line = ""
    if portable_libraries:
        library_line += f"target_link_libraries(lesson_check PRIVATE {' '.join(portable_libraries)})\n"
    if "m" in libraries:
        library_line += "if(NOT MSVC)\n  target_link_libraries(lesson_check PRIVATE m)\nendif()\n"
    cmake = f"""cmake_minimum_required(VERSION 3.20)
project({project} LANGUAGES {cmake_language})

add_executable(lesson_check
  {sources}
)
set_target_properties(lesson_check PROPERTIES
  {standard_property} {standard_number}
  {standard_property}_REQUIRED YES
  {standard_property}_EXTENSIONS NO
)
{include_line}
{library_line}if(MSVC)
  target_compile_options(lesson_check PRIVATE /W4)
else()
  target_compile_options(lesson_check PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME {project} COMMAND lesson_check)
"""
    (target / "CMakeLists.txt").write_text(cmake, encoding="utf-8")
    presets = {
        "version": 3,
        "cmakeMinimumRequired": {"major": 3, "minor": 20, "patch": 0},
        "configurePresets": [
            {
                "name": "default",
                "displayName": "Embedded Trainer Debug",
                "binaryDir": "${sourceDir}/build",
                "cacheVariables": {"CMAKE_BUILD_TYPE": "Debug"},
            }
        ],
        "buildPresets": [{"name": "default", "configurePreset": "default"}],
        "testPresets": [
            {
                "name": "default",
                "configurePreset": "default",
                "output": {"outputOnFailure": True},
            }
        ],
    }
    (target / "CMakePresets.json").write_text(
        json.dumps(presets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata = {
        "lessonId": manifest["id"],
        "manifest": str(manifest["_manifestPath"]),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "packId": manifest.get("_packId"),
        "packVersion": manifest.get("_packVersion"),
        "packSha256": manifest.get("_packSha256"),
    }
    (target / ".trainer-lesson.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_progress() -> dict[str, Any]:
    if not PROGRESS_FILE.exists():
        return {}
    data = read_json(PROGRESS_FILE)
    return data if isinstance(data, dict) else {}


def save_progress(progress: dict[str, Any]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    temp = PROGRESS_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(PROGRESS_FILE)


def mark_started(lesson_id: str) -> None:
    progress = load_progress()
    item = progress.setdefault(lesson_id, {"attempts": 0})
    item.setdefault("startedAt", datetime.now(timezone.utc).isoformat())
    if item.get("status") != "passed":
        item["status"] = "in-progress"
    save_progress(progress)


def record_attempt(lesson_id: str, passed: bool, phase: str) -> None:
    progress = load_progress()
    item = progress.setdefault(lesson_id, {"attempts": 0})
    item.setdefault("startedAt", datetime.now(timezone.utc).isoformat())
    item["attempts"] = int(item.get("attempts", 0)) + 1
    item["status"] = "passed" if passed else "in-progress"
    item["lastPhase"] = phase
    item["lastRun"] = datetime.now(timezone.utc).isoformat()
    save_progress(progress)


def cmd_doctor(_: argparse.Namespace) -> int:
    lessons = discover_lessons()
    validation_errors = sum(len(validate_lesson(item)) for item in lessons.values())
    tools = [
        ("Python 3.9+", sys.executable, sys.version_info >= (3, 9), True),
        ("C compiler", find_compiler("c"), find_compiler("c") is not None, True),
        ("C++ compiler", find_compiler("cpp"), find_compiler("cpp") is not None, True),
        ("CMake", shutil.which("cmake"), shutil.which("cmake") is not None, False),
        ("CTest", shutil.which("ctest"), shutil.which("ctest") is not None, False),
        ("Git", shutil.which("git"), shutil.which("git") is not None, False),
    ]
    print("Embedded Trainer 环境检查\n")
    required_ok = True
    for label, value, ok, required in tools:
        marker = "OK" if ok else ("MISSING" if required else "OPTIONAL")
        print(f"[{marker:8}] {label}: {value or '-'}")
        if required and not ok:
            required_ok = False
    print(f"[{'OK' if validation_errors == 0 else 'ERROR':8}] 课程：{len(lessons)} 个，{validation_errors} 个结构错误")
    print("\n说明：CMake/CTest 为可选路径，trainer check 可直接调用编译器。")
    return 0 if required_ok and validation_errors == 0 else 1


def cmd_validate(_: argparse.Namespace) -> int:
    lessons = discover_lessons()
    total_errors = 0
    for lesson_id, manifest in lessons.items():
        errors = validate_lesson(manifest)
        if errors:
            total_errors += len(errors)
            print(f"[ERROR] {lesson_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[OK] {lesson_id}")
    if not lessons:
        print("没有发现课程。")
        return 1
    print(f"\n校验完成：{len(lessons)} 个课程，{total_errors} 个错误。")
    return 0 if total_errors == 0 else 1


def cmd_smoke(_: argparse.Namespace) -> int:
    """Compile every starter without creating learner workspaces or progress."""
    lessons = discover_lessons()
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    failures = 0
    for lesson_id, lesson in lessons.items():
        errors = validate_lesson(lesson)
        if errors:
            print(f"[ERROR] {lesson_id}: 课程结构无效")
            failures += 1
            continue
        if lesson.get("questionType") not in PROGRAMMING:
            print(f"[OK] {lesson_id}: 题目数据有效")
            continue
        if lesson.get("_needsTrust"):
            print(f"[ERROR] {lesson_id}: 知识包代码尚未获准执行；不会运行初始测试")
            failures += 1
            continue
        with tempfile.TemporaryDirectory(prefix=f"smoke-{safe_name(lesson_id)}-", dir=STATE_ROOT) as temp_name:
            workspace = Path(temp_name)
            shutil.copytree(lesson["_lessonDir"] / lesson["starter"], workspace, dirs_exist_ok=True)
            shutil.copytree(lesson["_lessonDir"] / "tests", workspace / ".trainer-tests")
            executable = workspace / ("lesson_test.exe" if os.name == "nt" else "lesson_test")
            command = compile_command(lesson, workspace, executable)
            compiled = subprocess.run(
                command, cwd=workspace, text=True, capture_output=True,
                encoding="utf-8", errors="replace"
            )
            if compiled.returncode != 0:
                print(f"[ERROR] {lesson_id}: 初始代码无法编译")
                if compiled.stdout:
                    print(compiled.stdout, end="")
                if compiled.stderr:
                    print(compiled.stderr, end="", file=sys.stderr)
                failures += 1
                continue
            timeout = int(lesson["build"].get("timeoutSeconds", 5))
            try:
                tested = subprocess.run(
                    [str(executable)], cwd=workspace, text=True, capture_output=True,
                    encoding="utf-8", errors="replace", timeout=timeout
                )
                state = "初始测试已通过" if tested.returncode == 0 else "初始测试失败（符合练习预期）"
                print(f"[OK] {lesson_id}: 编译成功，{state}")
            except subprocess.TimeoutExpired:
                print(f"[ERROR] {lesson_id}: 初始测试超时")
                failures += 1
    print(f"\n冒烟检查完成：{len(lessons)} 个课程，{failures} 个错误。")
    return 0 if failures == 0 else 1


def cmd_list(args: argparse.Namespace) -> int:
    lessons = discover_lessons()
    progress = load_progress()
    rows = []
    for lesson_id, item in lessons.items():
        rows.append(
            {
                "id": lesson_id,
                "title": item["title"],
                "track": item["track"],
                "language": item["language"],
                "questionType": item["questionType"],
                "difficulty": item["difficulty"],
                "status": progress.get(lesson_id, {}).get("status", "not-started"),
            }
        )
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print(f"{'ID':38} {'类型':14} {'语言':5} {'难度':12} {'状态':12} 标题")
    print("-" * 110)
    for row in rows:
        print(
            f"{row['id'][:38]:38} {row['questionType'][:14]:14} {row['language']:5} {row['difficulty'][:12]:12} "
            f"{row['status'][:12]:12} {row['title']}"
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    lesson = get_lesson(args.lesson_id)
    if lesson.get("questionType") in PROGRAMMING:
        statement = lesson["_lessonDir"] / lesson["statement"]
        print(statement.read_text(encoding="utf-8"))
    else:
        quiz = lesson["quiz"]
        print(f"# {lesson['title']}\n\n{quiz['prompt']}")
        for option in quiz.get("options", []):
            print(f"{option['id']}. {option['text']}")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    lesson = get_lesson(args.lesson_id)
    if lesson.get("questionType") not in PROGRAMMING:
        raise TrainerError("选择题、判断题和填空题请使用 submit 提交答案，不需要创建代码工作区。")
    errors = validate_lesson(lesson)
    if errors:
        raise TrainerError("课程结构无效：\n- " + "\n- ".join(errors))
    target = EXERCISES_ROOT / lesson["id"]
    if target.exists():
        mark_started(lesson["id"])
        print(f"练习已经存在：{target}")
        print("框架不会自动覆盖你的代码。")
        return 0
    EXERCISES_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(lesson["_lessonDir"] / lesson["starter"], target)
    shutil.copytree(lesson["_lessonDir"] / "tests", target / ".trainer-tests")
    (target / "README.md").write_text(
        (lesson["_lessonDir"] / lesson["statement"]).read_text(encoding="utf-8"), encoding="utf-8"
    )
    write_workspace_files(target, lesson)
    mark_started(lesson["id"])
    print(f"已创建练习：{target}")
    print(f"编辑后运行：trainer check {lesson['id']}")
    return 0


def compile_command(manifest: dict[str, Any], workspace: Path, output: Path) -> list[str]:
    language = manifest["language"]
    compiler = find_compiler(language)
    if not compiler:
        variable = "TRAINER_CC" if language == "c" else "TRAINER_CXX"
        raise TrainerError(f"没有找到 {language} 编译器。请安装 GCC/Clang，或设置 {variable}。")
    build = manifest["build"]
    sources = [str(workspace / item) for item in build["sources"]]
    sources += [str(workspace / ".trainer-tests" / item) for item in build["tests"]]
    includes = [str(workspace / item) for item in build.get("includeDirs", ["."])]
    compiler_name = Path(compiler).name.lower()
    if compiler_name in {"cl", "cl.exe"}:
        standard = "/std:c++17" if language == "cpp" else "/std:c11"
        return [compiler, "/nologo", "/W4", standard, *sources, *[f"/I{item}" for item in includes], f"/Fe:{output}"]
    command = [compiler, f"-std={build['standard']}", "-Wall", "-Wextra", "-Wpedantic", "-g"]
    command += [f"-I{item}" for item in includes]
    command += sources
    command += ["-o", str(output)]
    command += [f"-l{item}" for item in build.get("linkLibraries", [])]
    return command


def cmd_check(args: argparse.Namespace) -> int:
    lesson = get_lesson(args.lesson_id)
    if lesson.get("questionType") not in PROGRAMMING:
        raise TrainerError("该课程不是编程题，请使用 submit 提交答案。")
    workspace = EXERCISES_ROOT / lesson["id"]
    if not workspace.exists():
        raise TrainerError(f"练习尚未创建。先运行：trainer start {lesson['id']}")
    metadata_file = workspace / ".trainer-lesson.json"
    if metadata_file.exists():
        metadata = read_json(metadata_file)
        if metadata.get("packId") and metadata.get("packSha256") != lesson.get("_packSha256"):
            from trainerlib.format import load_pack
            store = store_for(ROOT)
            index = store.index()
            old_version = metadata["packVersion"]
            old_entry = index["versions"].get(metadata["packId"], {}).get(old_version, {})
            if old_entry.get("sha256") != metadata.get("packSha256"):
                raise TrainerError("练习属于其他题库快照，已保留你的代码。请回退对应知识包，或备份后另开新练习。")
            _, old_questions = load_pack(store.location(metadata["packId"], old_version), integrity=True, approved=True)
            old = next((q for q in old_questions if q["id"] == lesson["id"]), None)
            if old is None:
                raise TrainerError("旧题库快照中找不到这道题。")
            lesson = {**old, "_packId": metadata["packId"], "_packVersion": old_version, "_packSha256": old_entry["sha256"], "_needsTrust": old_entry["sha256"] not in index.get("trusted", {}).get(metadata["packId"], [])}
            print(f"使用练习固定的知识包版本：{old_version}（不覆盖现有源码或测试）")
    if lesson.get("_needsTrust"):
        raise TrainerError(f"知识包 {lesson['_packId']} 的代码尚未获准在本机运行。请在插件中使用“信任知识包代码”确认该版本；下载校验不等于代码安全。")
    output_dir = BUILD_ROOT / safe_name(lesson["id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    executable = output_dir / ("lesson_test.exe" if os.name == "nt" else "lesson_test")
    command = compile_command(lesson, workspace, executable)
    print("编译：", command_display(command))
    compiled = subprocess.run(command, cwd=workspace, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if compiled.stdout:
        print(compiled.stdout, end="")
    if compiled.stderr:
        print(compiled.stderr, end="", file=sys.stderr)
    if compiled.returncode != 0:
        record_attempt(lesson["id"], False, "compile")
        print("\n[FAILED] 编译失败。")
        return 2
    timeout = int(lesson["build"].get("timeoutSeconds", 5))
    print(f"运行测试：{executable}")
    try:
        tested = subprocess.run(
            [str(executable)], cwd=workspace, text=True, capture_output=True,
            encoding="utf-8", errors="replace", timeout=timeout
        )
    except subprocess.TimeoutExpired:
        record_attempt(lesson["id"], False, "timeout")
        print(f"\n[FAILED] 测试超过 {timeout} 秒。")
        return 3
    if tested.stdout:
        print(tested.stdout, end="")
    if tested.stderr:
        print(tested.stderr, end="", file=sys.stderr)
    passed = tested.returncode == 0
    record_attempt(lesson["id"], passed, "test")
    print("\n[PASSED] 课程测试全部通过。" if passed else "\n[FAILED] 测试未通过，请修改代码后重试。")
    return 0 if passed else 1


def normalize_blank(value: str, case_sensitive: bool) -> str:
    normalized = value.strip()
    return normalized if case_sensitive else normalized.casefold()


def evaluate_quiz(lesson: dict[str, Any], answer: Any) -> bool:
    question_type = lesson["questionType"]
    quiz = lesson["quiz"]
    if question_type == "single-choice":
        return isinstance(answer, str) and answer == quiz["answer"]
    if question_type == "true-false":
        return isinstance(answer, bool) and answer is quiz["answer"]
    if question_type in {"fill-blank", "code-reading"}:
        blanks = quiz["blanks"]
        if not isinstance(answer, list) or len(answer) != len(blanks):
            return False
        for supplied, blank in zip(answer, blanks):
            if not isinstance(supplied, str):
                return False
            case_sensitive = bool(blank.get("caseSensitive", False))
            actual = normalize_blank(supplied, case_sensitive)
            expected = {normalize_blank(item, case_sensitive) for item in blank["answers"]}
            if actual not in expected:
                return False
        return True
    raise TrainerError("编程题不能使用 submit 提交答案。")


def cmd_submit(args: argparse.Namespace) -> int:
    lesson = get_lesson(args.lesson_id)
    if lesson.get("questionType") in PROGRAMMING:
        raise TrainerError("编程题请使用 check 运行评测。")
    try:
        answer = json.loads(args.answer)
    except json.JSONDecodeError as exc:
        raise TrainerError(f"答案不是有效 JSON：{exc.msg}") from exc
    passed = evaluate_quiz(lesson, answer)
    record_attempt(lesson["id"], passed, "quiz")
    if passed:
        print("[PASSED] 回答正确。")
        print(f"解析：{lesson['quiz']['explanation']}")
        return 0
    print("[FAILED] 回答错误，请重新思考或查看分级提示。")
    return 1


def cmd_hint(args: argparse.Namespace) -> int:
    lesson = get_lesson(args.lesson_id)
    hints = lesson.get("hints", [])
    level = args.level
    if level < 1 or level > len(hints):
        raise TrainerError(f"提示级别范围是 1..{len(hints)}")
    print(f"提示 {level}/{len(hints)}：{hints[level - 1]}")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    progress = load_progress()
    if args.json:
        print(json.dumps(progress, ensure_ascii=False, indent=2))
        return 0
    if not progress:
        print("还没有训练记录。")
        return 0
    for lesson_id, item in sorted(progress.items()):
        print(f"{lesson_id}: {item.get('status')}，尝试 {item.get('attempts', 0)} 次，最后阶段 {item.get('lastPhase')}")
    return 0


def cmd_catalog(_: argparse.Namespace) -> int:
    lessons = []
    for question in discover_lessons().values():
        lessons.append({**{k: v for k, v in question.items() if not k.startswith("_")},
                        "lessonDir": str(question["_lessonDir"]),
                        "manifestPath": str(question["_manifestPath"]),
                        "packId": question.get("_packId"),
                        "packVersion": question.get("_packVersion"),
                        "packSha256": question.get("_packSha256"),
                        "needsTrust": question.get("_needsTrust", False)})
    print(json.dumps({"lessons": lessons, "progress": load_progress()}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trainer", description="C/C++ 嵌入式训练框架")
    commands = parser.add_subparsers(dest="command", required=True)
    from trainerlib.cli import add_commands
    add_commands(commands)

    catalog = commands.add_parser("catalog", help="输出统一题库数据供插件读取")
    catalog.set_defaults(handler=cmd_catalog)

    doctor = commands.add_parser("doctor", help="检查环境")
    doctor.set_defaults(handler=cmd_doctor)

    validate = commands.add_parser("validate", help="校验课程")
    validate.set_defaults(handler=cmd_validate)

    smoke = commands.add_parser("smoke", help="编译全部课程的初始代码")
    smoke.set_defaults(handler=cmd_smoke)

    list_parser = commands.add_parser("list", help="列出课程")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(handler=cmd_list)

    show = commands.add_parser("show", help="显示课程说明")
    show.add_argument("lesson_id")
    show.set_defaults(handler=cmd_show)

    start = commands.add_parser("start", help="创建练习工作区")
    start.add_argument("lesson_id")
    start.set_defaults(handler=cmd_start)

    check = commands.add_parser("check", help="编译并测试练习")
    check.add_argument("lesson_id")
    check.set_defaults(handler=cmd_check)

    submit = commands.add_parser("submit", help="提交选择、判断或填空题答案")
    submit.add_argument("lesson_id")
    submit.add_argument("--answer", required=True, help="JSON 格式答案")
    submit.set_defaults(handler=cmd_submit)

    hint = commands.add_parser("hint", help="显示分级提示")
    hint.add_argument("lesson_id")
    hint.add_argument("level", nargs="?", type=int, default=1)
    hint.set_defaults(handler=cmd_hint)

    progress = commands.add_parser("progress", help="显示学习进度")
    progress.add_argument("--json", action="store_true")
    progress.set_defaults(handler=cmd_progress)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return int(args.handler(args))
    except (TrainerError, PackError, OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
