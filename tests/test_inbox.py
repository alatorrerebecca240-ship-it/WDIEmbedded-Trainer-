"""Synthetic fixtures only: neither network nor real Docker/upstream execution."""
import copy
import json
import shutil
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import test_exercism as fixtures
from trainerlib.common import PackError, atomic_json, canonical, digest, read_json
from trainerlib.format import fingerprint, load_pack
from trainerlib.inbox import Inbox, normalized_pack, validate_plan
from trainerlib.inbox_ci import verify_plan

REQUEST = "1" * 32
QID = "oss.exercism.c.leap"


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExercismTests()
        self.fixture.setUp()
        self.fixture.scanned()
        source = Path(self.fixture.imported()["destination"])
        self.root = self.fixture.root / "workspace"
        self.legacy = self.root / "knowledge/drafts/pilot"
        shutil.copytree(source, self.legacy)
        self.index = self.root / ".imports/exercism-index.json"
        atomic_json(self.index, read_json(self.fixture.index))
        self.inbox = Inbox(self.root)

    def tearDown(self):
        self.fixture.tearDown()

    def acquire(self):
        with patch("trainerlib.inbox.scan", side_effect=PackError("offline fixture")), \
                patch("subprocess.Popen", side_effect=AssertionError("No native execution")):
            return self.inbox.acquire(self.fixture.license, offline=True)

    def evidence(self, plan, passed=True, extra=None):
        entry = plan["entries"][0]
        pack = self.inbox.pack(self.inbox.read()["items"][entry["id"]])
        report = {"formatVersion": 1, "packId": load_pack(pack)[0]["id"], "runner": "docker", "passed": passed,
            "contentSha256": entry["contentSha256"], "referenceVerified": [entry["id"]] if passed else [],
            "errors": [] if passed else ["Compilation failed: fixture"], "warnings": []}
        if extra:
            report.update(extra)
        response = {"pipelineVersion": 1, "requestId": plan["requestId"], "planSha256": digest(canonical(plan)),
            "results": [{"id": entry["id"], "audit": report}]}
        archive = self.fixture.root / (plan["requestId"] + ".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("inbox-results.json", canonical(response))
        return archive, digest(archive.read_bytes())

    def ready(self):
        self.acquire()
        plan = self.inbox.prepare(REQUEST)
        archive, sha = self.evidence(plan)
        self.inbox.results(REQUEST, archive, sha)
        return self.inbox.pack(self.inbox.read()["items"][QID])

    def test_old_drafts_adopt_once_without_changing_originals(self):
        before = fingerprint(self.legacy)
        result = self.acquire()
        self.assertEqual(result["adopted"], 1)
        self.assertEqual(result["counts"], {"pending": 1})
        self.assertEqual(self.acquire()["adopted"], 0)
        self.assertEqual(fingerprint(self.legacy), before)
        self.assertFalse((self.root / "knowledge/approved").exists())
        self.assertIn("reference", str(self.inbox.details(QID)["files"]))

    def test_normalization_is_source_folder_independent(self):
        self.acquire()
        entry = self.inbox.read()["items"][QID]
        target = self.fixture.root / "other-normalized"
        self.assertEqual(normalized_pack(self.legacy, target, QID), entry["contentSha256"])

    def test_one_import_failure_does_not_block_next_question(self):
        index = read_json(self.index)
        for slug in ("another-a", "another-b"):
            q = {**index["candidates"][0], "slug": slug, "key": "c/" + slug, "title": slug}
            index["candidates"].append(q)
        index["sha256"] = digest(canonical({k: v for k, v in index.items() if k != "sha256"}))
        atomic_json(self.index, index)
        def importing(index, destination, cache, keys, project_license):
            if keys == ["c/another-a"]:
                raise PackError("Unsupported fixture layout")
            shutil.copytree(self.legacy, destination)
            data = read_json(Path(destination) / "questions.json")
            q = data["questions"][0]
            q.update(id="oss.exercism.c.another-b", title="A different exercise", summary="独立的数组遍历与边界统计题")
            atomic_json(Path(destination) / "questions.json", data)
        with patch("trainerlib.inbox.import_batch", side_effect=importing):
            result = self.acquire()
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["total"], 3)

    def test_machine_pass_does_not_approve_and_human_ack_required(self):
        pack = self.ready()
        self.assertFalse((pack / "review.json").exists())
        self.assertEqual(self.inbox.listing()["counts"], {"ready": 1})
        with self.assertRaises(PackError):
            self.inbox.decide([QID], "approve", "reviewer")
        result = self.inbox.decide([QID], "approve", "reviewer", True, True)
        self.assertEqual(result["completed"], [QID])
        self.assertEqual(result["publication"], "not-run")
        load_pack(pack, approved=True)
        self.assertFalse((self.root / "knowledge/approved").exists())
        self.assertEqual(self.inbox.stage_approved()["staged"], [QID])
        self.assertEqual(self.inbox.stage_approved()["staged"], [QID], "identical stage is idempotent")

    def test_failed_or_native_or_wrong_hash_reports_cannot_be_approved(self):
        self.acquire()
        for number, extra in enumerate(({"runner": "native"}, {"contentSha256": "0" * 64}, {"referenceVerified": []}, {"passed": False})):
            request = str(number + 2) * 32
            plan = self.inbox.prepare(request)
            archive, sha = self.evidence(plan, extra=extra)
            self.inbox.results(request, archive, sha)
            self.assertEqual(self.inbox.listing()["counts"], {"validation-failed": 1})
            result = self.inbox.decide([QID], "approve", "reviewer", True, True)
            self.assertEqual(result["completed"], [])

    def test_content_edits_invalidate_evidence_and_approval(self):
        pack = self.ready()
        (pack / "README.md").write_text("changed source", encoding="utf-8")
        self.assertEqual(self.inbox.listing()["counts"], {"changed": 1})
        self.assertFalse(self.inbox.decide([QID], "approve", "reviewer", True, True)["completed"])
        plan = self.inbox.prepare("8" * 32)
        self.assertEqual(plan["entries"][0]["mode"], "repository")
        self.assertEqual(plan["entries"][0]["contentSha256"], fingerprint(pack))
        self.assertTrue(plan["entries"][0]["path"].startswith("knowledge/drafts/inbox/"))

    def test_stale_results_and_deferred_questions_stay_unapproved(self):
        self.acquire()
        old = self.inbox.prepare(REQUEST)
        self.inbox.fail_request(REQUEST, "retry")
        newer = "2" * 32
        self.inbox.prepare(newer)
        archive, sha = self.evidence(old)
        self.inbox.results(REQUEST, archive, sha)
        self.assertEqual(self.inbox.read()["items"][QID]["requestId"], newer)
        self.assertEqual(self.inbox.listing()["counts"], {"checking": 1})
        self.inbox.decide([QID], "defer")
        self.inbox.fail_request(newer, "late failure")
        self.assertEqual(self.inbox.listing()["counts"], {"deferred": 1})

    def test_no_duplicate_dispatch_and_inbox_lock(self):
        self.acquire()
        self.assertEqual(len(self.inbox.prepare(REQUEST)["entries"]), 1)
        self.assertEqual(self.inbox.prepare("2" * 32)["entries"], [])
        with self.inbox.lock(), self.assertRaises(PackError):
            self.inbox.prepare("3" * 32)

    def test_artifact_checksum_zip_slip_and_missing_results_rejected(self):
        self.acquire()
        plan = self.inbox.prepare(REQUEST)
        archive, sha = self.evidence(plan)
        with self.assertRaises(PackError):
            self.inbox.results(REQUEST, archive, "0" * 64)
        with zipfile.ZipFile(archive, "a") as z:
            z.writestr("../../escaped.txt", "never extract")
        with self.assertRaises(PackError):
            self.inbox.results(REQUEST, archive, digest(archive.read_bytes()))
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_plan_disallows_unpinned_sources_paths_and_duplicate_questions(self):
        self.acquire()
        plan = self.inbox.prepare(REQUEST)
        for field, value in (("key", "c/../../bad"), ("commit", "main"), ("contentSha256", "bad")):
            candidate = copy.deepcopy(plan)
            candidate["entries"][0][field] = value
            with self.assertRaises(PackError):
                validate_plan(candidate)
        plan["entries"] *= 2
        with self.assertRaises(PackError):
            validate_plan(plan)

    def test_repository_mode_cannot_read_arbitrary_paths(self):
        self.acquire()
        plan = self.inbox.prepare(REQUEST)
        plan["entries"][0].update(mode="repository", path=".trainer/progress.json")
        with self.assertRaises(PackError):
            validate_plan(plan)

    def test_repository_mode_checks_exact_committed_content_without_download(self):
        pack = self.ready()
        (pack / "README.md").write_text("reviewed edit", encoding="utf-8")
        plan = self.inbox.prepare("7" * 32)
        output = self.fixture.root / "repository-result.json"
        with patch("trainerlib.inbox_ci.scan", side_effect=AssertionError("no upstream download")), \
                patch("trainerlib.inbox_ci.audit", return_value={"passed": True}) as check:
            result = verify_plan(plan, output, self.root / "LICENSE")
        self.assertEqual(result["verified"], 1)
        self.assertEqual(check.call_args.kwargs, {"runner": "docker"})

    def test_ci_uses_only_docker_and_retains_success_beside_failure(self):
        self.acquire()
        plan = self.inbox.prepare(REQUEST)
        second = {**plan["entries"][0], "id": "oss.exercism.c.another", "key": "c/another"}
        plan["entries"].append(second)
        output = self.fixture.root / "ci.json"
        with patch("trainerlib.inbox_ci.scan"), patch("trainerlib.inbox_ci.import_batch"), \
                patch("trainerlib.inbox_ci.normalized_pack", return_value=second["contentSha256"]), \
                patch("trainerlib.inbox_ci.audit", side_effect=[{"passed": True}, {"passed": False, "errors": ["fixture failed"]}]) as audit:
            result = verify_plan(plan, output, self.fixture.license)
        self.assertEqual(result, {"verified": 1, "total": 2})
        self.assertTrue(all(call.kwargs == {"runner": "docker"} for call in audit.call_args_list))
        self.assertEqual(len(read_json(output)["results"]), 2)


if __name__ == "__main__":
    unittest.main()
