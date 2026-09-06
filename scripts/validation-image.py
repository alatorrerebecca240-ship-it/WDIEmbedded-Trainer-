"""Prepare a recipe-versioned validation image on a Linux Actions runner only.

The publish job handles its own GHCR login. Verification receives no credentials.
No upstream question is built into, or executed while publishing, the image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "docker/validation"
RECIPE_FILES = ("Dockerfile", "smoke.c", "smoke.cpp", "smoke.sh")


def recipe_hash(context=CONTEXT):
    sha = hashlib.sha256()
    for name in RECIPE_FILES:
        # Git checkouts with CRLF and LF identify the same build recipe.
        sha.update(name.encode() + b"\0" + (context / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return sha.hexdigest()


def image_name(repository, recipe):
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository)
            or not re.fullmatch(r"[a-f0-9]{64}", recipe)):
        raise ValueError("Invalid image repository or recipe")
    return f"ghcr.io/{repository.lower()}-validator:recipe-{recipe}"


def run(args, *, timeout=240, capture=False, check=True):
    return subprocess.run(args, check=check, timeout=timeout, text=True, capture_output=capture)


def smoke(image):
    name = "trainer-image-smoke-" + uuid.uuid4().hex
    try:
        run(["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only",
             "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "64",
             "--memory", "768m", "--cpus", "1", "--user", "65534:65534",
             "--tmpfs", "/tmp:rw,exec,nosuid,size=64m,mode=1777", "--entrypoint", "sh",
             image, "/opt/trainer/smoke.sh"], timeout=120)
    finally:
        run(["docker", "rm", "-f", name], timeout=15, capture=True, check=False)


def prepare(repository, publish=False):
    recipe = recipe_hash()
    image = image_name(repository, recipe)
    started = time.perf_counter()
    # Existing recipe tags are reused, never deliberately overwritten.
    try:
        pulled = run(["docker", "pull", image], check=False).returncode == 0
    except subprocess.TimeoutExpired:
        pulled = False
    if not pulled:
        print("Prebuilt image unavailable; building the same recipe on this cloud runner.", flush=True)
        run(["docker", "build", "--pull", "--label", f"org.opencontainers.image.source=https://github.com/{repository}",
             "--label", f"io.embedded-trainer.recipe={recipe}", "-t", image, str(CONTEXT)], timeout=1200)
    info = json.loads(run(["docker", "image", "inspect", image], capture=True).stdout)[0]
    if info.get("Config", {}).get("Labels", {}).get("io.embedded-trainer.recipe") != recipe:
        raise ValueError("Validation image recipe label mismatch")
    identity = info.get("Id", "")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", identity):
        raise ValueError("Missing immutable local image ID")
    smoke(identity)
    if publish and not pulled:
        run(["docker", "push", image], timeout=1200)
    result = {"image": image, "imageId": identity, "recipeSha256": recipe,
              "mode": "prebuilt" if pulled else "built-on-runner",
              "prepareSeconds": round(time.perf_counter() - started, 3)}
    # Only this trusted host process sets the image; drafts cannot select it.
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as stream:
            stream.write(f"TRAINER_VALIDATION_IMAGE={identity}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write(f"\n## Validation image\n\n- Mode: {result['mode']}\n- Recipe: `{recipe}`\n"
                         f"- Image ID: `{identity}`\n- Preparation: {result['prepareSeconds']} s\n")
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_OS") != "Linux":
        parser.error("Run this helper on a Linux GitHub Actions runner; it does not configure local Docker.")
    prepare(os.environ["GITHUB_REPOSITORY"], args.publish)
