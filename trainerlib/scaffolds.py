"""Recognize retained upstream starters without editing or trusting arbitrary drafts."""
import re

from .common import HASH, PackError, digest, inside, read_json
from .format import payload_files


def starter_mode(root, q):
    """Only byte-identical, pinned official Exercism programming starters qualify.

    No manifest flag can bypass this check. Edited starters, AI derivatives,
    debugging exercises and other publishers retain the compilable-starter rule.
    """
    origin = q.get("origin", {})
    lang = q.get("language")
    prefix = f"oss.exercism.{lang}."
    qid = q.get("id", "")
    if (q.get("questionType") != "programming" or lang not in {"c", "cpp"}
            or not isinstance(origin, dict) or origin.get("type") not in {"imported", "adapted"}
            or origin.get("generator") or q.get("variantOf")
            or origin.get("repository") != f"https://github.com/exercism/{lang}"
            or origin.get("license") != "MIT" or not qid.startswith(prefix)
            or not re.fullmatch(r"[a-f0-9]{40}", origin.get("commit", ""))):
        return "compilable"
    slug = qid[len(prefix):]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return "compilable"
    try:
        sources = origin["sourceFiles"]
        by_path = {entry["path"]: entry for entry in sources}
        if len(by_path) != len(sources):
            return "compilable"
        base = f"exercises/practice/{slug}/"

        def retained(name):
            entry = by_path[base + name]
            data = inside(root, entry["retainedPath"]).read_bytes()
            if not HASH.fullmatch(entry["sha256"]) or digest(data) != entry["sha256"]:
                raise PackError("Retained starter source hash mismatch")
            return entry, data

        config, _ = retained(".meta/config.json")
        names = read_json(inside(root, config["retainedPath"]))["files"]["solution"]
        if not isinstance(names, list) or not names or len(names) != len(set(names)):
            return "compilable"
        actual = payload_files(inside(q["_lessonDir"], q["starter"]))
        if set(actual) != set(names):
            return "compilable"
        for name in names:
            entry, _ = retained(name)
            if actual[name] != entry["sha256"]:
                return "compilable"
        return "upstream-scaffold"
    except (PackError, OSError, KeyError, TypeError, ValueError):
        return "compilable"


def expected_scaffold_error(diagnostics):
    """Allow missing exercise interfaces, never toolchain/dependency/resource failures."""
    if re.search(r"fatal error:|internal compiler error|killed|out of memory|cannot allocate|"
                 r"no space left|permission denied|no such file|unrecognized command", diagnostics, re.I):
        return False
    return bool(re.search(r"undefined reference to|is not a member of|does not name a type|"
                          r"unknown type name|empty enum is invalid|empty translation unit|"
                          r"implicit declaration of function|undeclared|has not been declared", diagnostics))
