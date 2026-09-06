"""Offline package/security tests; no public service, user cache or real progress is modified."""

import copy
import argparse
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import trainer
from trainerlib.audit import approve, audit, build, run_program
from trainerlib.acquire import import_recipe
from trainerlib.common import PackError, atomic_json, digest, inside, version
from trainerlib.format import fingerprint, load_pack, payload_files
from trainerlib.generate import ai_variants, template_variants
from trainerlib.store import PackStore
from trainerlib.process import limited_run


LICENSE = """MIT License
Copyright (c) 2026 Embedded Trainer test fixture authors
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the Software), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
"""


def question(qid="fixture.basic"):
    return {"schemaVersion": 1, "id": qid, "title": "测试用知识题", "track": "fixtures", "language": "text", "questionType": "true-false", "difficulty": "beginner", "summary": "测试数据格式与更新", "prerequisites": [], "knowledge": ["fixture"], "hints": ["本题仅用于开发测试。"], "target": "knowledge", "quiz": {"prompt": "这是用于校验知识包的开发测试题。", "answer": True, "explanation": "测试解析。"}, "origin": {"type": "self-authored", "license": "MIT", "licenseFiles": ["licenses/MIT.txt"]}}


def make_pack(root, release="1.0.0", pack_id="fixture.pack", q=None):
    root = Path(root)
    (root / "licenses").mkdir(parents=True)
    (root / "licenses/MIT.txt").write_text(LICENSE, encoding="utf-8")
    atomic_json(root / "pack.json", {"formatVersion": 1, "id": pack_id, "version": release, "title": "Fixture pack", "minEngineVersion": "0.6.0", "license": "MIT"})
    atomic_json(root / "questions.json", {"formatVersion": 1, "questions": [q or question()]})
    return root


def released(root, release="1.0.0", pack_id="fixture.pack", q=None):
    source = make_pack(root / (pack_id + "-" + release), release, pack_id, q)
    approve(source, "fixture-reviewer")
    entry = build(source, root / "dist")
    return source, root / "dist" / entry["filename"], entry


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trainer-package-tests-")
        self.root = Path(self.temp.name)
        self.store = PackStore(self.root / "store")

    def tearDown(self):
        self.temp.cleanup()

    def test_install_is_data_only_and_deterministic(self):
        source, archive, entry = released(self.root)
        again = build(source, self.root / "second")
        self.assertEqual(entry["sha256"], again["sha256"])
        with patch("subprocess.run", side_effect=AssertionError("install must not execute code")):
            self.store.install(archive, entry["sha256"])
        self.assertTrue(self.store.lessons()["fixture.pack"][0]["_needsTrust"])
        self.store.trust("fixture.pack", entry["sha256"])
        self.assertFalse(self.store.lessons()["fixture.pack"][0]["_needsTrust"])

    def test_bad_checksum_preserves_active_version(self):
        _, archive, entry = released(self.root)
        self.store.install(archive, entry["sha256"])
        before = self.store.index_file.read_bytes()
        with self.assertRaises(PackError):
            self.store.install(archive, "0" * 64)
        self.assertEqual(before, self.store.index_file.read_bytes())

    def test_upgrade_retains_old_and_resets_new_version_trust(self):
        _, archive, first = released(self.root)
        self.store.install(archive, first["sha256"])
        self.store.trust(first["id"], first["sha256"])
        _, archive2, second = released(self.root, "1.1.0")
        self.store.install(archive2, second["sha256"])
        self.assertTrue(self.store.lessons()[first["id"]][0]["_needsTrust"])
        self.assertTrue(self.store.location(first["id"], "1.0.0").is_dir())
        self.store.rollback(first["id"], "1.0.0")
        self.assertTrue(self.store.index()["pinned"][first["id"]])
        self.assertFalse(self.store.lessons()[first["id"]][0]["_needsTrust"])
        self.store.unpin(first["id"])
        self.assertFalse(self.store.index()["pinned"][first["id"]])

    def test_stale_approval_and_unlicensed_source_block_build(self):
        source, _, _ = released(self.root)
        data = json.loads((source / "questions.json").read_text(encoding="utf-8"))
        data["questions"][0]["title"] = "修改过的题目"
        atomic_json(source / "questions.json", data)
        with self.assertRaises(PackError):
            build(source, self.root / "dist")
        data["questions"][0]["origin"]["license"] = "project-license"
        atomic_json(source / "questions.json", data)
        self.assertFalse(audit(source)["passed"])

    def test_duplicate_question_and_near_duplicate_rejected(self):
        source = make_pack(self.root / "source")
        q = question()
        other = {**q, "id": "fixture.second"}
        atomic_json(source / "questions.json", {"formatVersion": 1, "questions": [q, other]})
        self.assertTrue(any("duplicate" in e for e in audit(source)["errors"]))

    def test_cross_pack_duplicate_ids_rejected(self):
        _, first, e1 = released(self.root)
        self.store.install(first, e1["sha256"])
        _, second, e2 = released(self.root, pack_id="other.pack")
        with self.assertRaises(PackError):
            self.store.install(second, e2["sha256"])
        self.assertEqual(list(self.store.index()["active"]), ["fixture.pack"])

    def test_rollback_cannot_introduce_question_id_collisions(self):
        _, first, e1 = released(self.root)
        self.store.install(first, e1["sha256"])
        _, second, e2 = released(self.root, release="2.0.0", q=question("fixture.replacement"))
        self.store.install(second, e2["sha256"])
        _, other, e3 = released(self.root, pack_id="other.pack")
        self.store.install(other, e3["sha256"])
        with self.assertRaises(PackError):
            self.store.rollback("fixture.pack", "1.0.0")
        self.assertEqual(self.store.index()["active"]["fixture.pack"], "2.0.0")

    def test_immutable_version_cannot_be_replaced(self):
        _, archive, entry = released(self.root)
        self.store.install(archive, entry["sha256"])
        different = question()
        different["title"] = "不同内容"
        alt = make_pack(self.root / "changed", q=different)
        approve(alt, "fixture-reviewer")
        changed = build(alt, self.root / "changed-dist")
        with self.assertRaises(PackError):
            self.store.install(self.root / "changed-dist" / changed["filename"], changed["sha256"])

    def test_zip_slip_symlink_reserved_and_case_collision(self):
        cases = [("../escape.txt", 0), ("/absolute.txt", 0), ("C:/escape.txt", 0), ("a\\b.txt", 0), ("CON.txt", 0), ("file.txt:stream", 0), ("link.txt", stat.S_IFLNK | 0o777)]
        for name, mode in cases:
            with self.subTest(name=name):
                data = io.BytesIO()
                with zipfile.ZipFile(data, "w") as z:
                    entry = zipfile.ZipInfo("placeholder")
                    # ZipInfo normalizes OS separators when constructed on Windows.
                    entry.filename = name
                    entry.external_attr = mode << 16
                    z.writestr(entry, "bad")
                with self.assertRaises(PackError):
                    PackStore.extract(data.getvalue(), self.root / "extract")
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("case.txt", "a")
            z.writestr("CASE.txt", "b")
        with self.assertRaises(PackError):
            PackStore.extract(data.getvalue(), self.root / "collision")
        self.assertFalse((self.root / "escape.txt").exists())

    def test_zip_expansion_limit(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("bomb.txt", "a" * (2 * 1024 * 1024))
        with self.assertRaises(PackError):
            PackStore.extract(data.getvalue(), self.root / "bomb")

    def test_payload_hash_mismatch_rejected(self):
        _, archive, _ = released(self.root)
        changed = self.root / "tampered.zip"
        with zipfile.ZipFile(archive) as src, zipfile.ZipFile(changed, "w") as dst:
            for name in src.namelist():
                data = src.read(name)
                if name == "questions.json":
                    data = data.replace("测试数据".encode(), "变更数据".encode())
                dst.writestr(name, data)
        with self.assertRaises(PackError):
            self.store.install(changed, digest(changed.read_bytes()))
        self.assertEqual(self.store.index()["active"], {})

    def test_failed_activation_keeps_previous_and_retry_recovers(self):
        _, a1, e1 = released(self.root)
        self.store.install(a1, e1["sha256"])
        _, a2, e2 = released(self.root, "1.1.0")
        with patch("trainerlib.store.atomic_json", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                self.store.install(a2, e2["sha256"])
        self.assertEqual(self.store.index()["active"][e1["id"]], "1.0.0")
        self.store.install(a2, e2["sha256"])
        self.assertEqual(self.store.index()["active"][e1["id"]], "1.1.0")

    def test_install_lock_prevents_concurrent_writers(self):
        _, archive, entry = released(self.root)
        with self.store.lock(), self.assertRaises(PackError):
            self.store.install(archive, entry["sha256"])

    def test_catalog_validation_and_offline_cache(self):
        _, archive, entry = released(self.root)
        url = "https://example.github.io/questions/catalog.json"
        item = {**entry, "url": "https://github.com/example/questions/releases/download/v1/" + entry["filename"]}
        catalog = {"formatVersion": 1, "repository": "example/questions", "packages": [item]}
        with patch("trainerlib.store.download", return_value=json.dumps(catalog).encode()):
            self.assertFalse(self.store.catalog(url)[1])
        with patch("trainerlib.store.download", side_effect=PackError("offline")):
            self.assertTrue(self.store.catalog(url)[1])
        bad = copy.deepcopy(catalog)
        bad["packages"][0]["url"] = "http://localhost/secret"
        with self.assertRaises(PackError):
            PackStore.validate_catalog(bad)
        with self.assertRaises(PackError):
            self.store.catalog("https://127.0.0.1/catalog.json")

    def test_catalog_cannot_hijack_an_existing_publisher(self):
        _, archive, entry = released(self.root)
        self.store.install(archive, entry["sha256"], source="https://first.github.io/catalog.json")
        catalog = {"packages": [{**entry, "version": "2.0.0"}]}
        with patch.object(self.store, "catalog", return_value=(catalog, False)):
            self.assertEqual(self.store.updates("https://other.github.io/catalog.json")["packages"], [])

    def test_stable_versions_and_paths(self):
        self.assertGreater(version("1.10.0"), version("1.9.9"))
        for value in ("1", "1.0.0-beta", "01.0.0", "../1.0.0"):
            with self.assertRaises(PackError):
                version(value)
        for path in ("a/../b", "a//b", "a./file.txt"):
            with self.assertRaises(PackError):
                inside(self.root, path)

    def test_code_reading_reference_is_compiled_and_answers_bound(self):
        q = question()
        code = '#include <stdio.h>\nint main(void) { printf("%d\\n", 3 + 4); return 0; }\n'
        q.update(language="c", questionType="code-reading", quiz={"prompt": "填写输出整数", "code": code, "blanks": [{"answers": ["7"], "caseSensitive": True}], "explanation": "整数相加为 7。"}, verification={"source": code, "expectedStdout": "7"})
        source = make_pack(self.root / "reading", q=q)
        compilers = {"c": trainer.find_compiler("c")}
        self.assertFalse(audit(source)["passed"], "no execution means no publication approval")
        self.assertTrue(audit(source, "native", compilers)["passed"])
        q["verification"]["expectedStdout"] = "9"
        atomic_json(source / "questions.json", {"formatVersion": 1, "questions": [q]})
        self.assertFalse(audit(source, "native", compilers)["passed"])

    def test_local_ai_rejects_remote_endpoints_without_network(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("must not connect")):
            for endpoint in ("https://api.example.com", "http://localhost.attacker.com", "http://127.0.0.1@remote.example", "http://127.0.0.1/redirect"):
                with self.assertRaises(PackError):
                    ai_variants(self.root, "fixture.basic", "local-model", endpoint=endpoint)

    def test_import_keeps_upstream_license_separate_from_authored_mit(self):
        upstream = self.root / "upstream"
        upstream.mkdir()
        # Provenance fixture only: this is not a downloadable or published package.
        files = {"LICENSE": "Apache-2.0 license placeholder for an isolated unit-test fixture.",
                 "sample.c": "/* SPDX-License-Identifier: Apache-2.0 */\nint sample(void) { return 0; }\n"}
        records = []
        for name, value in files.items():
            (upstream / name).write_bytes(value.encode())
            records.append({"path": name, "sha256": digest(value.encode())})
        atomic_json(upstream / "source.json", {"profile": "fixture", "repository": "https://github.com/example/fixture", "commit": "a" * 40, "declaredLicense": "Apache-2.0", "licenseFiles": ["LICENSE"], "files": records})
        recipe = {"source": "fixture", "pack": {"formatVersion": 1, "id": "fixture.import", "version": "1.0.0", "title": "Fixture import", "minEngineVersion": "0.6.0", "license": "mixed"}, "modifications": "Added an MIT licensed question for testing.", "authoredLicense": {"license": "MIT", "text": LICENSE}, "questions": [{"question": question()}]}
        destination = self.root / "imported"
        import_recipe(upstream, recipe, destination)
        manifest, questions = load_pack(destination)
        origin = questions[0]["origin"]
        self.assertEqual(manifest["license"], "mixed")
        self.assertEqual(origin["license"], "Apache-2.0")
        self.assertEqual(origin["authoredLicense"], "MIT")
        self.assertIn("licenses/PROJECT.txt", origin["licenseFiles"])
        self.assertEqual((destination / "upstream/sample.c").read_bytes(), files["sample.c"].encode())
        self.assertFalse((destination / "review.json").exists())

    def test_missing_format_and_future_engine_fail_closed(self):
        source = make_pack(self.root / "source")
        atomic_json(source / "questions.json", {"questions": [question()]})
        with self.assertRaises(PackError):
            load_pack(source)
        atomic_json(source / "questions.json", {"formatVersion": 1, "questions": [question()]})
        manifest = json.loads((source / "pack.json").read_text())
        atomic_json(source / "pack.json", {**manifest, "minEngineVersion": "99.0.0"})
        with self.assertRaises(PackError):
            load_pack(source)

    def test_local_source_id_cannot_be_shadowed_by_another_pack(self):
        _, archive, entry = released(self.root)
        self.store.reserved_questions = {"fixture.basic": "workspace.other"}
        with self.assertRaises(PackError):
            self.store.install(archive, entry["sha256"])
        self.assertEqual(self.store.index()["active"], {})

    def programming_fixture(self):
        q = question()
        q.update(language="c", questionType="debugging", starter="starter", reference="reference", statement="README.md",
                 build={"standard": "c11", "sources": ["answer.c"], "tests": ["test.c"], "includeDirs": ["."]})
        source = make_pack(self.root / "programming", q=q)
        for directory in ("starter", "reference", "tests"):
            (source / directory).mkdir()
        (source / "README.md").write_text("Repair add_one: return input plus one.")
        (source / "starter/answer.c").write_text("int add_one(int n) { return n; }\n")
        (source / "reference/answer.c").write_text("int add_one(int n) { return n + 1; }\n")
        (source / "tests/test.c").write_text("int add_one(int); int main(void) { return add_one(2) == 3 && add_one(-1) == 0 ? 0 : 1; }\n")
        return source

    def test_programming_requires_passing_reference_and_failing_compilable_starter(self):
        source = self.programming_fixture()
        compilers = {"c": trainer.find_compiler("c")}
        self.assertTrue(audit(source, "native", compilers)["passed"])
        (source / "starter/answer.c").write_text("int add_one(int n) { return n + 1; }\n")
        self.assertTrue(any("Starter already passes" in e for e in audit(source, "native", compilers)["errors"]))
        (source / "starter/answer.c").write_text("broken C source\n")
        self.assertTrue(any("Compilation failed" in e for e in audit(source, "native", compilers)["errors"]))

    def test_ci_report_review_is_content_bound_and_does_not_bypass_release_execution(self):
        source = self.programming_fixture()
        report = {"packId": "fixture.pack", "contentSha256": fingerprint(source), "runner": "docker", "passed": True, "referenceVerified": ["fixture.basic"]}
        with patch("trainerlib.audit.run_program", side_effect=AssertionError("must not execute locally")):
            approve(source, "human who verified CI artifact", execution_report=report)
        with self.assertRaises(PackError):
            build(source, self.root / "out", runner="none")
        (source / "README.md").write_text("Changed after CI verification.")
        with self.assertRaises(PackError):
            approve(source, "reviewer", execution_report=report)

    def test_docker_arguments_are_restricted_without_executing_container(self):
        source = self.programming_fixture()
        q = load_pack(source)[1][0]
        with patch("trainerlib.audit.limited_run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run, patch("trainerlib.audit.subprocess.run"):
            run_program(source, q, runner="docker")
        command = run.call_args.args[0]
        for flag in ("--read-only", "--cap-drop", "--pids-limit", "--memory", "--cpus", "--user"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertIn("readonly", command[command.index("--mount") + 1])
        self.assertNotIn("docker.sock", " ".join(command))

    def test_duplicate_gate_compares_other_packs(self):
        first = make_pack(self.root / "first")
        second = make_pack(self.root / "second", pack_id="second.pack", q=question("second.question"))
        self.assertFalse(audit(second, against=[first])["passed"])

    def test_template_is_deterministic_and_failure_is_atomic(self):
        template = json.loads((Path(__file__).resolve().parents[1] / "knowledge/templates/c-modulo.json").read_text(encoding="utf-8"))
        template_variants(template, self.root / "one", count=3, seed=42)
        template_variants(template, self.root / "two", count=3, seed=42)
        self.assertEqual(fingerprint(self.root / "one"), fingerprint(self.root / "two"))
        template["derive"]["answer"]["args"] = [1, 0]
        with self.assertRaises(PackError):
            template_variants(template, self.root / "bad", count=1)
        self.assertFalse((self.root / "bad").exists())

    def test_ai_draft_ignores_model_provenance_and_invalidates_review(self):
        source = make_pack(self.root / "ai")
        approve(source, "fixture-reviewer")
        candidate = {**question(), "title": "本地模型草稿", "origin": {"license": "invented"}}
        response = json.dumps({"response": json.dumps({"questions": [candidate]})}).encode()
        with patch("urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(response)
            result = ai_variants(source, "fixture.basic", "test-local-model", count=1)
        self.assertEqual(result["added"], 1)
        questions = load_pack(source)[1]
        self.assertEqual(questions[-1]["origin"]["license"], "MIT")
        self.assertEqual(questions[-1]["origin"]["generator"]["kind"], "ollama")
        with self.assertRaises(PackError):
            load_pack(source, approved=True)

    def test_process_output_is_bounded(self):
        with self.assertRaises(PackError):
            limited_run([sys.executable, "-c", "print('x' * 10000)"], limit=100)

    def test_standalone_engine_offline_install_catalog_and_submission(self):
        # Mirrors a VSIX runtime in an empty project: no content/ or source tree.
        project, runtime = self.root / "empty-workspace", self.root / "runtime"
        project.mkdir()
        runtime.mkdir()
        repository = Path(__file__).resolve().parents[1]
        shutil.copy2(repository / "trainer.py", runtime / "trainer.py")
        shutil.copytree(repository / "trainerlib", runtime / "trainerlib", ignore=shutil.ignore_patterns("__pycache__"))
        env = {**os.environ, "TRAINER_PROJECT_ROOT": str(project), "TRAINER_PACK_HOME": str(self.store.root)}

        def command(*args):
            result = subprocess.run([sys.executable, str(runtime / "trainer.py"), *args], cwd=project, env=env, capture_output=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        self.assertEqual(json.loads(command("catalog"))["lessons"], [])
        _, archive, entry = released(self.root)
        command("packs", "install", str(archive), "--sha256", entry["sha256"])
        self.assertEqual(json.loads(command("catalog"))["lessons"][0]["id"], "fixture.basic")
        command("submit", "fixture.basic", "--answer", "true")
        progress = json.loads((project / ".trainer/progress.json").read_text(encoding="utf-8"))
        self.assertEqual(progress["fixture.basic"]["status"], "passed")

    def test_existing_exercise_uses_its_trusted_old_package_after_update(self):
        source = self.programming_fixture()
        compiler = trainer.find_compiler("c")
        compilers = {"c": compiler}
        approve(source, "fixture-reviewer", "native", compilers)
        first = build(source, self.root / "dist", "native", compilers)
        self.store.install(self.root / "dist" / first["filename"], first["sha256"])
        project = self.root / "practice"
        project.mkdir()
        overrides = {"ROOT": project, "CONTENT_ROOT": project / "content", "EXERCISES_ROOT": project / "exercises", "STATE_ROOT": project / ".trainer", "BUILD_ROOT": project / ".trainer/build", "PROGRESS_FILE": project / ".trainer/progress.json"}
        env = {"TRAINER_PACK_HOME": str(self.store.root), "TRAINER_CC": compiler}
        with patch.multiple(trainer, **overrides), patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()):
            args = argparse.Namespace(lesson_id="fixture.basic")
            trainer.cmd_start(args)
            with self.assertRaises(trainer.TrainerError):
                trainer.cmd_check(args)
            self.store.trust(first["id"], first["sha256"])
            workspace = project / "exercises/fixture.basic"
            shutil.copy2(source / "reference/answer.c", workspace / "answer.c")
            original_test = (workspace / ".trainer-tests/test.c").read_bytes()
            manifest = json.loads((source / "pack.json").read_text())
            atomic_json(source / "pack.json", {**manifest, "version": "2.0.0"})
            (source / "reference/answer.c").write_text("int add_one(int n) { return n + 2; }\n")
            (source / "tests/test.c").write_text("int add_one(int); int main(void) { return add_one(2) == 4 ? 0 : 1; }\n")
            approve(source, "fixture-reviewer", "native", compilers)
            second = build(source, self.root / "dist", "native", compilers)
            self.store.install(self.root / "dist" / second["filename"], second["sha256"])
            self.assertTrue(self.store.lessons()[first["id"]][0]["_needsTrust"])
            self.assertEqual(trainer.cmd_check(args), 0, "old answer must be checked with old tests and trust")
            self.assertEqual((workspace / ".trainer-tests/test.c").read_bytes(), original_test)


if __name__ == "__main__":
    unittest.main()
