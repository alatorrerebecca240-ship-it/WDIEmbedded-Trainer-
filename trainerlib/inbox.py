"""Persistent, per-question authoring inbox. Acquisition is strictly data-only."""
import contextlib
import difflib
import json
import os
import re
import shutil
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from .audit import approve, audit, copyright_errors
from .common import HASH, PackError, atomic_json, canonical, digest, inside, read_json
from .exercism import import_batch, read_index, scan, SLUG, SHA
from .format import fingerprint, load_pack

REQUEST = re.compile(r"[a-f0-9]{32}\Z")
PIPELINE_VERSION = 1
ROOT_README = b"# Review inbox\n\nPublication requires matching Docker evidence and an explicit human review.json record.\n"


def key_for(q):
    lang = q.get("language")
    prefix = f"oss.exercism.{lang}."
    slug = q.get("id", "")[len(prefix):]
    if (lang not in {"c", "cpp"} or not q.get("id", "").startswith(prefix) or not SLUG.fullmatch(slug)
            or q.get("origin", {}).get("repository") != f"https://github.com/exercism/{lang}"):
        raise PackError("Only identified official Exercism questions enter this inbox")
    return f"{lang}/{slug}"


def normalized_pack(source, target, question_id, validated_question=None):
    """Same bytes from an existing multi-question draft or a fresh upstream import."""
    source, target = Path(source), Path(target)
    # Legacy batches are validated once by acquire(), not rehashed for each question.
    questions = [validated_question] if validated_question is not None else load_pack(source)[1]
    found = [q for q in questions if q["id"] == question_id]
    if len(found) != 1 or target.exists():
        raise PackError("Missing question or destination already exists")
    q = {k: v for k, v in found[0].items() if not k.startswith("_")}
    key = key_for(q)
    pack_id = "review.exercism." + key.replace("/", ".")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="inbox-normalize-", dir=target.parent) as name:
        stage = Path(name) / "pack"
        stage.mkdir()
        asset = inside(source, q["assetRoot"])
        shutil.copytree(asset, inside(stage, q["assetRoot"]), symlinks=True)
        for origin in [q["origin"], *q["origin"].get("dependencies", [])]:
            names = [*origin.get("licenseFiles", []), *origin.get("noticeFiles", []),
                     *(v["retainedPath"] for v in origin.get("sourceFiles", []))]
            for relative in names:
                dest = inside(stage, relative)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(inside(source, relative), dest)
        atomic_json(stage / "pack.json", {"formatVersion": 1, "id": pack_id, "version": "1.0.0",
            "title": q["title"], "minEngineVersion": "0.9.0",
            "license": "mixed" if q["origin"].get("dependencies") else q["origin"]["license"]})
        atomic_json(stage / "questions.json", {"formatVersion": 1, "questions": [q]})
        (stage / "README.md").write_bytes(ROOT_README)
        load_pack(stage)
        os.replace(stage, target)
    return fingerprint(target)


def static_errors(pack):
    report = audit(pack, runner="none")
    # Only the explicit no-execution gate is expected; never mask other failures.
    expected = ": Reference execution requires --runner docker or explicitly trusted --runner native"
    return [e for e in report["errors"] if not e.endswith(expected)], report["warnings"]


class Inbox:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.state = inside(self.root, ".trainer/authoring")
        self.file = self.state / "inbox.json"

    def read(self):
        data = read_json(self.file) if self.file.exists() else {"formatVersion": 1, "items": {}}
        if data.get("formatVersion") != 1 or not isinstance(data.get("items"), dict):
            raise PackError("Invalid inbox state; original drafts are retained")
        return data

    @contextlib.contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True)
        lock = inside(self.root, ".trainer/authoring/inbox.lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise PackError("Another inbox operation is active; after a crash inspect inbox.lock before removing it") from exc
        try:
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            yield
        finally:
            lock.unlink(missing_ok=True)

    def pack(self, entry):
        path = entry.get("pack", "")
        if not path.startswith("knowledge/drafts/inbox/") or path.count("/") != 3:
            raise PackError("Invalid inbox package path")
        return inside(self.root, path)

    def listing(self):
        items = []
        for entry in self.read()["items"].values():
            current = dict(entry)
            if entry.get("pack"):
                try:
                    sha = fingerprint(self.pack(entry))
                    if sha != entry["contentSha256"]:
                        current.update(status="changed", errors=["本地内容已修改，旧验证和审核已失效。提交修改后的草稿后才能重新云端验证。"])
                except (PackError, OSError) as exc:
                    current.update(status="changed", errors=[str(exc)])
            items.append(current)
        return {"items": items, "counts": dict(Counter(v["status"] for v in items)), "total": len(items)}

    def details(self, question_id):
        entry = self.read()["items"].get(question_id)
        if not entry or not entry.get("pack"):
            raise PackError("该题尚未成功导入，请查看错误并重试获取。")
        root = self.pack(entry)
        _, questions = load_pack(root)
        q = questions[0]
        files = [{"label": "来源与题目格式：questions.json", "path": str(root / "questions.json")}]
        asset = inside(root, q["assetRoot"])
        files.insert(0, {"label": "题目说明", "path": str(inside(asset, q["statement"]))})
        for role in ("starter", "reference", "tests"):
            for file in sorted((asset / role).rglob("*")):
                if file.is_file():
                    checked = inside(root, file.relative_to(root).as_posix())
                    files.append({"label": f"{role}: {file.relative_to(asset / role).as_posix()}", "path": str(checked)})
        for file in sorted((root / "licenses").glob("*")):
            if file.is_file():
                files.append({"label": "许可：" + file.name, "path": str(inside(root, file.relative_to(root).as_posix()))})
        if entry.get("evidence"):
            files.append({"label": "Docker 验证报告", "path": str(inside(self.root, entry["evidence"]))})
        return {"entry": entry, "files": files}

    def acquire(self, project_license, offline=False, limit=20, existing_questions=()):
        if type(limit) is not int or not 1 <= limit <= 50:
            raise PackError("Acquisition limit must be 1..50")
        with self.lock():
            data = self.read()
            summary = {"added": 0, "adopted": 0, "failed": 0, "skipped": 0, "warnings": []}
            existing, families, texts = set(data["items"]), set(), []
            for item in data["items"].values():
                families.add(item["key"].split("/")[1])
                if item.get("summary"):
                    texts.append(item["summary"].casefold().strip())
            for q in existing_questions:
                existing.add(q["id"])
                texts.append(q["summary"].casefold().strip())
                try:
                    families.add(key_for(q).split("/")[1])
                except PackError:
                    pass
            # Existing publication sources are never modified or re-imported.
            for collection in ("knowledge/packs", "knowledge/approved"):
                for manifest in (self.root / collection).glob("*/pack.json"):
                    _, questions = load_pack(inside(self.root, manifest.parent.relative_to(self.root).as_posix()))
                    for q in questions:
                        existing.add(q["id"])
                        texts.append(q["summary"].casefold().strip())
                        try:
                            families.add(key_for(q).split("/")[1])
                        except PackError:
                            pass
            # Adopt legacy Exercism drafts, keeping originals byte-for-byte intact.
            for manifest in sorted((self.root / "knowledge/drafts").glob("*/pack.json")):
                try:
                    source = inside(self.root, manifest.parent.relative_to(self.root).as_posix())
                    _, questions = load_pack(source)
                    for q in questions:
                        try:
                            key = key_for(q)
                        except PackError:
                            continue
                        if q["id"] in existing:
                            continue
                        self._add(data, source, q, key)
                        existing.add(q["id"])
                        families.add(key.split("/")[1])
                        texts.append(q["summary"].casefold().strip())
                        summary["adopted"] += 1
                        atomic_json(self.file, data)
                except (PackError, OSError, ValueError) as exc:
                    summary["warnings"].append(f"保留未适配旧草稿 {manifest.parent.name}: {exc}")
            index_path = inside(self.root, ".imports/exercism-index.json")
            cache = inside(self.root, ".imports/exercism-cache")
            try:
                scan(index_path, cache, offline=offline)
            except (PackError, OSError, ValueError) as exc:
                summary["warnings"].append(f"扫描不可用，继续使用完整旧目录：{exc}")
                if not index_path.exists():
                    atomic_json(self.file, data)
                    return {**summary, **self.listing()}
            index = read_index(index_path)
            candidates = sorted(index["candidates"], key=lambda q: (q["difficulty"] != "beginner", not q["recommended"], q["key"]))
            attempted = 0
            for candidate in candidates:
                lang, slug = candidate["language"], candidate["slug"]
                qid = f"oss.exercism.{lang}.{slug}"
                if qid in existing or slug in families or not candidate["supported"] or candidate["difficulty"] == "advanced":
                    summary["skipped"] += 1
                    continue
                if attempted >= limit:
                    break
                attempted += 1
                try:
                    with tempfile.TemporaryDirectory(prefix="inbox-acquire-", dir=self.state) as name:
                        source = Path(name) / "source"
                        import_batch(index_path, source, cache, keys=[candidate["key"]], project_license=project_license)
                        q = load_pack(source)[1][0]
                        text = q["summary"].casefold().strip()
                        if any(difflib.SequenceMatcher(None, text, previous, autojunk=False).ratio() >= .93 for previous in texts):
                            summary["skipped"] += 1
                            continue
                        self._add(data, source, q, candidate["key"])
                        texts.append(text)
                        families.add(slug)
                        existing.add(qid)
                        summary["added"] += 1
                except (PackError, OSError, ValueError, KeyError, TypeError) as exc:
                    data["items"][qid] = {"id": qid, "key": candidate["key"], "title": candidate["title"],
                        "status": "import-failed", "errors": [str(exc)], "pack": None}
                    summary["failed"] += 1
                atomic_json(self.file, data)
            atomic_json(self.file, data)
            return {**summary, **self.listing()}

    def _add(self, data, source, q, key):
        relative = "knowledge/drafts/inbox/review.exercism." + key.replace("/", ".")
        target = inside(self.root, relative)
        # Recovery after a crash between writing a complete pack and saving the queue.
        if target.exists():
            _, actual = load_pack(target)
            if len(actual) != 1 or actual[0]["id"] != q["id"]:
                raise PackError("Existing inbox folder belongs to another question")
            q = actual[0]
            sha = fingerprint(target)
        else:
            sha = normalized_pack(source, target, q["id"], validated_question=q)
        errors, warnings = static_errors(target)
        data["items"][q["id"]] = {"id": q["id"], "key": key, "title": q["title"], "summary": q["summary"],
            "pack": relative, "contentSha256": sha, "commit": q["origin"]["commit"],
            "status": "static-failed" if errors else "pending", "errors": errors, "warnings": warnings}

    def prepare(self, request_id, ids=()):
        if not REQUEST.fullmatch(request_id):
            raise PackError("Invalid cloud request ID")
        with self.lock():
            data = self.read()
            entries = []
            selected = set(ids)
            current = {v["id"]: v for v in self.listing()["items"]}
            for qid, entry in data["items"].items():
                if selected and qid not in selected:
                    continue
                if current[qid]["status"] not in {"pending", "validation-failed", "changed"}:
                    continue
                errors, _ = static_errors(self.pack(entry))
                if errors:
                    entry.update(status="static-failed", errors=errors)
                    continue
                if current[qid]["status"] == "changed":
                    entry.update(contentSha256=fingerprint(self.pack(entry)), mode="repository")
                planned = {"id": qid, "key": entry["key"], "commit": entry["commit"], "contentSha256": entry["contentSha256"]}
                if entry.get("mode") == "repository":
                    planned.update(mode="repository", path=entry["pack"])
                entries.append(planned)
                if len(entries) == 50:
                    break
            plan = {"pipelineVersion": PIPELINE_VERSION, "requestId": request_id, "entries": entries}
            if entries:
                plan_path = self.state / "requests" / (request_id + ".json")
                if plan_path.exists():
                    raise PackError("Request ID already exists")
                atomic_json(plan_path, plan)
                for entry in entries:
                    data["items"][entry["id"]].update(status="checking", requestId=request_id, errors=[])
            atomic_json(self.file, data)
            return plan

    def fail_request(self, request_id, reason):
        if not REQUEST.fullmatch(request_id):
            raise PackError("Invalid request ID")
        with self.lock():
            data = self.read()
            for entry in data["items"].values():
                if entry.get("requestId") == request_id and entry["status"] == "checking":
                    entry.update(status="validation-failed", errors=[str(reason)[:2000]])
            atomic_json(self.file, data)
        return self.listing()

    def results(self, request_id, archive, expected_sha):
        if not REQUEST.fullmatch(request_id) or not HASH.fullmatch(expected_sha):
            raise PackError("Invalid result identity/checksum")
        if Path(archive).stat().st_size > 8 * 1024 * 1024:
            raise PackError("CI artifact exceeds size limit")
        raw = Path(archive).read_bytes()
        if len(raw) > 8 * 1024 * 1024 or digest(raw) != expected_sha:
            raise PackError("CI artifact checksum/size mismatch")
        # Read one exact bounded JSON member; never extract arbitrary artifact files.
        try:
            with zipfile.ZipFile(archive) as package:
                infos = package.infolist()
                if len(infos) != 1 or infos[0].filename != "inbox-results.json" or infos[0].file_size > 4 * 1024 * 1024:
                    raise PackError("Unexpected CI artifact contents")
                report = json.loads(package.read(infos[0]).decode("utf-8"))
        except (zipfile.BadZipFile, UnicodeError, ValueError) as exc:
            raise PackError("Invalid CI artifact") from exc
        plan = read_json(self.state / "requests" / (request_id + ".json"))
        validate_plan(plan)
        if (not isinstance(report, dict) or report.get("pipelineVersion") != PIPELINE_VERSION or report.get("requestId") != request_id
                or report.get("planSha256") != digest(canonical(plan)) or not isinstance(report.get("results"), list)):
            raise PackError("CI result is not bound to this request")
        received = report["results"]
        if (len(received) != len(plan["entries"]) or any(not isinstance(v, dict) for v in received)
                or {v.get("id") for v in received} != {v["id"] for v in plan["entries"]}):
            raise PackError("CI result has missing/duplicate/unexpected questions")
        with self.lock():
            data = self.read()
            for result in received:
                entry = data["items"].get(result["id"])
                if not entry or entry.get("requestId") != request_id or entry["status"] != "checking":
                    continue  # stale result or deliberately deferred by the reviewer
                execution = result.get("audit")
                if fingerprint(self.pack(entry)) != entry["contentSha256"]:
                    entry.update(status="changed", errors=["本地题目已修改，拒绝旧云端报告。"])
                    continue
                valid = (isinstance(execution, dict) and execution.get("formatVersion") == 1
                         and execution.get("errors") == [] and execution.get("referenceVerified") == [entry["id"]])
                check = audit(self.pack(entry), execution_report=execution) if valid else None
                if not check or not check["passed"]:
                    errors = result.get("errors") or (execution.get("errors") if isinstance(execution, dict) else None) or (check or {}).get("errors") or ["缺少有效 Docker 证据"]
                    errors = [str(v)[:4000] for v in (errors if isinstance(errors, list) else [errors])[:10]]
                    entry.update(status="validation-failed", errors=errors)
                    continue
                evidence = f".trainer/authoring/evidence/{request_id}/{entry['id']}.json"
                atomic_json(inside(self.root, evidence), execution)
                notices = execution.get("warnings", [])
                notices = [v[:2000] for v in notices[:10] if isinstance(v, str)] if isinstance(notices, list) else []
                entry.update(status="ready", errors=[], warnings=notices, evidence=evidence, artifactSha256=expected_sha)
            atomic_json(self.file, data)
        return self.listing()

    def decide(self, ids, decision, reviewer="", ack_content=False, ack_copyright=False):
        if decision not in {"approve", "defer", "resume"} or not ids or len(set(ids)) != len(ids):
            raise PackError("Invalid review selection")
        if decision == "approve" and not (reviewer.strip() and ack_content and ack_copyright):
            raise PackError("Explicit human content/copyright acknowledgement and reviewer required")
        with self.lock():
            data = self.read()
            completed, failed = [], []
            for qid in ids:
                try:
                    entry = data["items"][qid]
                    if decision == "defer":
                        if entry["status"] == "approved":
                            raise PackError("已审核题目不能通过暂缓菜单撤销已准备的发布快照。")
                        entry.update(status="deferred")
                    elif decision == "resume":
                        if entry["status"] == "import-failed" or (entry["status"] == "deferred" and not entry.get("pack")):
                            del data["items"][qid]  # permit acquisition retry; original files are untouched
                        elif entry["status"] != "approved":
                            entry.update(status="pending", errors=[])
                    else:
                        if entry["status"] != "ready" or fingerprint(self.pack(entry)) != entry["contentSha256"]:
                            raise PackError("Question is not ready or changed since validation")
                        evidence = read_json(inside(self.root, entry["evidence"]))
                        approve(self.pack(entry), reviewer, execution_report=evidence)
                        entry.update(status="approved", reviewer=reviewer)
                    completed.append(qid)
                except (PackError, OSError, KeyError, ValueError) as exc:
                    failed.append({"id": qid, "error": str(exc)})
                atomic_json(self.file, data)
            return {"completed": completed, "failed": failed, "publication": "not-run"}

    def stage_approved(self):
        """Explicit user action; copies approved snapshots, never pushes/tags/releases."""
        with self.lock():
            data = self.read()
            staged, failed = [], []
            for entry in data["items"].values():
                if entry["status"] != "approved":
                    continue
                try:
                    source = self.pack(entry)
                    manifest, _ = load_pack(source, approved=True)
                    if fingerprint(source) != entry["contentSha256"]:
                        raise PackError("Approved content changed")
                    target = inside(self.root, "knowledge/approved/" + manifest["id"])
                    if target.exists():
                        load_pack(target, approved=True)
                        if fingerprint(target) != entry["contentSha256"]:
                            raise PackError("Never overwrite an existing publication snapshot")
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with tempfile.TemporaryDirectory(prefix="inbox-stage-", dir=target.parent) as name:
                            temp = Path(name) / "pack"
                            shutil.copytree(source, temp)
                            load_pack(temp, approved=True)
                            os.replace(temp, target)
                    staged.append(entry["id"])
                except (PackError, OSError) as exc:
                    failed.append({"id": entry["id"], "error": str(exc)})
            return {"staged": staged, "failed": failed, "publication": "not-run"}


def validate_plan(plan):
    if (not isinstance(plan, dict) or plan.get("pipelineVersion") != PIPELINE_VERSION
            or not isinstance(plan.get("requestId"), str) or not REQUEST.fullmatch(plan["requestId"])
            or not isinstance(plan.get("entries"), list) or not 1 <= len(plan["entries"]) <= 50):
        raise PackError("Invalid cloud acquisition plan")
    keys = set()
    for item in plan["entries"]:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            raise PackError("Invalid cloud question")
        parts = item["key"].split("/")
        if (len(parts) != 2 or parts[0] not in {"c", "cpp"} or not SLUG.fullmatch(parts[1])
                or item.get("id") != f"oss.exercism.{parts[0]}.{parts[1]}" or item["key"] in keys
                or not isinstance(item.get("commit"), str) or not SHA.fullmatch(item["commit"])
                or not isinstance(item.get("contentSha256"), str) or not HASH.fullmatch(item["contentSha256"])):
            raise PackError("Invalid or duplicate pinned question")
        keys.add(item["key"])
        if item.get("mode", "upstream") not in {"upstream", "repository"}:
            raise PackError("Unsupported reconstruction mode")
        if item.get("mode") == "repository" and item.get("path") != "knowledge/drafts/inbox/review.exercism." + item["key"].replace("/", "."):
            raise PackError("Repository verification is restricted to the exact inbox draft path")
    return plan
