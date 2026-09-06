"""Existing evidence publication must never reexecute question code."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_knowledge import make_pack
from trainerlib.audit import approve, build_from_report
from trainerlib.common import PackError, read_json
from trainerlib.format import fingerprint


class ExistingEvidenceTests(unittest.TestCase):
    def test_bound_report_packages_without_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = make_pack(root / "source")
            report = {"formatVersion": 1, "packId": "fixture.pack", "runner": "docker",
                      "contentSha256": fingerprint(source), "passed": True,
                      "referenceVerified": [], "errors": []}
            approve(source, "fixture-reviewer", execution_report=report)
            with patch("trainerlib.audit.run_program", side_effect=AssertionError("Must not execute")):
                entry = build_from_report(source, root / "dist", report, {"runId": 1})
            self.assertTrue((root / "dist" / entry["filename"]).exists())
            stored = read_json(root / "dist" / "fixture.pack-1.0.0.audit.json")
            self.assertEqual(stored["runner"], "ci-report")
            self.assertEqual(stored["originalExecutionReport"], report)
            for key, value in [("runner", "native"), ("passed", False), ("contentSha256", "0" * 64)]:
                changed = {**report, key: value}
                with self.assertRaises(PackError):
                    build_from_report(source, root / "bad", changed, {})
            with (source / "licenses/MIT.txt").open("a", encoding="utf-8") as file:
                file.write("\nChanged payload\n")
            with self.assertRaises(PackError):
                build_from_report(source, root / "changed", report, {})
