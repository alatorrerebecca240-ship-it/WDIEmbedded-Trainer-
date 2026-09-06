"""Knowledge package authoring, publication and consumer commands."""

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from . import ENGINE_VERSION
from .acquire import fetch_source, import_recipe
from .audit import approve, audit, build
from .common import PROGRAMMING, PackError, atomic_json, digest, inside, read_json
from .format import fingerprint, load_pack
from .generate import ai_variants, template_variants
from .runtime import store_for
from .store import PackStore


def migrate(legacy, destination, pack_id="foundation.core"):
    target = Path(destination)
    if target.exists():
        raise PackError("Migration destination exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="migration-", dir=target.parent) as temp:
        stage = Path(temp) / "pack"
        result = _migrate_into(legacy, stage, pack_id)
        os.replace(stage, target)
    return {**result, "destination": str(target)}


def _migrate_into(legacy, destination, pack_id):
    """Non-destructive export. Original lessons and learner progress are never rewritten."""
    legacy, target = Path(legacy), Path(destination)
    if target.exists():
        raise PackError("Migration destination exists")
    target.mkdir(parents=True)
    questions = []
    for path in sorted(legacy.rglob("lesson.json")):
        q = read_json(path)
        q.pop("$schema", None)
        q["assetRoot"] = "lessons/" + q["id"]
        asset = inside(target, q["assetRoot"])
        asset.mkdir(parents=True)
        for name in (q["starter"], "tests"):
            shutil.copytree(inside(path.parent, name), inside(asset, name))
        shutil.copy2(inside(path.parent, q["statement"]), inside(asset, q["statement"]))
        questions.append(q)
    for path in sorted(legacy.rglob("question-bank.json")):
        bank = read_json(path)
        for question in bank["questions"]:
            questions.append({**bank.get("defaults", {}), **question})
    atomic_json(target / "pack.json", {"formatVersion": 1, "id": pack_id, "version": "1.0.0", "title": "基础课程合集", "minEngineVersion": ENGINE_VERSION, "license": "LicenseRef-Pending"})
    atomic_json(target / "questions.json", {"formatVersion": 1, "questions": questions})
    (target / "README.md").write_text("# 基础课程合集\n\n由旧 content/ 无损导出。ID 不变，旧进度继续适用。\n\n当前为本地可编辑来源，不是已审核的公开发布包。原创授权、许可证文件和编程题参考实现需补齐后才能通过发布门禁。\n", encoding="utf-8")
    load_pack(target)
    return {"destination": str(target), "questions": len(questions), "review": "pending"}


def make_catalog(entries, repository, tag, destination):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"[A-Za-z0-9_.-]+", tag):
        raise PackError("Invalid repository/tag")
    packages = []
    for entry in entries:
        packages.append({k: v for k, v in {**entry, "url": f"https://github.com/{repository}/releases/download/{tag}/{entry['filename']}"}.items() if k != "filename"})
    result = {"formatVersion": 1, "repository": repository, "releaseTag": tag, "packages": packages}
    PackStore.validate_catalog(result)
    atomic_json(destination, result)
    return result


def handle(args):
    import trainer  # Authoring may reuse compiler discovery, but format/store never depend on the UI.
    root = trainer.ROOT
    store = store_for(root)
    compilers = {key: trainer.find_compiler(key) for key in ("c", "cpp")}
    action = args.pack_action
    if action in {"install", "sync", "rollback"}:
        store.reserved_questions = {q["id"]: q.get("_packId", "legacy") for q in trainer.discover_lessons().values()}
    if getattr(args, "runner", None) == "native" and not getattr(args, "trust_code", False):
        raise PackError("Native execution is NOT a sandbox. Pass --trust-code only after reviewing all input code, or use Docker.")
    if action == "list":
        result = store.index()
    elif action == "migrate":
        result = migrate(args.source, args.destination, args.id)
    elif action == "audit":
        result = audit(args.path, args.runner, compilers, args.against)
        if args.report:
            atomic_json(args.report, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    elif action == "review":
        if not (args.ack_copyright and args.ack_content):
            raise PackError("Reviewer must explicitly acknowledge copyright and educational content checks")
        result = approve(args.path, args.reviewer, args.runner, compilers,
                         read_json(args.verification_report) if args.verification_report else None)
    elif action == "build":
        result = build(args.path, args.output, args.runner, compilers)
        atomic_json(Path(args.output) / (result["filename"] + ".entry.json"), result)
    elif action == "promote":
        load_pack(args.path, approved=True)
        destination = Path(args.destination)
        if destination.exists():
            raise PackError("Approved destination exists; do not overwrite a released source")
        shutil.copytree(args.path, destination)
        result = {"destination": str(destination), "review": "approved snapshot retained; publication will rerun all gates"}
    elif action == "stage-catalog":
        data = read_json(args.path)
        PackStore.validate_catalog(data)
        atomic_json(Path(args.destination) / "catalog.json", data)
        result = {"destination": args.destination}
    elif action == "publish-bundle":
        # Build every source package; never silently omit a package with failed gates.
        packs = sorted(Path(args.source).glob("*/pack.json"))
        if not packs:
            raise PackError("No source packages selected for publication")
        package_ids, question_ids = set(), set()
        for path in packs:
            manifest, questions = load_pack(path.parent, approved=True)
            if manifest["id"] in package_ids or question_ids.intersection(q["id"] for q in questions):
                raise PackError("Publication bundle contains duplicate package/question IDs")
            package_ids.add(manifest["id"])
            question_ids.update(q["id"] for q in questions)
        entries = [build(p.parent, args.output, args.runner, compilers,
                         against=[other.parent for other in packs if other != p]) for p in packs]
        result = make_catalog(entries, args.repository, args.tag, Path(args.output) / "catalog.json")
    elif action == "install":
        result = store.install(args.archive, args.sha256)
    elif action == "rollback":
        store.rollback(args.id, args.version)
        result = {"id": args.id, "version": args.version, "pinned": True}
    elif action == "unpin":
        store.unpin(args.id)
        result = {"id": args.id, "pinned": False}
    elif action == "trust":
        if not args.trust_code:
            raise PackError("Explicit --trust-code acknowledgement is required")
        store.trust(args.id, args.sha256)
        result = {"trusted": args.id, "sha256": args.sha256}
    elif action in {"updates", "sync"}:
        result = store.updates(args.catalog, args.offline)
        if action == "sync":
            installed = []
            for item in result["packages"]:
                selected = item["id"] == args.id if args.id else item["updateAvailable"] and not item["pinned"]
                if selected:
                    installed.append(store.fetch_install(args.catalog, item))
            if args.id and not installed:
                raise PackError("Requested package not found or belongs to another source")
            result["installed"] = installed
    elif action == "fetch":
        profiles = read_json(args.profiles)["sources"]
        selected = profiles if args.source == "all" else [p for p in profiles if p["id"] == args.source]
        if not selected:
            raise PackError("Unknown source profile")
        result = []
        for profile in selected:
            location = fetch_source(profile, args.output, args.ref)
            result.append({"source": profile["id"], "directory": str(location)})
    elif action == "import":
        result = import_recipe(args.source, read_json(args.recipe), args.destination)
    elif action == "generate":
        result = template_variants(read_json(args.template), args.destination, args.count, args.seed)
    elif action == "ai":
        result = ai_variants(args.path, args.question, args.model, args.count, args.endpoint)
    else:
        raise PackError("Unknown package action")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def add_commands(commands):
    parser = commands.add_parser("packs", help="知识包：导入、验证、发布、更新与回退")
    actions = parser.add_subparsers(dest="pack_action", required=True)
    for name in ("list", "migrate", "audit", "review", "build", "promote", "stage-catalog", "publish-bundle", "install", "rollback", "unpin", "trust", "updates", "sync", "fetch", "import", "generate", "ai"):
        p = actions.add_parser(name)
        p.set_defaults(handler=handle)
        if name in {"audit", "review", "build", "publish-bundle"}:
            p.add_argument("--runner", choices=["none", "native", "docker"], default="none")
            p.add_argument("--trust-code", action="store_true")
        if name in {"audit", "review", "build", "ai", "promote", "stage-catalog"}:
            p.add_argument("path")
        if name in {"promote", "stage-catalog"}:
            p.add_argument("--destination", required=True)
        if name in {"build", "publish-bundle", "fetch"}:
            p.add_argument("--output", required=True)
        if name == "audit":
            p.add_argument("--against", action="append", default=[])
            p.add_argument("--report")
        if name == "review":
            p.add_argument("--reviewer", required=True)
            p.add_argument("--verification-report", help="Human-attested CI Docker audit JSON; release builds rerun all checks")
            p.add_argument("--ack-copyright", action="store_true")
            p.add_argument("--ack-content", action="store_true")
        if name == "publish-bundle":
            p.add_argument("--source", required=True)
            p.add_argument("--repository", required=True)
            p.add_argument("--tag", required=True)
        if name == "migrate":
            p.add_argument("--source", default="content")
            p.add_argument("--destination", required=True)
            p.add_argument("--id", default="foundation.core")
        if name == "install":
            p.add_argument("archive")
            p.add_argument("--sha256", required=True)
        if name in {"rollback", "unpin", "trust"}:
            p.add_argument("id")
        if name == "rollback":
            p.add_argument("version")
        if name == "trust":
            p.add_argument("--sha256", required=True)
            p.add_argument("--trust-code", action="store_true")
        if name in {"updates", "sync"}:
            p.add_argument("--catalog", required=True)
            p.add_argument("--offline", action="store_true")
        if name == "sync":
            p.add_argument("--id")
        if name == "fetch":
            p.add_argument("--profiles", default="knowledge/sources.json")
            p.add_argument("--source", required=True)
            p.add_argument("--ref")
        if name == "import":
            p.add_argument("--source", required=True)
            p.add_argument("--recipe", required=True)
            p.add_argument("--destination", required=True)
        if name == "generate":
            p.add_argument("--template", required=True)
            p.add_argument("--destination", required=True)
            p.add_argument("--count", type=int, default=10)
            p.add_argument("--seed", type=int, default=0)
        if name == "ai":
            p.add_argument("--question", required=True)
            p.add_argument("--model", required=True)
            p.add_argument("--count", type=int, default=3)
            p.add_argument("--endpoint", default="http://127.0.0.1:11434")
