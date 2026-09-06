"""Immutable versions + one atomically replaced activation index. Install never runs code."""

import contextlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import time
import urllib.parse
import zipfile
from pathlib import Path

from .common import HASH, ID, MAX_ARCHIVE, MAX_EXPANDED, MAX_FILES, PackError, atomic_json, digest, download, https_url, inside, read_json, safe_path, version
from .format import load_pack


GITHUB_HOSTS = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


class PackStore:
    def __init__(self, root):
        self.root = Path(root)
        self.index_file = self.root / "installed.json"
        self.reserved_questions = {}

    def index(self):
        return read_json(self.index_file) if self.index_file.exists() else {"formatVersion": 1, "active": {}, "versions": {}, "pinned": {}, "trusted": {}}

    @contextlib.contextmanager
    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / "install.lock"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise PackError("Another installation is active. If it crashed, inspect install.lock before removing it.") from exc
        try:
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            yield
        finally:
            path.unlink(missing_ok=True)

    def location(self, pack_id, release):
        version(release)
        return inside(self.root, f"versions/{pack_id}/{release}")

    def install(self, archive, expected_sha, source="offline", expected=None):
        archive = Path(archive)
        if not HASH.fullmatch(expected_sha or ""):
            raise PackError("An independently obtained SHA-256 is required, including offline imports")
        if archive.stat().st_size > MAX_ARCHIVE:
            raise PackError("Archive too large")
        data = archive.read_bytes()
        if digest(data) != expected_sha:
            raise PackError("Archive SHA-256 mismatch; previous version remains active")
        with self.lock(), tempfile.TemporaryDirectory(prefix="staging-", dir=self.root) as temp:
            stage = Path(temp)
            self.extract(data, stage)
            manifest, lessons = load_pack(stage, integrity=True, approved=True)
            if expected and (manifest["id"] != expected["id"] or manifest["version"] != expected["version"]):
                raise PackError("Archive identity differs from catalog")
            pack_id, release = manifest["id"], manifest["version"]
            if any(q["id"] in self.reserved_questions and self.reserved_questions[q["id"]] != pack_id for q in lessons):
                raise PackError("Question IDs conflict with the configured local source library")
            index = self.index()
            previous = index["versions"].get(pack_id, {}).get(release)
            if previous and previous["sha256"] != expected_sha:
                raise PackError("An immutable version cannot be republished with different bytes")
            active = index["active"].get(pack_id)
            if active and version(release) < version(active):
                raise PackError("Install refuses downgrades; use explicit rollback")
            new_ids = {q["id"] for q in lessons}
            for other_id, other_version in index["active"].items():
                if other_id != pack_id:
                    _, others = load_pack(self.location(other_id, other_version), integrity=True, approved=True)
                    if new_ids & {q["id"] for q in others}:
                        raise PackError("Question IDs conflict with another active package")
            destination = self.location(pack_id, release)
            if destination.exists():
                # Crash recovery never treats an arbitrary pre-existing directory as the release.
                existing, _ = load_pack(destination, integrity=True, approved=True)
                if existing != manifest or read_json(destination / "review.json") != read_json(stage / "review.json"):
                    raise PackError("Existing version directory differs from verified archive")
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage, destination)
                # TemporaryDirectory cleanup sees a recreated empty stage, never the installed version.
                stage.mkdir()
            cache = self.root / "cache"
            cache.mkdir(exist_ok=True)
            cached = cache / f"{expected_sha}.zip"
            if not cached.exists() or digest(cached.read_bytes()) != expected_sha:
                with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
                    stream.write(data)
                    name = stream.name
                os.replace(name, cached)
            index["versions"].setdefault(pack_id, {})[release] = {"sha256": expected_sha, "source": source, "installedAt": int(time.time())}
            index["active"][pack_id] = release
            index["pinned"].setdefault(pack_id, False)
            atomic_json(self.index_file, index)
            return {"id": pack_id, "version": release, "sha256": expected_sha, "questions": len(lessons)}

    @staticmethod
    def extract(data, destination):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_FILES + 3:
                    raise PackError("Too many ZIP entries")
                total, names = 0, set()
                for entry in entries:
                    safe_path(entry.orig_filename)
                    name = safe_path(entry.filename)
                    folded = name.casefold()
                    if folded in names:
                        raise PackError("Duplicate/case-colliding ZIP entry")
                    names.add(folded)
                    mode = entry.external_attr >> 16
                    if entry.is_dir() or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)) or entry.flag_bits & 1:
                        raise PackError("Only regular, unencrypted files are allowed")
                    total += entry.file_size
                    if total > MAX_EXPANDED or entry.file_size > MAX_ARCHIVE or (entry.file_size > 1024 * 1024 and entry.file_size > max(1, entry.compress_size) * 200):
                        raise PackError("ZIP expansion limit exceeded")
                    target = inside(destination, name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as src, target.open("xb") as dst:
                        size = 0
                        while True:
                            block = src.read(65536)
                            if not block:
                                break
                            size += len(block)
                            if size > entry.file_size or size > MAX_ARCHIVE:
                                raise PackError("ZIP size mismatch")
                            dst.write(block)
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            if isinstance(exc, PackError):
                raise
            raise PackError(f"Invalid archive: {exc}") from exc

    def rollback(self, pack_id, release):
        with self.lock():
            index = self.index()
            if release not in index["versions"].get(pack_id, {}):
                raise PackError("Rollback target is not a cached installed version")
            _, questions = load_pack(self.location(pack_id, release), integrity=True, approved=True)
            target_ids = {q["id"] for q in questions}
            if any(qid in self.reserved_questions and self.reserved_questions[qid] != pack_id for qid in target_ids):
                raise PackError("Rollback would conflict with configured source questions")
            for other_id, other_version in index["active"].items():
                if other_id != pack_id:
                    _, others = load_pack(self.location(other_id, other_version), integrity=True, approved=True)
                    if target_ids.intersection(q["id"] for q in others):
                        raise PackError("Rollback would conflict with another active package")
            index["active"][pack_id] = release
            # Prevent the next background poll from undoing a deliberate rollback.
            index["pinned"][pack_id] = True
            atomic_json(self.index_file, index)

    def unpin(self, pack_id):
        with self.lock():
            index = self.index()
            if pack_id not in index["active"]:
                raise PackError("Package is not installed")
            index["pinned"][pack_id] = False
            atomic_json(self.index_file, index)

    def trust(self, pack_id, sha256):
        with self.lock():
            index = self.index()
            release = index["active"].get(pack_id)
            entry = index["versions"].get(pack_id, {}).get(release, {})
            if entry.get("sha256") != sha256:
                raise PackError("Trust must match the current installed archive hash")
            trusted = index["trusted"].setdefault(pack_id, [])
            if sha256 not in trusted:
                trusted.append(sha256)
            atomic_json(self.index_file, index)

    def lessons(self):
        index = self.index()
        result = {}
        for pack_id, release in index["active"].items():
            manifest, lessons = load_pack(self.location(pack_id, release), integrity=True, approved=True)
            sha = index["versions"][pack_id][release]["sha256"]
            result[pack_id] = [{**q, "_packId": pack_id, "_packVersion": release, "_packSha256": sha, "_needsTrust": sha not in index.get("trusted", {}).get(pack_id, [])} for q in lessons]
        return result

    def catalog(self, url, offline=False):
        p = urllib.parse.urlsplit(https_url(url))
        # v1 deliberately supports GitHub Pages only; no intranet/localhost fetches.
        if not p.hostname.endswith(".github.io"):
            raise PackError("Catalog must be hosted on a configured GitHub Pages HTTPS origin")
        key = digest(url.encode())
        cache = self.root / "catalogs" / f"{key}.json"
        stale = offline
        if not offline:
            try:
                data = json.loads(download(url, 2 * 1024 * 1024, {p.hostname}))
                self.validate_catalog(data)
                atomic_json(cache, data)
            except (PackError, ValueError):
                if not cache.exists():
                    raise
                stale = True
        if stale:
            data = read_json(cache)
            self.validate_catalog(data)
        return data, stale

    @staticmethod
    def validate_catalog(data):
        if not isinstance(data, dict) or data.get("formatVersion") != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", data.get("repository", "")):
            raise PackError("Invalid catalog/repository")
        packs = data.get("packages")
        if not isinstance(packs, list) or len(packs) > 1000:
            raise PackError("Invalid catalog packages")
        seen = set()
        for item in packs:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not ID.fullmatch(item["id"]) or item["id"] in seen:
                raise PackError("Invalid/duplicate catalog package")
            safe_path(item["id"])
            seen.add(item["id"])
            version(item.get("version"))
            if not HASH.fullmatch(item.get("sha256", "")) or type(item.get("size")) is not int or not 0 < item["size"] <= MAX_ARCHIVE:
                raise PackError("Invalid catalog hash/size")
            https_url(item.get("url", ""), {"github.com"})
            prefix = f"https://github.com/{data['repository']}/releases/download/"
            if not item["url"].startswith(prefix):
                raise PackError("Release URL must belong to the declared repository")

    def updates(self, url, offline=False):
        catalog, stale = self.catalog(url, offline)
        index = self.index()
        rows = []
        for item in catalog["packages"]:
            active = index["active"].get(item["id"])
            known = index["versions"].get(item["id"], {}).get(item["version"])
            if known and known["sha256"] != item["sha256"]:
                raise PackError("Catalog attempted to replace an immutable version")
            current = index["versions"].get(item["id"], {}).get(active, {})
            if current and current.get("source") != url:
                # Never let one subscription take over another publisher's package ID.
                # A byte-identical offline copy can be explicitly reinstalled from
                # a trusted catalog to subscribe; background sync sees no update.
                if not (current.get("source") == "offline" and active == item["version"] and current["sha256"] == item["sha256"]):
                    continue
            rows.append({**item, "installed": active, "pinned": index["pinned"].get(item["id"], False), "updateAvailable": bool(active and version(item["version"]) > version(active))})
        return {"packages": rows, "offline": stale}

    def fetch_install(self, url, item):
        cache = self.root / "cache" / f"{item['sha256']}.zip"
        if cache.exists() and cache.stat().st_size != item["size"]:
            raise PackError("Cached release size differs from catalog")
        if not cache.exists() or digest(cache.read_bytes()) != item["sha256"]:
            data = download(item["url"], min(MAX_ARCHIVE, item["size"]), GITHUB_HOSTS)
            if len(data) != item["size"] or digest(data) != item["sha256"]:
                raise PackError("Release size/hash mismatch")
            cache.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False) as stream:
                stream.write(data)
                name = stream.name
            os.replace(name, cache)
        return self.install(cache, item["sha256"], source=url, expected=item)
