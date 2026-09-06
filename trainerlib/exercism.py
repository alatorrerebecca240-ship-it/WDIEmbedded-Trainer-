"""Exercism discovery and data-only batch import. No upstream scripts are run."""

import hashlib
import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .common import PackError, atomic_json, canonical, digest, download, inside, read_json, safe_path
from .exercism_curriculum import BOOST_LICENSE, PILOT
from .format import fingerprint, load_pack

SHA = re.compile(r"[a-f0-9]{40}\Z")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
LANGUAGES = ("c", "cpp")
CODE_SUFFIXES = {".c", ".h", ".cpp", ".hpp"}
MAX_BATCH = 50


def _progress(text):
    print(text, file=sys.stderr, flush=True)


def _json(data):
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise PackError("Invalid upstream JSON") from exc


def _git_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _validate_source(language, source):
    if (language not in LANGUAGES or not isinstance(source, dict)
            or source.get("repository") != f"exercism/{language}"
            or not isinstance(source.get("commit"), str) or not SHA.fullmatch(source["commit"])):
        raise PackError("Only pinned official Exercism C/C++ sources are supported")
    files = source.get("files")
    if not isinstance(files, dict) or len(files) > 50000:
        raise PackError("Invalid or oversized upstream tree")
    for name, entry in files.items():
        safe_path(name)
        if (not isinstance(entry, dict) or not isinstance(entry.get("sha"), str)
                or not SHA.fullmatch(entry["sha"]) or entry.get("mode") != "100644"
                or type(entry.get("size")) is not int or entry["size"] < 0):
            raise PackError("Invalid blob entry (scripts, links and submodules are not imported)")


def _blob(source, name, cache):
    safe_path(name)
    entry = source["files"].get(name)
    if not entry or entry["mode"] != "100644" or not 0 <= entry.get("size", 0) <= 2 * 1024 * 1024:
        raise PackError(f"Unsupported or missing source file: {name}")
    relative = f"{source['repository'].split('/')[1]}/{source['commit']}/{name}"
    target = inside(cache, relative)
    if target.exists():
        data = target.read_bytes()
    else:
        data = download(f"https://raw.githubusercontent.com/{source['repository']}/{source['commit']}/{name}",
                        2 * 1024 * 1024, {"raw.githubusercontent.com"})
    if _git_hash(data) != entry["sha"]:
        raise PackError(f"Pinned Git blob checksum mismatch: {name}")
    data.decode("utf-8")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        # Separate workers request distinct paths. Partial writes are never reused.
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            staging = Path(stream.name)
            stream.write(data)
        try:
            os.replace(staging, target)
        finally:
            staging.unlink(missing_ok=True)
    return data


def _catalog_result(index, output, offline=False):
    return {"index": str(Path(output).resolve()), "offline": offline,
            "sources": {lang: {"repository": v["repository"], "commit": v["commit"]} for lang, v in index["sources"].items()},
            "candidates": index["candidates"], "count": len(index["candidates"]),
            "recommendedCount": sum(q["recommended"] for q in index["candidates"])}


def read_index(path):
    index = read_json(path)
    if not isinstance(index, dict) or not isinstance(index.get("sources"), dict) or not index["sources"]:
        raise PackError("Invalid source index")
    body = {key: value for key, value in index.items() if key != "sha256"}
    if index.get("formatVersion") != 1 or digest(canonical(body)) != index.get("sha256"):
        raise PackError("Source index changed or is invalid; scan again")
    for language, source in index["sources"].items():
        _validate_source(language, source)
    if not isinstance(index.get("candidates"), list) or len(index["candidates"]) > 2000:
        raise PackError("Invalid candidate list")
    keys = set()
    for q in index["candidates"]:
        if (not isinstance(q, dict) or q.get("language") not in index["sources"]
                or not isinstance(q.get("slug"), str) or not SLUG.fullmatch(q["slug"])
                or q.get("key") != f"{q['language']}/{q['slug']}" or q["key"] in keys
                or q.get("commit") != index["sources"][q["language"]]["commit"]
                or not isinstance(q.get("title"), str) or not q["title"].strip()
                or q.get("difficulty") not in {"beginner", "intermediate", "advanced"}
                or not isinstance(q.get("topics"), list) or not q["topics"]
                or any(not isinstance(v, str) or not v for v in q["topics"])
                or type(q.get("recommended")) is not bool or type(q.get("supported")) is not bool):
            raise PackError("Invalid or duplicate candidate metadata")
        keys.add(q["key"])
    return index


def scan(output, cache, language="all", max_difficulty=3, refs=None, offline=False):
    if offline:
        return _catalog_result(read_index(output), output, True)
    if language not in (*LANGUAGES, "all") or not 1 <= max_difficulty <= 10:
        raise PackError("Invalid language or difficulty filter")
    index = {"formatVersion": 1, "sources": {}, "candidates": []}
    for lang in LANGUAGES if language == "all" else (language,):
        _progress(f"扫描 Exercism {lang}：固定上游提交并读取目录…")
        commit = (refs or {}).get(lang)
        if commit is None:
            commit = _json(download(f"https://api.github.com/repos/exercism/{lang}/commits/main", 1024 * 1024, {"api.github.com"}))["sha"]
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            raise PackError("A full 40-character upstream commit is required")
        tree = _json(download(f"https://api.github.com/repos/exercism/{lang}/git/trees/{commit}?recursive=1", 8 * 1024 * 1024, {"api.github.com"}))
        if tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
            raise PackError("Upstream tree is incomplete; no partial index was saved")
        files = {v["path"]: {key: v[key] for key in ("sha", "mode", "size")}
                 for v in tree["tree"] if v.get("type") == "blob" and v.get("mode") == "100644"}
        source = {"repository": f"exercism/{lang}", "commit": commit, "files": files}
        _validate_source(lang, source)
        config = _json(_blob(source, "config.json", cache))
        license_text = _blob(source, "LICENSE", cache).decode("utf-8")
        if "MIT License" not in license_text or "Permission is hereby granted" not in license_text:
            raise PackError("Upstream root license changed; manual inspection required")
        index["sources"][lang] = source
        for entry in config.get("exercises", {}).get("practice", []):
            slug, difficulty = entry.get("slug"), entry.get("difficulty")
            if not isinstance(slug, str) or not SLUG.fullmatch(slug):
                raise PackError("Invalid upstream exercise slug")
            if type(difficulty) is not int or difficulty > max_difficulty or entry.get("status") == "deprecated":
                continue
            base = f"exercises/practice/{slug}/"
            curated = PILOT.get((lang, slug))
            supported = all(base + name in files for name in (".meta/config.json", ".docs/instructions.md"))
            topics = curated["topics"] if curated else entry.get("topics") or entry.get("practices") or ["基础编程"]
            index["candidates"].append({"key": f"{lang}/{slug}", "language": lang, "slug": slug,
                "title": curated["title"] if curated else entry.get("name", slug), "upstreamTitle": entry.get("name", slug),
                "difficulty": curated["difficulty"] if curated else ("beginner" if difficulty <= 2 else "intermediate"),
                "upstreamDifficulty": difficulty, "topics": topics, "recommended": bool(curated and supported),
                "supported": supported, "reason": "" if supported else "缺少可识别的题面或文件清单",
                "commit": commit, "license": "MIT", "frameworkLicense": "MIT" if lang == "c" else "BSL-1.0"})
    index["sha256"] = digest(canonical(index))
    atomic_json(output, index)
    return _catalog_result(index, output)


def _safe_members(metadata, group, required=True):
    values = metadata.get("files", {}).get(group, [])
    if not isinstance(values, list) or len(values) > 20 or (required and not values):
        raise PackError(f"Missing/oversized metadata files.{group}")
    for name in values:
        safe_path(name)
        if Path(name).suffix not in CODE_SUFFIXES or (group != "example" and "/" in name):
            raise PackError(f"Unsupported layout in files.{group}: {name}")
        if group == "example" and not re.fullmatch(r"\.meta/example\.(c|h|cpp|hpp)", name):
            raise PackError("Custom reference layout needs a dedicated adapter")
    return values


def _enable_c_tests(text):
    # Only remove a standalone ignore statement, optionally followed by a comment.
    # Never rewrite assertions, control flow or arbitrary IGNORE_MESSAGE expressions.
    result, count = re.subn(r"(?m)^[ \t]*TEST_IGNORE\(\);[ \t]*(?://[^\r\n]*)?\r?$",
                            "    /* Trainer: enable this upstream test. */", text)
    if re.search(r"\bTEST_IGNORE(?:_MESSAGE)?\s*\(", result):
        raise PackError("Unrecognized ignored test; manual review is required")
    return result, count


def _write(root, name, data):
    target = inside(root, name)
    if target.exists():
        if target.read_bytes() == data:
            return
        raise PackError(f"Asset collision: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _convert(source, candidate, cache, stage):
    lang, slug = candidate["language"], candidate["slug"]
    base = f"exercises/practice/{slug}/"
    metadata_name = base + ".meta/config.json"
    metadata_data = _blob(source, metadata_name, cache)
    metadata = _json(metadata_data)
    solution = _safe_members(metadata, "solution")
    examples = _safe_members(metadata, "example")
    tests = _safe_members(metadata, "test")
    if len({Path(v).suffix for v in solution}) != len(solution):
        raise PackError("Multiple solution files with the same suffix need a dedicated mapping")
    if any(Path(v).suffix not in ({".c"} if lang == "c" else {".cpp"}) for v in tests):
        raise PackError("Unsupported test language")
    framework = (["test-framework/unity.c", "test-framework/unity.h", "test-framework/unity_internals.h"]
                 if lang == "c" else ["test/catch.hpp", "test/tests-main.cpp"])
    names = list(dict.fromkeys(["LICENSE", metadata_name, base + ".docs/instructions.md",
                               *[base + name for name in [*solution, *examples, *tests, *framework]]]))
    supplements = [base + ".docs/" + name for name in ("introduction.md", "instructions.append.md")
                   if base + ".docs/" + name in source["files"]]
    names.extend(supplements)
    # Preserve any license/NOTICE files beside the selected framework and exercise.
    for name in source["files"]:
        if name.startswith(base) and re.search(r"(?:^|/)(?:license[^/]*|notice[^/]*)$", name, re.I):
            if name not in names:
                names.append(name)
    if len(names) > 100:
        raise PackError("An exercise exceeds the 100-file acquisition limit")
    with ThreadPoolExecutor(max_workers=4) as workers:
        payload = dict(zip(names, workers.map(lambda name: _blob(source, name, cache), names)))
    if b"MIT License" not in payload["LICENSE"] or b"Permission is hereby granted" not in payload["LICENSE"]:
        raise PackError("Upstream root license changed; manual inspection required")
    marker = b"MIT License" if lang == "c" else b"Boost Software License, Version 1.0"
    if marker not in payload[base + framework[0]][:4096]:
        raise PackError("Test framework license changed; manual inspection required")
    license_path = f"licenses/exercism-{lang}.txt"
    _write(stage, license_path, payload["LICENSE"])
    retained, dependencies = [], []
    for name, data in payload.items():
        if name == "LICENSE":
            continue
        # Keep original paths including metadata; append .txt only for opaque notices.
        retained_name = f"upstream/{lang}/{name}"
        if Path(retained_name).suffix.lower() not in {".c", ".h", ".cpp", ".hpp", ".md", ".json", ".txt"}:
            retained_name += ".txt"
        _write(stage, retained_name, data)
        item = {"path": name, "retainedPath": retained_name, "sha256": digest(data)}
        (dependencies if lang == "cpp" and name == base + "test/catch.hpp" else retained).append(item)
    qid = f"oss.exercism.{lang}.{slug}"
    asset = f"lessons/{qid}"
    mappings = {Path(name).suffix: name for name in examples}
    for name in solution:
        _write(stage, f"{asset}/starter/{name}", payload[base + name])
        reference = mappings.get(Path(name).suffix, name)
        _write(stage, f"{asset}/reference/{name}", payload[base + reference])
    if set(mappings) - {Path(v).suffix for v in solution}:
        raise PackError("Reference cannot be mapped to starter layout")
    enabled = 0
    for name in tests:
        text = payload[base + name].decode("utf-8")
        if lang == "c":
            text, count = _enable_c_tests(text)
            enabled += count
        else:
            text = "#define EXERCISM_RUN_ALL_TESTS 1\n" + text
        _write(stage, f"{asset}/tests/{name}", text.encode("utf-8"))
    for name in framework:
        data = payload[base + name]
        if lang == "cpp" and name.endswith("tests-main.cpp"):
            # Catch2 v2 predates dynamically sized SIGSTKSZ in newer glibc.
            data = b"#define CATCH_CONFIG_NO_POSIX_SIGNALS\n" + data
        _write(stage, f"{asset}/tests/{name}", data)
    curated = PILOT.get((lang, slug))
    summary = curated["summary"] if curated else str(metadata.get("blurb") or candidate["upstreamTitle"])
    instructions = payload[base + ".docs/instructions.md"].decode("utf-8")
    if base + ".docs/introduction.md" in payload:
        instructions = payload[base + ".docs/introduction.md"].decode("utf-8") + "\n\n" + instructions
    if base + ".docs/instructions.append.md" in payload:
        instructions += "\n\n### 语言补充说明（原文）\n\n" + payload[base + ".docs/instructions.append.md"].decode("utf-8")
    description = (f"# {candidate['title']}\n\n> 未审核的导入草稿，不是已发布课程。\n\n"
                   f"## 学习目标\n\n{summary}\n\n知识点：{'、'.join(candidate['topics'])}。\n\n"
                   "## 实作要求\n\n保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；"
                   "本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。\n\n"
                   f"## 上游原题\n\n{instructions}\n\n## 来源\n\n"
                   f"https://github.com/{source['repository']}/tree/{source['commit']}/{base}\n\n"
                   "题目和参考实现：Exercism MIT；测试框架保留各自许可。\n")
    _write(stage, f"{asset}/README.md", description.encode("utf-8"))
    origin = {"type": "adapted", "license": "MIT", "repository": f"https://github.com/{source['repository']}",
              "commit": source["commit"], "licenseFiles": [license_path, "licenses/PROJECT.txt"], "sourceFiles": retained,
              "authoredLicense": "MIT", "modifications": "新增中文学习目标与知识点；按上游 metadata 映射初始/参考源码；保留完整原题、测试和测试框架。C 测试移除 TEST_IGNORE；C++ 启用 EXERCISM_RUN_ALL_TESTS 并关闭 Catch2 POSIX 信号捕获。不运行上游构建脚本。"}
    if dependencies:
        _write(stage, "licenses/BSL-1.0.txt", BOOST_LICENSE.encode("utf-8"))
        origin["dependencies"] = [{"type": "imported", "license": "BSL-1.0", "name": "Catch2",
            "repository": origin["repository"], "commit": origin["commit"], "licenseFiles": ["licenses/BSL-1.0.txt"],
            "sourceFiles": dependencies, "modifications": "Catch2 single-header framework retained unchanged from the pinned Exercism exercise."}]
    q = {"schemaVersion": 1, "id": qid, "title": candidate["title"], "track": "c-basics" if lang == "c" else "cpp-basics",
         "language": lang, "questionType": "programming", "difficulty": candidate["difficulty"], "summary": summary,
         "knowledge": candidate["topics"], "prerequisites": [], "hints": ["先阅读原题及测试中的函数签名，列出输入、输出和边界条件。"],
         "target": "native", "assetRoot": asset, "starter": "starter", "reference": "reference", "statement": "README.md",
         "build": {"standard": "c11" if lang == "c" else "c++17", "sources": [v for v in solution if Path(v).suffix in {".c", ".cpp"}],
                   "tests": [*tests, "test-framework/unity.c" if lang == "c" else "test/tests-main.cpp"],
                   "includeDirs": ["."], "linkLibraries": ["m"] if lang == "c" else [], "timeoutSeconds": 5}, "origin": origin}
    return q, {"id": qid, "key": candidate["key"], "enabledIgnoredTests": enabled,
               "reference": "retained, not executed", "starter": "upstream starter retained; compile/fail gate pending",
               "translation": "Chinese learning objective; original English statement retained"}


def import_batch(index_path, destination, cache, keys=None, recommended=False, project_license=None):
    index = read_index(index_path)
    candidates = {q["key"]: q for q in index["candidates"]}
    selected = list(dict.fromkeys(keys or []))
    if recommended:
        if selected:
            raise PackError("Choose explicit exercises OR the recommended pilot")
        selected = [key for key, q in candidates.items() if q["recommended"]]
    if not 1 <= len(selected) <= MAX_BATCH or any(key not in candidates for key in selected):
        raise PackError("Select 1..50 exercises from the saved source index")
    if any(not candidates[key]["supported"] for key in selected):
        raise PackError("Selection contains unsupported layouts")
    target = Path(destination).absolute()
    if target.exists():
        raise PackError("Draft already exists; choose a new folder (never overwrite reviewed content)")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,70}", target.name):
        raise PackError("Use a lowercase draft folder name containing letters, digits, dots or hyphens")
    safe_path(target.name)
    license_text = Path(project_license).read_bytes() if project_license else None
    if not license_text or b"MIT License" not in license_text:
        raise PackError("An explicit local MIT license file is required for authored adaptations")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exercism-import-", dir=target.parent) as name:
        stage = Path(name) / "pack"
        stage.mkdir()
        _write(stage, "licenses/PROJECT.txt", license_text)
        questions, entries = [], []
        for number, key in enumerate(selected, 1):
            _progress(f"导入 {number}/{len(selected)}：{key}（仅下载和转换，不执行）")
            candidate = candidates[key]
            q, entry = _convert(index["sources"][candidate["language"]], candidate, cache, stage)
            questions.append(q)
            entries.append(entry)
        atomic_json(stage / "pack.json", {"formatVersion": 1, "id": target.name, "version": "1.0.0",
                    "title": "Exercism C/C++ 基础练习（导入草稿）", "minEngineVersion": "0.8.0",
                    "license": "mixed" if any(q["language"] == "cpp" for q in questions) else "MIT"})
        atomic_json(stage / "questions.json", {"formatVersion": 1, "questions": questions})
        atomic_json(stage / "import-manifest.json", {"formatVersion": 1, "adapter": "exercism-v1", "sourceIndexSha256": index["sha256"],
                    "questions": entries, "approved": False, "execution": "not-run", "needsReview": ["copyright", "Chinese statement", "starter interfaces", "Docker reference and starter checks"]})
        _write(stage, "README.md", ("# Exercism 导入草稿\n\n未审核，未执行，不可发布。\n\n"
               "每题保留原题、初始代码、参考实现、原始测试、框架许可证及文件哈希。"
               "导入不表示初始代码可编译或参考答案已通过；请查看 import-manifest.json 并在 Actions Docker 验证。\n").encode("utf-8"))
        load_pack(stage)
        # Check provenance without running code or pretending execution passed.
        from .audit import copyright_errors
        for q in questions:
            errors = copyright_errors(q, stage)
            if errors:
                raise PackError(f"{q['id']}: " + "; ".join(errors))
        sha = fingerprint(stage)
        os.replace(stage, target)
    return {"destination": str(target), "questions": len(questions), "contentSha256": sha,
            "review": "pending", "execution": "not-run", "entries": entries}
