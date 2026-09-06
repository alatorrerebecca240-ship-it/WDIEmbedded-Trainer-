"""Pinned GitHub acquisition + declarative conversion. Never imports upstream build scripts."""

import json
import os
import re
import shutil
import tempfile
import urllib.parse
from pathlib import Path

from .common import LICENSES, PackError, atomic_json, digest, download, inside, read_json
from .format import load_pack


def fetch_source(profile, destination, ref=None):
    repository = profile["repository"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise PackError("Invalid source repository")
    revision = ref or profile["ref"]
    if re.fullmatch(r"[a-f0-9]{40}", revision):
        commit = revision
    else:
        url = f"https://api.github.com/repos/{repository}/commits/{urllib.parse.quote(revision, safe='')}"
        commit = json.loads(download(url, 2 * 1024 * 1024, {"api.github.com"}))["sha"]
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise PackError("GitHub did not return a full commit SHA")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    target = inside(root, profile["id"] + "-" + commit)
    requested = list(dict.fromkeys([*profile["licenseFiles"], *profile.get("noticeFiles", []), *profile["files"]]))
    if target.exists():
        lock = read_json(target / "source.json")
        if (set(requested) != {item["path"] for item in lock["files"]}
                or lock["repository"] != "https://github.com/" + repository or lock["commit"] != commit
                or lock["declaredLicense"] != profile["license"]):
            raise PackError("Source profile changed; use a new output directory to preserve the locked snapshot")
        for item in lock["files"]:
            if digest(inside(target, item["path"]).read_bytes()) != item["sha256"]:
                raise PackError("Source cache was modified")
        return target
    if not 1 <= len(requested) <= 100:
        raise PackError("Fetch batches must contain 1..100 explicitly selected paths")
    with tempfile.TemporaryDirectory(prefix="fetch-", dir=root) as temp:
        stage = Path(temp)
        files = []
        for name in requested:
            output = inside(stage, name)
            url = f"https://raw.githubusercontent.com/{repository}/{commit}/{urllib.parse.quote(name, safe='/')}"
            data = download(url, 2 * 1024 * 1024, {"raw.githubusercontent.com"})
            data.decode("utf-8")  # No binary or opaque vendored blobs.
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            files.append({"path": name, "sha256": digest(data), "url": url})
        atomic_json(stage / "source.json", {"formatVersion": 1, "profile": profile["id"], "repository": "https://github.com/" + repository, "commit": commit, "declaredLicense": profile["license"], "licenseScope": profile["scope"], "licenseFiles": profile["licenseFiles"], "noticeFiles": profile.get("noticeFiles", []), "files": files})
        os.replace(stage, target)
        stage.mkdir()
    return target


def import_recipe(source, recipe, destination):
    """Recipe mappings are data, not Python/JS plugins; unsupported exercises need a recipe."""
    source = Path(source)
    lock = read_json(source / "source.json")
    if recipe.get("source") != lock["profile"]:
        raise PackError("Recipe belongs to another upstream profile")
    for entry in lock["files"]:
        if digest(inside(source, entry["path"]).read_bytes()) != entry["sha256"]:
            raise PackError("Source snapshot integrity failed")
    target = Path(destination)
    if target.exists():
        raise PackError("Draft destination already exists; choose a new folder")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="import-", dir=target.parent) as temp:
        stage = Path(temp)
        retained, license_files, notice_files = [], [], []
        for item in lock["files"]:
            is_license = item["path"] in lock["licenseFiles"]
            is_notice = item["path"] in lock.get("noticeFiles", [])
            relative = ("licenses/" if is_license or is_notice else "upstream/") + item["path"]
            if is_license or is_notice:
                relative += ".txt"
            out = inside(stage, relative)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(inside(source, item["path"]).read_bytes())
            if is_license:
                license_files.append(relative)
            elif is_notice:
                notice_files.append(relative)
            else:
                retained.append({"path": item["path"], "retainedPath": relative, "sha256": item["sha256"]})
        origin = {"type": "adapted", "license": lock["declaredLicense"], "repository": lock["repository"], "commit": lock["commit"], "licenseFiles": license_files, "noticeFiles": notice_files, "sourceFiles": retained, "modifications": recipe["modifications"]}
        authored = recipe.get("authoredLicense")
        if authored is not None:
            if (not isinstance(authored, dict) or authored.get("license") not in LICENSES
                    or not isinstance(authored.get("text"), str) or len(authored["text"]) < 30):
                raise PackError("Invalid explicit license for newly authored adaptations")
            authored_path = inside(stage, "licenses/PROJECT.txt")
            if authored_path.exists():
                raise PackError("Authored license must not overwrite upstream notices")
            authored_path.parent.mkdir(parents=True, exist_ok=True)
            authored_path.write_text(authored["text"], encoding="utf-8")
            origin["authoredLicense"] = authored["license"]
            origin["licenseFiles"] = [*license_files, "licenses/PROJECT.txt"]
        questions = []
        for entry in recipe["questions"]:
            q = {**entry["question"], "origin": origin}
            for name, value in entry.get("files", {}).items():
                out = inside(stage, name)
                out.parent.mkdir(parents=True, exist_ok=True)
                if out.exists():
                    raise PackError("Recipe attempts to replace retained provenance or another asset")
                if isinstance(value, dict):
                    if set(value) != {"upstream"} or value["upstream"] not in {v["path"] for v in lock["files"]}:
                        raise PackError("Invalid upstream mapping")
                    out.write_bytes(inside(source, value["upstream"]).read_bytes())
                elif isinstance(value, str):
                    out.write_text(value, encoding="utf-8")
                else:
                    raise PackError("Recipe files must be text or an upstream mapping")
            questions.append(q)
        atomic_json(stage / "pack.json", recipe["pack"])
        atomic_json(stage / "questions.json", {"formatVersion": 1, "questions": questions})
        (stage / "MODIFICATIONS.md").write_text(recipe["modifications"] + "\n\nUpstream: " + lock["repository"] + "\nCommit: " + lock["commit"] + "\n", encoding="utf-8")
        load_pack(stage)
        os.replace(stage, target)
        stage.mkdir()
    return {"destination": str(target), "questions": len(questions), "review": "pending", "commit": lock["commit"]}
