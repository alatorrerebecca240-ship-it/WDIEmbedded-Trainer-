"""Offline image orchestration tests; Docker and all network calls are mocked."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validation_image", ROOT / "scripts/validation-image.py")
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)
REPO = "Owner/Trainer"
IDENTITY = "sha256:" + "a" * 64


class ValidationImageTests(unittest.TestCase):
    def run_prepare(self, pulled=True, publish=False, label=None):
        recipe = image.recipe_hash()
        def runner(args, **kwargs):
            if args[:3] == ["docker", "image", "inspect"]:
                info = [{"Id": IDENTITY, "Config": {"Labels": {"io.embedded-trainer.recipe": label or recipe}}}]
                return SimpleNamespace(stdout=json.dumps(info), returncode=0)
            return SimpleNamespace(returncode=0 if args[1] != "pull" or pulled else 1)
        with patch.dict("os.environ", {}, clear=True), patch.object(image, "run", side_effect=runner) as run, \
                patch.object(image, "smoke") as smoke:
            result = image.prepare(REPO, publish)
        return result, run, smoke

    def test_prebuilt_image_is_smoked_and_pinned_without_rebuild_or_push(self):
        result, run, smoke = self.run_prepare()
        self.assertEqual(result["mode"], "prebuilt")
        self.assertEqual(result["imageId"], IDENTITY)
        smoke.assert_called_once_with(IDENTITY)
        self.assertFalse(any(v.args[0][1] in {"build", "push"} for v in run.call_args_list))

    def test_unpublished_image_falls_back_to_identical_recipe_not_native_or_old_image(self):
        result, run, _ = self.run_prepare(pulled=False)
        self.assertEqual(result["mode"], "built-on-runner")
        commands = [v.args[0] for v in run.call_args_list]
        self.assertEqual(sum(v[1] == "build" for v in commands), 1)
        self.assertFalse(any(v[1] == "push" for v in commands))
        self.assertTrue(all(v[0] == "docker" for v in commands))

    def test_only_explicit_publisher_pushes_new_recipe_and_reuses_existing(self):
        _, run, _ = self.run_prepare(pulled=False, publish=True)
        self.assertEqual(sum(v.args[0][1] == "push" for v in run.call_args_list), 1)
        _, run, _ = self.run_prepare(publish=True)
        self.assertFalse(any(v.args[0][1] == "push" for v in run.call_args_list))

    def test_wrong_recipe_rejected(self):
        with self.assertRaisesRegex(ValueError, "label mismatch"):
            self.run_prepare(label="b" * 64)

    def test_smoke_is_isolated_and_cleaned_up_on_timeout(self):
        with patch.object(image, "run", side_effect=[subprocess.TimeoutExpired("docker", 120), None]) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                image.smoke(IDENTITY)
        args = run.call_args_list[0].args[0]
        for flag in ("--read-only", "--memory", "--cpus", "--pids-limit", "--cap-drop"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--network") + 1], "none")
        self.assertEqual(run.call_args_list[1].args[0][:3], ["docker", "rm", "-f"])
        self.assertNotIn("--mount", args)

    def test_recipe_is_line_ending_independent_and_changes_with_contents(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            for filename in image.RECIPE_FILES:
                (folder / filename).write_bytes((image.CONTEXT / filename).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            self.assertEqual(image.recipe_hash(folder), image.recipe_hash())
            (folder / "smoke.c").write_text("changed", encoding="utf-8")
            self.assertNotEqual(image.recipe_hash(folder), image.recipe_hash())

    def test_names_reject_untrusted_registry_or_shell_tokens(self):
        for repo in ("../repo", "https://evil.invalid/repo", "owner/repo;evil", "owner/repo\nTOKEN=x"):
            with self.assertRaises(ValueError):
                image.image_name(repo, "a" * 64)

    def test_workflows_cache_only_blobs_and_keep_image_publishing_separate(self):
        workflow = (ROOT / ".github/workflows/acquire-review.yml").read_text(encoding="utf-8")
        self.assertIn("path: .imports/ci-blobs", workflow)
        self.assertNotIn("packages: write", workflow)
        self.assertNotIn("secrets.", workflow)
        builder = (ROOT / ".github/workflows/build-validation-image.yml").read_text(encoding="utf-8")
        self.assertIn("github.ref == 'refs/heads/main'", builder)
        self.assertIn("packages: write", builder)
        self.assertNotIn("pull_request", builder)
        for filename in ("acquire-review.yml", "review-draft.yml", "exercism-pilot.yml", "publish-knowledge.yml"):
            content = (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8")
            self.assertIn("python scripts/validation-image.py", content)
            self.assertNotIn("docker pull gcc:14", content)


if __name__ == "__main__":
    unittest.main()
