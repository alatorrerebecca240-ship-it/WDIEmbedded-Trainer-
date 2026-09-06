"""Data-only importer tests with synthetic upstream blobs, no network/compiler."""
import copy
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from trainerlib.audit import copyright_errors, audit, run_program
from trainerlib.common import PackError, atomic_json, canonical, digest
from trainerlib.exercism import _blob, _enable_c_tests, _git_hash, import_batch, read_index, scan
from trainerlib.exercism_curriculum import PILOT
from trainerlib.format import load_pack

LICENSE = b"MIT License\nCopyright fixture authors\nPermission is hereby granted, free of charge.\n"
COMMIT = "a" * 40


class ExercismTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trainer-exercism-test-")
        self.root = Path(self.temp.name)
        self.cache = self.root / "cache"
        self.index = self.root / "index.json"
        self.license = self.root / "LICENSE"
        self.license.write_bytes(LICENSE)
        self.payload = {"LICENSE": LICENSE, "config.json": canonical({"exercises": {"practice": [
            {"slug": "leap", "name": "Leap", "difficulty": 1, "topics": ["conditionals"]},
            {"slug": "hard", "name": "Hard", "difficulty": 9}]}})}
        base = "exercises/practice/leap/"
        assets = {".meta/config.json": canonical({"files": {"solution": ["leap.c", "leap.h"],
            "example": [".meta/example.c", ".meta/example.h"], "test": ["test_leap.c"]}}),
            ".docs/instructions.md": b"Return whether a year is a leap year.",
            ".docs/introduction.md": b"Fixture historical context.",
            ".docs/instructions.append.md": b"Fixture language-specific return convention.",
            "leap.c": b"int leap(int year) { return 0; }\n", "leap.h": b"int leap(int year);\n",
            ".meta/example.c": b"int leap(int year) { return year % 4 == 0; }\n",
            ".meta/example.h": b"int leap(int year);\n",
            "test_leap.c": b"void test(void) {\r\n TEST_IGNORE(); // enable me\r\n ASSERT(1);\r\n}\r\n",
            "test-framework/unity.c": b"/* MIT License fixture, not real upstream code */\n",
            "test-framework/unity.h": b"/* fixture */\n",
            "test-framework/unity_internals.h": b"/* fixture */\n"}
        self.payload.update({base + k: v for k, v in assets.items()})
        self.network = []

    def tearDown(self):
        self.temp.cleanup()

    def download(self, url, *args):
        self.network.append(url)
        if "/git/trees/" in url:
            return canonical({"truncated": False, "tree": [
                {"path": name, "sha": _git_hash(data), "size": len(data), "mode": "100644", "type": "blob"}
                for name, data in self.payload.items()]})
        prefix = f"https://raw.githubusercontent.com/exercism/c/{COMMIT}/"
        self.assertTrue(url.startswith(prefix), url)
        return self.payload[url[len(prefix):]]

    def scanned(self):
        with patch("trainerlib.exercism.download", side_effect=self.download):
            return scan(self.index, self.cache, language="c", refs={"c": COMMIT})

    def imported(self, name="fixture.pack"):
        with patch("trainerlib.exercism.download", side_effect=self.download), \
                patch("subprocess.run", side_effect=AssertionError("No native execution")), \
                patch("subprocess.Popen", side_effect=AssertionError("No processes")):
            return import_batch(self.index, self.root / name, self.cache,
                recommended=True, project_license=self.license)

    def test_curated_pilot_has_32_distinct_families(self):
        self.assertEqual(len(PILOT), 32)
        self.assertEqual(len({slug for _, slug in PILOT}), 32)
        self.assertEqual(sum(lang == "c" for lang, _ in PILOT), 24)
        self.assertEqual(sum(q["difficulty"] == "beginner" for q in PILOT.values()), 25)

    def test_scan_pins_sources_filters_and_offline_never_downloads(self):
        result = self.scanned()
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["sources"]["c"]["commit"], COMMIT)
        with patch("trainerlib.exercism.download", side_effect=AssertionError("offline")):
            self.assertTrue(scan(self.index, self.cache, offline=True)["offline"])

    def test_import_preserves_originals_enables_tests_and_stays_unapproved(self):
        self.scanned()
        result = self.imported()
        root = Path(result["destination"])
        manifest, questions = load_pack(root)
        self.assertEqual(manifest["minEngineVersion"], "0.8.0")
        self.assertEqual(result["execution"], "not-run")
        self.assertFalse((root / "review.json").exists())
        self.assertEqual(copyright_errors(questions[0], root), [])
        original = root / "upstream/c/exercises/practice/leap/test_leap.c"
        self.assertEqual(original.read_bytes(), self.payload["exercises/practice/leap/test_leap.c"])
        tests = root / "lessons/oss.exercism.c.leap/tests/test_leap.c"
        self.assertNotIn("TEST_IGNORE", tests.read_text())
        self.assertIn("ASSERT(1)", tests.read_text())
        description = (root / "lessons/oss.exercism.c.leap/README.md").read_text(encoding="utf-8")
        self.assertIn("Fixture historical context.", description)
        self.assertIn("Fixture language-specific return convention.", description)
        self.assertFalse(audit(root)["passed"])
        before = (root / "questions.json").read_bytes()
        with self.assertRaises(PackError):
            self.imported()
        self.assertEqual(before, (root / "questions.json").read_bytes())

    def test_ignore_rewriter_is_conservative(self):
        text, count = _enable_c_tests("TEST_IGNORE();\n TEST_IGNORE(); // run\r\nASSERT(1);\n")
        self.assertEqual(count, 2)
        self.assertIn("ASSERT(1);", text)
        for dangerous in ["if (flag) TEST_IGNORE();", 'TEST_IGNORE_MESSAGE("why");', "TEST_IGNORE(); ASSERT(0);"]:
            with self.subTest(dangerous=dangerous), self.assertRaises(PackError):
                _enable_c_tests(dangerous)

    def test_corrupt_cache_rejected_without_refetch(self):
        self.scanned()
        source = read_index(self.index)["sources"]["c"]
        (self.cache / "c" / COMMIT / "LICENSE").write_bytes(b"tampered")
        with patch("trainerlib.exercism.download", side_effect=AssertionError("no refetch")), self.assertRaises(PackError):
            _blob(source, "LICENSE", self.cache)

    def test_index_tamper_and_rehashed_traversal_are_rejected(self):
        self.scanned()
        value = json.loads(self.index.read_text(encoding="utf-8"))
        value["candidates"][0]["title"] = "modified"
        atomic_json(self.index, value)
        with self.assertRaises(PackError):
            read_index(self.index)
        value["candidates"][0]["slug"] = "../../escape"
        value["sha256"] = digest(canonical({k: v for k, v in value.items() if k != "sha256"}))
        atomic_json(self.index, value)
        with self.assertRaises(PackError):
            read_index(self.index)

    def test_failure_is_atomic_and_preserves_previous_index(self):
        self.scanned()
        previous = self.index.read_bytes()
        with patch("trainerlib.exercism.download", return_value=canonical({"truncated": True, "tree": []})), self.assertRaises(PackError):
            scan(self.index, self.cache, language="c", refs={"c": COMMIT})
        self.assertEqual(previous, self.index.read_bytes())
        with patch("trainerlib.exercism._convert", side_effect=PackError("unsupported layout")), self.assertRaises(PackError):
            self.imported()
        self.assertFalse((self.root / "fixture.pack").exists())
        self.assertFalse(list(self.root.glob("exercism-import-*")))

    def test_batch_limit_and_ambiguous_selection_rejected(self):
        self.scanned()
        for keys, recommended in [(["c/leap"] * 2, True), ([f"c/a-{i}" for i in range(51)], False), ([], False)]:
            with self.subTest(keys=keys), self.assertRaises(PackError):
                import_batch(self.index, self.root / "fixture.pack", self.cache,
                    keys=keys, recommended=recommended, project_license=self.license)

    def test_dependency_provenance_is_independently_checked(self):
        self.scanned()
        root = Path(self.imported()["destination"])
        q = load_pack(root)[1][0]
        dependency = copy.deepcopy(q["origin"])
        q["origin"]["dependencies"] = [dependency]
        self.assertEqual(copyright_errors(q, root), [])
        dependency["sourceFiles"][0]["sha256"] = "0" * 64
        self.assertTrue(any("Dependency:" in e for e in copyright_errors(q, root)))
        dependency["dependencies"] = []
        self.assertTrue(any("flat" in e for e in copyright_errors(q, root)))

    def test_non_mit_root_is_not_scanned(self):
        self.payload["LICENSE"] = b"All rights reserved, no redistribution."
        with patch("trainerlib.exercism.download", side_effect=self.download), self.assertRaises(PackError):
            scan(self.index, self.cache, language="c", refs={"c": COMMIT})
        self.assertFalse(self.index.exists())

    def test_cpp_retains_catch_dependency_and_enables_full_suite(self):
        base = "exercises/practice/reverse-string/"
        assets = {"LICENSE": LICENSE, "config.json": canonical({"exercises": {"practice": [
            {"slug": "reverse-string", "name": "Reverse", "difficulty": 1}]}}),
            base + ".meta/config.json": canonical({"files": {"solution": ["reverse_string.cpp", "reverse_string.h"],
                "example": [".meta/example.h"], "test": ["reverse_string_test.cpp"]}}),
            base + ".docs/instructions.md": b"Reverse a string.",
            base + "reverse_string.cpp": b"// empty fixture\n", base + "reverse_string.h": b"// TODO fixture\n",
            base + ".meta/example.h": b"// inline reference fixture\n",
            base + "reverse_string_test.cpp": b"#if defined(EXERCISM_RUN_ALL_TESTS)\n// extra assertions\n#endif\n",
            base + "test/tests-main.cpp": b'#define CATCH_CONFIG_MAIN\n#include "catch.hpp"\n',
            base + "test/catch.hpp": b"// Boost Software License, Version 1.0. Fixture only.\n"}
        def fetch(url, *args):
            if "/git/trees/" in url:
                return canonical({"truncated": False, "tree": [
                    {"path": name, "sha": _git_hash(data), "size": len(data), "mode": "100644", "type": "blob"}
                    for name, data in assets.items()]})
            return assets[url.split(COMMIT + "/", 1)[1]]
        with patch("trainerlib.exercism.download", side_effect=fetch), \
                patch("subprocess.Popen", side_effect=AssertionError("must not execute")):
            scan(self.index, self.cache, language="cpp", refs={"cpp": COMMIT})
            result = import_batch(self.index, self.root / "cpp.fixture", self.cache,
                recommended=True, project_license=self.license)
        root = Path(result["destination"])
        manifest, questions = load_pack(root)
        self.assertEqual(manifest["license"], "mixed")
        self.assertEqual(copyright_errors(questions[0], root), [])
        dep = questions[0]["origin"]["dependencies"][0]
        self.assertEqual(dep["license"], "BSL-1.0")
        self.assertEqual((root / dep["sourceFiles"][0]["retainedPath"]).read_bytes(), assets[base + "test/catch.hpp"])
        lesson = root / "lessons/oss.exercism.cpp.reverse-string"
        self.assertTrue((lesson / "tests/reverse_string_test.cpp").read_text().startswith("#define EXERCISM_RUN_ALL_TESTS 1"))
        self.assertIn("CATCH_CONFIG_NO_POSIX_SIGNALS", (lesson / "tests/test/tests-main.cpp").read_text())
        self.assertEqual((lesson / "reference/reverse_string.h").read_bytes(), assets[base + ".meta/example.h"])
        with patch("trainerlib.audit.limited_run", return_value=subprocess.CompletedProcess([], 0, "", "")) as runner, \
                patch("trainerlib.audit.subprocess.run"):
            run_program(root, questions[0], runner="docker")
            args = runner.call_args.args[0]
            self.assertEqual(args[args.index("--memory") + 1], "768m")
            self.assertEqual(runner.call_args.kwargs["timeout"], 90)
            self.assertEqual(args[args.index("--network") + 1], "none")
            self.assertIn("--read-only", args)
        manifest["minEngineVersion"] = "0.6.0"
        atomic_json(root / "pack.json", manifest)
        with self.assertRaisesRegex(PackError, "Dependency provenance"):
            load_pack(root)
        (root / "licenses/BSL-1.0.txt").unlink()
        self.assertTrue(any("Dependency: Missing license" in e for e in copyright_errors(questions[0], root)))


if __name__ == "__main__":
    unittest.main()
