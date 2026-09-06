"""Knowledge Pack v1: data-only, portable, fully indexed archives."""

import re
from pathlib import Path

from . import ENGINE_VERSION
from .common import HASH, ID, LICENSES, MAX_EXPANDED, MAX_FILES, PROGRAMMING, TYPES, PackError, canonical, digest, inside, read_json, safe_path, version


def payload_files(root):
    root = Path(root)
    result = {}
    folded_names = set()
    size = 0
    for file in sorted(root.rglob("*")):
        relative = file.relative_to(root).as_posix()
        inside(root, relative)
        if not file.is_file() or relative in {"pack.json", "review.json", "audit.json"}:
            continue
        if relative.casefold() in folded_names:
            raise PackError("Case-colliding payload filenames")
        folded_names.add(relative.casefold())
        if file.suffix.lower() not in {".json", ".md", ".txt", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh"}:
            raise PackError(f"Unsupported payload file (no scripts/binaries): {relative}")
        size += file.stat().st_size
        if size > MAX_EXPANDED or len(result) >= MAX_FILES:
            raise PackError("Package exceeds file/size limit")
        result[relative] = digest(file.read_bytes())
    return result


def fingerprint(root):
    manifest = read_json(Path(root) / "pack.json")
    manifest.pop("files", None)
    return digest(canonical({"manifest": manifest, "files": payload_files(root)}))


def validate_question(q, root):
    if not isinstance(q, dict) or q.get("schemaVersion") != 1:
        raise PackError("Question must be a schemaVersion=1 object")
    for field in ("id", "title", "track", "summary", "target"):
        if not isinstance(q.get(field), str) or not q[field].strip():
            raise PackError(f"Missing question field: {field}")
    if not ID.fullmatch(q["id"]):
        raise PackError("Invalid question ID")
    if q.get("language") not in {"c", "cpp", "text"} or q.get("questionType") not in TYPES:
        raise PackError("Unsupported language/question type")
    if q.get("difficulty") not in {"beginner", "intermediate", "advanced"}:
        raise PackError("Invalid difficulty")
    for field in ("knowledge", "hints", "prerequisites"):
        value = q.get(field)
        if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
            raise PackError(f"Invalid {field}")
        if field != "prerequisites" and not value:
            raise PackError(f"Empty {field}")
    asset = inside(root, q["assetRoot"]) if "assetRoot" in q else Path(root)
    if q["questionType"] in PROGRAMMING:
        if q["language"] not in {"c", "cpp"}:
            raise PackError("Programming/debugging requires c/cpp")
        for field in ("starter", "statement"):
            if not inside(asset, q.get(field)).exists():
                raise PackError(f"Missing {field} asset")
        build = q.get("build", {})
        standards = {"c": {"c11", "c17"}, "cpp": {"c++17", "c++20"}}
        if build.get("standard") not in standards[q["language"]]:
            raise PackError("Unsupported compiler standard")
        for group in ("sources", "tests"):
            names = build.get(group)
            if not isinstance(names, list) or (group == "tests" and not names):
                raise PackError(f"Missing build.{group}")
            for name in names:
                file = inside(inside(asset, q["starter"]) if group == "sources" else asset / "tests", name)
                if not file.is_file() or file.suffix not in {".c", ".cpp", ".cc", ".cxx"}:
                    raise PackError(f"Invalid source file: {name}")
        for name in build.get("includeDirs", ["."]):
            if name != ".":
                inside(asset, name)
        if any(lib != "m" for lib in build.get("linkLibraries", [])):
            raise PackError("Only portable libm linking is currently supported")
        timeout = build.get("timeoutSeconds", 5)
        if type(timeout) is not int or not 1 <= timeout <= 30:
            raise PackError("Invalid test timeout")
    else:
        quiz = q.get("quiz")
        if not isinstance(quiz, dict) or not isinstance(quiz.get("prompt"), str) or not quiz["prompt"].strip() or not isinstance(quiz.get("explanation"), str) or not quiz["explanation"].strip():
            raise PackError("Quiz needs prompt/explanation")
        if q["questionType"] == "single-choice":
            opts = quiz.get("options", [])
            if not isinstance(opts, list) or len(opts) < 2:
                raise PackError("Choice question needs options")
            ids = []
            for opt in opts:
                if not isinstance(opt, dict) or not isinstance(opt.get("id"), str) or not isinstance(opt.get("text"), str) or not opt["text"]:
                    raise PackError("Invalid option")
                ids.append(opt["id"])
            if len(set(ids)) != len(ids) or quiz.get("answer") not in ids:
                raise PackError("Invalid choice answer/duplicate option IDs")
        elif q["questionType"] == "true-false":
            if type(quiz.get("answer")) is not bool:
                raise PackError("Boolean answer required")
        else:
            blanks = quiz.get("blanks", [])
            if not isinstance(blanks, list) or not blanks:
                raise PackError("Fill/code-reading requires answer blanks")
            for blank in blanks:
                if not isinstance(blank, dict) or not isinstance(blank.get("answers"), list) or not blank["answers"] or any(not isinstance(a, str) or not a.strip() for a in blank["answers"]):
                    raise PackError("Missing blank answers")
            if q["questionType"] == "code-reading" and (q["language"] not in {"c", "cpp"} or not quiz.get("code")):
                raise PackError("Code reading requires C/C++ code")
    return {**q, "_lessonDir": asset, "_manifestPath": Path(root) / "questions.json"}


def load_pack(root, integrity=False, approved=False):
    root = Path(root)
    p = read_json(root / "pack.json")
    if not isinstance(p, dict) or p.get("formatVersion") != 1 or not ID.fullmatch(p.get("id", "")):
        raise PackError("Invalid pack manifest")
    version(p.get("version"))
    if version(p.get("minEngineVersion", "0.6.0")) > version(ENGINE_VERSION):
        raise PackError("This package needs a newer training engine")
    if not isinstance(p.get("title"), str) or not p["title"].strip() or not isinstance(p.get("license"), str):
        raise PackError("Pack needs title/license")
    if "minEngineVersion" not in p or set(p) - {"formatVersion", "id", "version", "title", "minEngineVersion", "license", "files"}:
        raise PackError("Pack manifest has missing/unsupported fields")
    data = read_json(root / "questions.json")
    if not isinstance(data, dict) or data.get("formatVersion") != 1:
        raise PackError("questions.json requires formatVersion=1")
    qs = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(qs, list) or not 1 <= len(qs) <= 5000:
        raise PackError("Package must have 1..5000 questions")
    lessons, ids = [], set()
    for q in qs:
        item = validate_question(q, root)
        if (isinstance(q.get("origin"), dict) and "dependencies" in q["origin"]
                and version(p["minEngineVersion"]) < (0, 8, 0)):
            raise PackError("Dependency provenance requires minEngineVersion 0.8.0 or later")
        if item["id"] in ids:
            raise PackError(f"Duplicate ID: {item['id']}")
        ids.add(item["id"])
        lessons.append(item)
    actual = payload_files(root)
    if integrity and p.get("files") != actual:
        raise PackError("Package file index/hash mismatch")
    if approved:
        review = read_json(root / "review.json")
        if review.get("approved") is not True or not review.get("reviewer") or review.get("contentSha256") != fingerprint(root):
            raise PackError("Missing, unapproved or stale review")
        if review.get("copyrightChecked") is not True or review.get("contentChecked") is not True:
            raise PackError("Copyright and content review are required")
    return p, lessons
