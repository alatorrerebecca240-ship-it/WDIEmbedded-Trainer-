"""Regression tests; all attempts and builds use disposable state, never learner files."""

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import trainer


TRACKS = {"linux-basics", "ros2-basics"}
REFERENCES = {
    "linux.permission.triplet-01": '''#include "permissions.h"
int permission_triplet(unsigned digit, char output[4]) {
    if (digit > 7) return -1;
    const unsigned bits[] = {4, 2, 1};
    const char symbols[] = "rwx";
    for (unsigned i = 0; i < 3; ++i) output[i] = (digit & bits[i]) ? symbols[i] : '-';
    output[3] = '\\0';
    return 0;
}
''',
    "linux.path.components-01": '''#include "path_parts.h"
size_t count_path_parts(const char *path) {
    if (!path) return 0;
    size_t count = 0;
    int in_part = 0;
    for (; *path; ++path) {
        if (*path == '/') in_part = 0;
        else if (!in_part) { ++count; in_part = 1; }
    }
    return count;
}
''',
    "ros2.message.twist-01": '''#include "twist_model.hpp"
Twist make_planar_twist(double forward, double yaw_rate) {
    Twist value{};
    value.linear.x = forward;
    value.angular.z = yaw_rate;
    return value;
}
''',
    "ros2.service.add-01": '''#include "add_service.hpp"
AddResponse handle_add(const AddRequest &request) { return {request.a + request.b}; }
''',
}


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = trainer.discover_lessons()

    def test_tracks_and_manifests(self):
        for track in TRACKS:
            lessons = [item for item in self.lessons.values() if item["track"] == track]
            self.assertEqual(Counter(item["questionType"] for item in lessons), {
                "programming": 2, "single-choice": 12, "true-false": 9, "fill-blank": 9,
            })
            self.assertGreater(sum(item["difficulty"] == "beginner" for item in lessons), 24)
            for lesson in lessons:
                with self.subTest(lesson=lesson["id"]):
                    self.assertEqual(trainer.validate_lesson(lesson), [])
                    self.assertTrue(set(lesson["prerequisites"]).issubset(self.lessons))
                    self.assertIn(lesson["difficulty"], {"beginner", "intermediate"})

    def test_text_is_only_a_quiz_language(self):
        quiz = self.lessons["linux.path.pwd-choice-01"]
        self.assertEqual(quiz["language"], "text")
        self.assertEqual(trainer.validate_lesson(quiz), [])
        programming = self.lessons["linux.path.components-01"]
        self.assertIn("编程题的 language 必须是 c 或 cpp", trainer.validate_lesson({**programming, "language": "text"}))

    def test_quiz_answers_and_rejection(self):
        # Exercise all banks as a regression check, not only the new tracks.
        for lesson in self.lessons.values():
            kind = lesson["questionType"]
            if kind == "programming":
                continue
            quiz = lesson["quiz"]
            with self.subTest(lesson=lesson["id"]):
                if kind == "fill-blank":
                    answer = [blank["answers"][0] for blank in quiz["blanks"]]
                    for index, blank in enumerate(quiz["blanks"]):
                        for alias in blank["answers"]:
                            candidate = answer.copy()
                            candidate[index] = "  " + alias + "  "
                            self.assertTrue(trainer.evaluate_quiz(lesson, candidate))
                    bad = ["__wrong_answer__"] * len(answer)
                else:
                    answer = quiz["answer"]
                    if kind == "single-choice":
                        for option in quiz["options"]:
                            self.assertEqual(trainer.evaluate_quiz(lesson, option["id"]), option["id"] == answer)
                        bad = "__wrong_answer__"
                    else:
                        bad = not answer
                        self.assertFalse(trainer.evaluate_quiz(lesson, int(answer)))
                self.assertTrue(trainer.evaluate_quiz(lesson, answer))
                self.assertFalse(trainer.evaluate_quiz(lesson, bad))
                self.assertFalse(trainer.evaluate_quiz(lesson, None))

    def test_case_sensitive_shell_answers(self):
        for lesson_id, answer in [("linux.shell.path-fill-01", "PATH"), ("ros2.domain.variable-fill-01", "ROS_DOMAIN_ID")]:
            self.assertTrue(trainer.evaluate_quiz(self.lessons[lesson_id], [answer]))
            self.assertFalse(trainer.evaluate_quiz(self.lessons[lesson_id], [answer.lower()]))
        for lesson_id, answer in [("linux.shell.status-fill-01", "$?"), ("linux.shell.redirect-fill-01", "&1")]:
            self.assertTrue(trainer.evaluate_quiz(self.lessons[lesson_id], [answer]))

    def test_submission_progress_isolated(self):
        with tempfile.TemporaryDirectory(prefix="trainer-quiz-tests-") as name:
            state = Path(name)
            with patch.multiple(trainer, STATE_ROOT=state, PROGRESS_FILE=state / "progress.json"):
                for lesson_id, answer in [("linux.path.pwd-choice-01", "A"), ("ros2.node.process-judge-01", False), ("ros2.environment.source-fill-01", ["."])]:
                    with self.subTest(lesson=lesson_id), contextlib.redirect_stdout(io.StringIO()):
                        args = argparse.Namespace(lesson_id=lesson_id, answer="null")
                        self.assertEqual(trainer.cmd_submit(args), 1)
                        self.assertEqual(trainer.load_progress()[lesson_id]["status"], "in-progress")
                        args.answer = json.dumps(answer)
                        self.assertEqual(trainer.cmd_submit(args), 0)
                        progress = trainer.load_progress()[lesson_id]
                        self.assertEqual(progress["status"], "passed")
                        self.assertEqual(progress["attempts"], 2)

    def test_programming_starters_fail_and_references_pass(self):
        for lesson_id, source in REFERENCES.items():
            lesson = self.lessons[lesson_id]
            with self.subTest(lesson=lesson_id), tempfile.TemporaryDirectory(prefix="trainer-code-tests-") as name:
                root = Path(name)
                with patch.multiple(trainer, STATE_ROOT=root / "state", PROGRESS_FILE=root / "state/progress.json", EXERCISES_ROOT=root / "exercises", BUILD_ROOT=root / "build"):
                    args = argparse.Namespace(lesson_id=lesson_id)
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(trainer.cmd_start(args), 0)
                        self.assertEqual(trainer.cmd_check(args), 1, output.getvalue())
                        workspace = root / "exercises" / lesson_id
                        solution_file = workspace / lesson["build"]["sources"][0]
                        solution_file.write_text(source, encoding="utf-8")
                        # Starting again must not overwrite a learner's implementation.
                        self.assertEqual(trainer.cmd_start(args), 0)
                        self.assertEqual(solution_file.read_text(encoding="utf-8"), source)
                        self.assertEqual(trainer.cmd_check(args), 0, output.getvalue())
                        self.assertEqual(trainer.load_progress()[lesson_id]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
