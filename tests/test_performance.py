"""Single-pass validation regression tests; only temporary fixture packs are edited."""
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_knowledge import make_pack
from trainerlib.common import PackError, atomic_json, digest, inside
from trainerlib.format import fingerprint, load_pack, load_pack_snapshot, payload_files
from trainerlib.runtime import configured_lessons


class SinglePassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trainer-performance-")
        self.root = Path(self.temp.name)
        self.pack = make_pack(self.root / "source")

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_and_approved_load_scan_once_and_keep_fingerprint(self):
        sha = fingerprint(self.pack)
        atomic_json(self.pack / "review.json", {
            "approved": True, "reviewer": "fixture", "contentSha256": sha,
            "copyrightChecked": True, "contentChecked": True,
        })
        with patch("trainerlib.format.payload_files", wraps=payload_files) as scan:
            manifest, lessons, actual_sha = load_pack_snapshot(self.pack, approved=True)
        self.assertEqual(scan.call_count, 1)
        self.assertEqual(actual_sha, sha)
        self.assertEqual(len(lessons), 1)
        self.assertEqual(manifest["id"], "fixture.pack")

    def test_discovery_does_not_scan_again_for_fingerprint(self):
        atomic_json(self.root / "trainer-packs.json", {"sources": ["source"], "legacyContent": False})
        with patch.dict(os.environ, {"TRAINER_PACK_HOME": str(self.root / "empty-store")}):
            with patch("trainerlib.format.payload_files", wraps=payload_files) as scan:
                legacy, lessons = configured_lessons(self.root)
        self.assertFalse(legacy)
        self.assertEqual(len(lessons), 1)
        self.assertEqual(scan.call_count, 1)

    def test_same_size_same_mtime_tampering_is_not_cached(self):
        file = self.pack / "licenses/MIT.txt"
        manifest, _, sha = load_pack_snapshot(self.pack)
        manifest["files"] = payload_files(self.pack)
        atomic_json(self.pack / "pack.json", manifest)
        atomic_json(self.pack / "review.json", {"approved": True, "reviewer": "fixture",
            "contentSha256": sha, "copyrightChecked": True, "contentChecked": True})
        load_pack(self.pack, integrity=True, approved=True)
        previous = file.stat()
        data = file.read_bytes()
        file.write_bytes(data.replace(b"MIT", b"BAD", 1))
        os.utime(file, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        with self.assertRaisesRegex(PackError, "hash mismatch"):
            load_pack(self.pack, integrity=True, approved=True)
        with self.assertRaisesRegex(PackError, "stale review"):
            load_pack(self.pack, approved=True)

    def test_payload_matches_original_safe_walk(self):
        (self.pack / "nested").mkdir()
        (self.pack / "nested/a.c").write_text("int x;", encoding="utf-8")
        expected = {}
        for file in sorted(self.pack.rglob("*")):
            relative = file.relative_to(self.pack).as_posix()
            inside(self.pack, relative)
            if file.is_file() and relative not in {"pack.json", "review.json", "audit.json"}:
                expected[relative] = digest(file.read_bytes())
        self.assertEqual(payload_files(self.pack), expected)

    def test_limits_and_unsupported_files_still_rejected(self):
        with patch("trainerlib.format.MAX_EXPANDED", 1):
            with self.assertRaises(PackError):
                payload_files(self.pack)
        with patch("trainerlib.format.MAX_FILES", 1):
            with self.assertRaises(PackError):
                payload_files(self.pack)
        (self.pack / "run.exe").write_bytes(b"not executable")
        with self.assertRaisesRegex(PackError, "Unsupported payload"):
            payload_files(self.pack)

    def test_reparse_directory_is_rejected_before_descent(self):
        entry = SimpleNamespace(name="junction", path=str(self.pack / "junction"),
            stat=lambda **_: SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400))
        with patch("trainerlib.format.os.scandir") as scan:
            scan.return_value.__enter__.return_value = [entry]
            with self.assertRaisesRegex(PackError, "Links are not permitted"):
                payload_files(self.pack)
            self.assertEqual(scan.call_count, 1)

    def test_broken_symlink_is_rejected(self):
        link = self.pack / "link.txt"
        try:
            link.symlink_to(self.root / "missing")
        except OSError:
            self.skipTest("Host does not permit creating symlinks")
        with self.assertRaises(PackError):
            payload_files(self.pack)
        with self.assertRaises(PackError):
            inside(self.pack, "link.txt")

    @unittest.skipUnless(os.name == "nt", "Windows extended-length paths")
    def test_extended_path_spelling_does_not_false_positive_or_allow_escape(self):
        actual_resolve = Path.resolve
        file = self.pack / "new.txt"
        def extended(path, *args, **kwargs):
            resolved = actual_resolve(path, *args, **kwargs)
            return Path("\\\\?\\" + str(resolved)) if path == file else resolved
        with patch.object(Path, "resolve", extended):
            self.assertEqual(inside(self.pack, "new.txt"), file)
        outside = self.root / "outside.txt"
        def escape(path, *args, **kwargs):
            return Path("\\\\?\\" + str(outside)) if path == file else actual_resolve(path, *args, **kwargs)
        with patch.object(Path, "resolve", escape):
            with self.assertRaisesRegex(PackError, "escapes root"):
                inside(self.pack, "new.txt")
