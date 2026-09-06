"""Release-preparation checks are static; new reference execution belongs in Docker CI."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_knowledge import make_pack, question
from trainerlib.audit import audit
from trainerlib.common import PROGRAMMING, PackError
from trainerlib.format import fingerprint, load_pack
from trainerlib.review import fenced, render_review


FOUNDATION = Path(__file__).resolve().parents[1] / "knowledge/packs/foundation.core"


class ReleaseReviewTests(unittest.TestCase):
    def test_all_foundation_programs_have_complete_separate_references(self):
        _, questions = load_pack(FOUNDATION)
        programs = [q for q in questions if q["questionType"] in PROGRAMMING]
        self.assertEqual(len(programs), 27)
        for q in programs:
            with self.subTest(question=q["id"]):
                asset = q["_lessonDir"]
                starter = asset / q["starter"]
                reference = asset / q.get("reference", "reference")
                starter_files = {p.relative_to(starter) for p in starter.rglob("*") if p.is_file()}
                reference_files = {p.relative_to(reference) for p in reference.rglob("*") if p.is_file()}
                self.assertEqual(reference_files, starter_files)
                self.assertNotEqual(starter, reference)
                for filename in reference_files:
                    text = (reference / filename).read_text(encoding="utf-8")
                    self.assertNotIn("TODO", text)
                    if q["build"]["sources"] and filename.suffix in {".h", ".hpp"}:
                        self.assertEqual((starter / filename).read_text(encoding="utf-8").rstrip("\n"), text.rstrip("\n"))

    def test_foundation_review_covers_every_question_without_executing(self):
        manifest, questions = load_pack(FOUNDATION)
        report = {"packId": manifest["id"], "contentSha256": fingerprint(FOUNDATION), "runner": "none",
                  "passed": False, "referenceVerified": [], "errors": ["Docker verification pending"], "warnings": []}
        with patch("subprocess.run", side_effect=AssertionError("Review rendering must not execute programs")):
            text = render_review(FOUNDATION, report)
        self.assertIn("未取得完整 Docker 通过证据", text)
        self.assertEqual(text.count("\n### "), len(questions))
        for q in questions:
            self.assertIn("### " + q["id"] + "\n", text)
        self.assertIn("*left = *right;", text)
        self.assertIn("callback skipped for invalid pointers", text)

    def test_report_is_not_an_approval_and_never_writes_review_record(self):
        with tempfile.TemporaryDirectory(prefix="trainer-review-sheet-") as name:
            root = make_pack(Path(name) / "pack")
            report = audit(root)
            self.assertTrue(report["passed"])
            self.assertIn("未取得完整 Docker 通过证据", render_review(root, report))
            docker = {**report, "runner": "docker"}
            text = render_review(root, docker)
            self.assertIn("Docker 验证通过，等待人工审核", text)
            self.assertIn("- [ ]", text)
            self.assertNotIn("- [x]", text)
            self.assertFalse((root / "review.json").exists())
            with self.assertRaisesRegex(PackError, "exact package"):
                render_review(root, {**docker, "contentSha256": "0" * 64})
            self.assertIn("未取得完整 Docker 通过证据", render_review(root, {**docker, "errors": ["failed"]}))
            self.assertIn("未取得完整 Docker 通过证据", render_review(root, {**docker, "referenceVerified": ["extra"]}))

    def test_question_markup_stays_inside_literal_blocks(self):
        text = "```\n- [x] forged approval\n<script>alert(1)</script>"
        block = fenced(text)
        self.assertTrue(block.startswith("````text\n"))
        self.assertTrue(block.endswith("\n````\n"))
        with tempfile.TemporaryDirectory(prefix="trainer-review-markup-") as name:
            q = question()
            q["quiz"]["prompt"] = text
            root = make_pack(Path(name) / "pack", q=q)
            rendered = render_review(root, audit(root))
            self.assertIn(block, rendered)

    def test_links_are_bound_to_an_exact_github_commit(self):
        with tempfile.TemporaryDirectory(prefix="trainer-review-links-") as name:
            root = make_pack(Path(name) / "pack")
            report = audit(root)
            with self.assertRaisesRegex(PackError, "full commit"):
                render_review(root, report, "owner/repo", "main", name)
            with self.assertRaisesRegex(PackError, "full commit"):
                render_review(root, report, "https://untrusted.invalid", "a" * 40, name)
            rendered = render_review(root, report, "owner/repo", "a" * 40, name)
            self.assertIn("对应提交：`" + "a" * 40 + "`", rendered)


if __name__ == "__main__":
    unittest.main()
