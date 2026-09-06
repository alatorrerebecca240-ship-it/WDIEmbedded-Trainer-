"""Synthetic source fixtures and mocked execution only; never run upstream code."""
import copy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import test_exercism as fixtures
from trainerlib.audit import CompilationError, audit, run_program
from trainerlib.common import PackError
from trainerlib.format import fingerprint, load_pack
from trainerlib.scaffolds import expected_scaffold_error, starter_mode


class ScaffoldTests(TestCase):
    def setUp(self):
        self.fixture = fixtures.ExercismTests()
        self.fixture.setUp()
        self.fixture.scanned()
        self.root = Path(self.fixture.imported()["destination"])
        self.q = load_pack(self.root)[1][0]

    def tearDown(self):
        self.fixture.tearDown()

    def test_unmodified_upstream_starter_is_recognized_without_rewriting(self):
        before = fingerprint(self.root)
        self.assertEqual(starter_mode(self.root, self.q), "upstream-scaffold")
        self.assertEqual(fingerprint(self.root), before)

    def test_edited_extra_and_unretained_files_do_not_qualify(self):
        file = self.q["_lessonDir"] / "starter/leap.c"
        previous = file.read_bytes()
        file.write_bytes(previous + b"// edited\n")
        self.assertEqual(starter_mode(self.root, self.q), "compilable")
        file.write_bytes(previous)
        extra = file.parent / "extra.h"
        extra.write_text("// extra file")
        self.assertEqual(starter_mode(self.root, self.q), "compilable")
        extra.unlink()
        altered = copy.deepcopy(self.q)
        altered["origin"]["sourceFiles"] = []
        self.assertEqual(starter_mode(self.root, altered), "compilable")

    def test_spoofed_publisher_generated_and_debugging_remain_strict(self):
        for update in ({"repository": "https://github.com/other/c"}, {"type": "generated"},
                       {"generator": {"kind": "ai"}}, {"commit": "main"}):
            q = copy.deepcopy(self.q)
            q["origin"].update(update)
            self.assertEqual(starter_mode(self.root, q), "compilable")
        self.assertEqual(starter_mode(self.root, {**self.q, "questionType": "debugging"}), "compilable")
        self.assertEqual(starter_mode(self.root, {**self.q, "variantOf": "seed"}), "compilable")

    def test_original_scaffold_compile_error_is_a_warning_after_reference_passes(self):
        before = fingerprint(self.root)
        with patch("trainerlib.audit.run_program", side_effect=[{}, CompilationError("undefined reference to 'leap'")]) as run:
            report = audit(self.root, runner="docker")
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(report["referenceVerified"], [self.q["id"]])
        self.assertEqual(report["checks"][self.q["id"]]["starter"], "expected-incomplete-scaffold")
        self.assertIn("原始上游框架", report["warnings"][0])
        self.assertEqual(fingerprint(self.root), before)

    def test_reference_failure_never_downgrades_to_scaffold_warning(self):
        with patch("trainerlib.audit.run_program", side_effect=CompilationError("undefined reference to 'leap'")) as run:
            report = audit(self.root, runner="docker")
        self.assertFalse(report["passed"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(report["referenceVerified"], [])
        self.assertIn("参考答案", report["errors"][0])

    def test_missing_dependency_timeout_and_already_passing_starter_still_fail(self):
        for error in (CompilationError("fatal error: missing.h: No such file or directory"),
                      CompilationError("internal compiler error: Killed"),
                      PackError("Sandbox execution timed out"),
                      PackError("Starter already passes; no effective exercise")):
            with self.subTest(error=str(error)):
                with patch("trainerlib.audit.run_program", side_effect=[{}, error]):
                    report = audit(self.root, runner="docker")
                self.assertFalse(report["passed"])
                self.assertEqual(report["checks"][self.q["id"]]["reference"], "passed")
                self.assertIn("初始代码", report["errors"][0])

    def test_edited_starter_does_not_downgrade_matching_error(self):
        (self.q["_lessonDir"] / "starter/leap.c").write_text("broken source")
        with patch("trainerlib.audit.run_program", side_effect=[{}, CompilationError("unknown type name 'X'")]):
            report = audit(self.root, runner="docker")
        self.assertFalse(report["passed"])

    def test_diagnostics_are_narrowly_classified(self):
        for message in ("undefined reference to 'f'", "'x' is not a member of 'x'", "empty enum is invalid"):
            self.assertTrue(expected_scaffold_error(message))
        for message in ("syntax error", "fatal error: missing.h", "undefined reference to f\nKilled",
                        "Cannot allocate memory", "Compiler could not start"):
            self.assertFalse(expected_scaffold_error(message))

    def test_real_run_wrapper_raises_typed_compile_error_without_executing(self):
        from subprocess import CompletedProcess
        with patch("trainerlib.audit.limited_run", return_value=CompletedProcess([], 120, "", "undefined reference to f")), \
                patch("trainerlib.audit.subprocess.run"):
            with self.assertRaises(CompilationError):
                run_program(self.root, self.q, reference=False, runner="docker")

    def test_static_validation_remains_execution_free(self):
        from trainerlib.inbox import static_errors
        with patch("subprocess.Popen", side_effect=AssertionError("No process allowed")):
            errors, _ = static_errors(self.root)
        self.assertEqual(errors, [])

    def test_host_image_is_used_without_weakening_container_limits(self):
        from subprocess import CompletedProcess
        image = "sha256:" + "c" * 64
        with patch.dict("os.environ", {"TRAINER_VALIDATION_IMAGE": image}), \
                patch("trainerlib.audit.limited_run", return_value=CompletedProcess([], 0, "", "")) as run, \
                patch("trainerlib.audit.subprocess.run"):
            run_program(self.root, self.q, runner="docker")
        command = run.call_args.args[0]
        self.assertIn(image, command)
        for flag, value in (("--network", "none"), ("--cap-drop", "ALL"), ("--user", "65534:65534")):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertIn("--read-only", command)
