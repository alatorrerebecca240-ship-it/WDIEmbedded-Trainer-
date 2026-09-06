"""Shared fail-closed data, path and download primitives."""

import hashlib
import json
import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


class PackError(RuntimeError):
    pass


MAX_ARCHIVE = 32 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_FILES = 4000
ID = re.compile(r"[a-z0-9][a-z0-9.-]{0,99}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "BSL-1.0", "CC0-1.0", "CC-BY-4.0"}
PROGRAMMING = {"programming", "debugging"}
TYPES = PROGRAMMING | {"single-choice", "true-false", "fill-blank", "code-reading"}


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PackError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, ValueError) as exc:
        raise PackError(f"Cannot read JSON {path}: {exc}") from exc


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or ":" in value:
        raise PackError(f"Unsafe relative path: {value!r}")
    parts = value.split("/")
    if any(not p or p in {".", ".."} or p.endswith((".", " ")) for p in parts):
        raise PackError(f"Unsafe relative path: {value!r}")
    for part in parts:
        if re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part):
            raise PackError(f"Reserved filename: {value}")
        if any(ord(char) < 32 or char in '<>"|?*' for char in part):
            raise PackError(f"Unsafe filename: {value}")
    if PurePosixPath(value).is_absolute():
        raise PackError(f"Absolute path: {value}")
    return value


def inside(root, value):
    root = Path(root).resolve()
    path = root / safe_path(value)
    # Reject symlinks AND Windows reparse points, including directory junctions.
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink() or (candidate.exists() and getattr(candidate.lstat(), "st_file_attributes", 0) & 0x400):
            raise PackError(f"Links are not permitted: {candidate}")
    if not path.resolve().is_relative_to(root):
        raise PackError(f"Path escapes root: {value}")
    return path


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise PackError(f"Expected stable MAJOR.MINOR.PATCH version: {value!r}")
    return tuple(map(int, value.split(".")))


def https_url(value, hosts=None):
    try:
        p = urllib.parse.urlsplit(value)
        valid = p.scheme == "https" and p.hostname and not p.username and not p.password and not p.fragment and p.port in (None, 443)
    except (TypeError, ValueError) as exc:
        raise PackError("Invalid HTTPS URL") from exc
    if not valid:
        raise PackError("Only credential-free HTTPS URLs on port 443 are allowed")
    host = p.hostname.lower()
    if hosts is not None and host not in hosts:
        raise PackError(f"Untrusted download host: {host}")
    return value


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        https_url(newurl, self.hosts)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(url, limit=MAX_ARCHIVE, hosts=None):
    https_url(url, hosts)
    opener = urllib.request.build_opener(CheckedRedirect(hosts))
    request = urllib.request.Request(url, headers={"User-Agent": "Embedded-Trainer/0.6", "Accept": "application/json, application/octet-stream, */*"})
    started = time.monotonic()
    try:
        with opener.open(request, timeout=25) as response:
            https_url(response.geturl(), hosts)
            if int(response.headers.get("Content-Length", "0")) > limit:
                raise PackError("Download too large")
            chunks, size = [], 0
            while True:
                if time.monotonic() - started > 120:
                    raise PackError("Download total time limit exceeded")
                chunk = response.read(min(65536, limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > limit:
                    raise PackError("Download exceeds size limit")
            return b"".join(chunks)
    except (OSError, ValueError) as exc:
        raise PackError(f"Download failed: {exc}") from exc
