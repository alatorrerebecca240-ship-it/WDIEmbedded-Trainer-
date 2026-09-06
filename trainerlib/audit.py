"""Publication gates: structure, provenance, duplicates, reference execution and review."""

import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .common import LICENSES, PROGRAMMING, PackError, atomic_json, canonical, digest, inside, read_json
from .format import fingerprint, load_pack, payload_files
from .process import limited_run


def run_program(root, q, reference=True, runner="none", compiler=None, image="gcc:14"):
    """Only an explicit native/docker audit may run content; install never calls this."""
    if runner not in {"native", "docker"}:
        raise PackError("Reference execution requires --runner docker or explicitly trusted --runner native")
    asset = q["_lessonDir"]
    with tempfile.TemporaryDirectory(prefix="trainer-audit-") as name:
        work = Path(name)
        if q["questionType"] in PROGRAMMING:
            source_root = inside(asset, q.get("reference", "reference") if reference else q["starter"])
            if not source_root.is_dir():
                raise PackError("Reference implementation directory is required")
            shutil.copytree(source_root, work, dirs_exist_ok=True)
            shutil.copytree(asset / "tests", work / "tests", dirs_exist_ok=True)
            build = q["build"]
            sources = [*build["sources"], *("tests/" + s for s in build["tests"])]
            includes = build.get("includeDirs", ["."])
        else:
            check = q.get("verification")
            if not isinstance(check, dict) or not isinstance(check.get("expectedStdout"), str):
                raise PackError("Code reading requires executable verification and expectedStdout")
            if check.get("source") != q["quiz"]["code"]:
                raise PackError("Displayed code must exactly match the verified code")
            blanks = q["quiz"]["blanks"]
            if len(blanks) != 1 or check["expectedStdout"].strip() not in [a.strip() for a in blanks[0]["answers"]]:
                raise PackError("Code reading answer must match verified stdout")
            filename = "reading.c" if q["language"] == "c" else "reading.cpp"
            (work / filename).write_text(check["source"], encoding="utf-8")
            sources, includes = [filename], ["."]
            build = {"standard": "c11" if q["language"] == "c" else "c++17"}
        tool = "gcc" if q["language"] == "c" else "g++"
        options = [f"-std={build['standard']}", "-Wall", "-Wextra", "-Wpedantic", "-Werror", *["-I" + p for p in includes], *sources, *["-l" + lib for lib in build.get("linkLibraries", [])]]
        if runner == "docker":
            # TemporaryDirectory is 0700 on Linux; the unprivileged container user
            # needs read/traverse permission on this disposable, code-only copy.
            work.chmod(0o755)
            for entry in work.rglob("*"):
                entry.chmod(0o755 if entry.is_dir() else 0o644)
            if not re.fullmatch(r"[a-zA-Z0-9./:_@-]+", image):
                raise PackError("Invalid container image")
            container = "trainer-audit-" + uuid.uuid4().hex
            # Read-only inputs; no host home, credentials, sockets, or network mounts.
            command = ["docker", "run", "--rm", "--name", container, "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "64", "--memory", "256m", "--cpus", "1", "--user", "65534:65534", "--tmpfs", "/tmp:rw,exec,nosuid,size=64m,mode=1777", "--mount", f"type=bind,source={work},target=/work,readonly", "-w", "/work", image, "sh", "-c", " ".join(shlex.quote(p) for p in [tool, *options, "-o", "/tmp/answer"]) + " || exit 120; /tmp/answer"]
            try:
                result = limited_run(command, timeout=60)
            except subprocess.TimeoutExpired as exc:
                raise PackError("Sandbox execution timed out") from exc
            finally:
                subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=15)
            if result.returncode in {125, 126, 127}:
                raise PackError("Container could not start")
            # A starter compiler error must not be misreported as an expected failing test.
            if result.returncode == 120:
                raise PackError("Compilation failed: " + result.stderr[:4000])
        else:
            executable = work / ("answer.exe" if os.name == "nt" else "answer")
            command = [compiler or tool, *options, "-o", str(executable)]
            try:
                compiled = limited_run(command, cwd=work, timeout=30)
                if compiled.returncode:
                    raise PackError("Compilation failed: " + compiled.stderr[:4000])
                result = limited_run([str(executable)], cwd=work, timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise PackError("Compile/test timed out") from exc
        if reference and result.returncode:
            raise PackError("Reference tests failed: " + result.stdout[:2000] + result.stderr[:2000])
        if not reference and result.returncode == 0:
            raise PackError("Starter already passes; no effective exercise")
        if q["questionType"] == "code-reading" and result.stdout.strip() != q["verification"]["expectedStdout"].strip():
            raise PackError("Verified stdout does not match reference answer")
        return {"runner": runner, "passed": True}


def copyright_errors(q, root):
    errors = []
    origin = q.get("origin", {})
    if origin.get("license") not in LICENSES:
        errors.append("A supported explicit SPDX license is required; project-license/unknown is not publishable")
    if "authoredLicense" in origin and origin["authoredLicense"] not in LICENSES:
        errors.append("Newly authored adaptations need a supported explicit license")
    licenses = origin.get("licenseFiles", [])
    if not licenses:
        errors.append("Retained license text is required")
    for file in licenses + origin.get("noticeFiles", []):
        path = inside(root, file)
        if not path.is_file() or path.stat().st_size < 30:
            errors.append("Missing license/notice file: " + file)
    if origin.get("type") in {"imported", "adapted"}:
        if not re.fullmatch(r"[a-f0-9]{40}", origin.get("commit", "")) or not re.fullmatch(r"https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", origin.get("repository", "")):
            errors.append("Imported content needs repository URL and pinned full commit")
        sources = origin.get("sourceFiles", [])
        if not sources or not origin.get("modifications"):
            errors.append("Imported content needs retained sources and modification notice")
        for source in sources:
            path = inside(root, source.get("retainedPath"))
            if not path.exists() or digest(path.read_bytes()) != source.get("sha256"):
                errors.append("Retained upstream source hash mismatch")
            else:
                markers = re.findall(r"SPDX-License-Identifier:\s*([^\r\n*]+)", path.read_text(encoding="utf-8"))
                if any(marker.strip() != origin.get("license") for marker in markers):
                    errors.append("File-level SPDX differs from declared license; manual adaptation required")
    if origin.get("type") not in {"self-authored", "imported", "adapted", "generated"}:
        errors.append("Unknown provenance type")
    if origin.get("type") == "generated" and not origin.get("generator"):
        errors.append("Generated question needs generator provenance")
    return errors


def audit(root, runner="none", compilers=None, against=(), execution_report=None):
    errors, warnings, executed = [], [], []
    try:
        manifest, questions = load_pack(root)
        content_sha = fingerprint(root)
        if execution_report is not None:
            required = {q["id"] for q in questions if q["questionType"] in PROGRAMMING | {"code-reading"}}
            if (execution_report.get("passed") is not True or execution_report.get("runner") != "docker"
                    or execution_report.get("packId") != manifest["id"]
                    or execution_report.get("contentSha256") != content_sha
                    or set(execution_report.get("referenceVerified", [])) != required):
                raise PackError("CI Docker report is failed, incomplete or does not match this exact source")
        if manifest["license"] not in LICENSES and manifest["license"] != "mixed":
            errors.append("Pack license is not explicitly selected")
        comparison = []
        for other in against:
            comparison.extend(load_pack(other)[1])
        signatures = []
        for q in comparison + questions:
            quiz = q.get("quiz", {})
            prompt = quiz.get("prompt", q.get("summary", ""))
            text = re.sub(r"\s+", " ", prompt + "\n" + quiz.get("code", "")).strip().casefold()
            is_current = q in questions
            if is_current:
                for previous, prev_text in signatures:
                    score = difflib.SequenceMatcher(None, text, prev_text, autojunk=False).ratio()
                    same_family = q.get("variantOf") and q.get("variantOf") == previous.get("variantOf") and q.get("parameters") != previous.get("parameters")
                    if score == 1 or (score >= .93 and not same_family):
                        errors.append(f"{q['id']}: duplicate/near-duplicate of {previous['id']} ({score:.2f})")
                    elif score >= .85:
                        warnings.append(f"{q['id']}: similar to {previous['id']} ({score:.2f}); reviewer must inspect")
                errors.extend(f"{q['id']}: {error}" for error in copyright_errors(q, root))
                if q["questionType"] in PROGRAMMING | {"code-reading"}:
                    try:
                        if execution_report is None:
                            compiler = (compilers or {}).get(q["language"])
                            run_program(root, q, runner=runner, compiler=compiler)
                            if q["questionType"] in PROGRAMMING:
                                run_program(root, q, reference=False, runner=runner, compiler=compiler)
                        executed.append(q["id"])
                    except (PackError, OSError) as exc:
                        errors.append(f"{q['id']}: {exc}")
            signatures.append((q, text))
        return {"formatVersion": 1, "packId": manifest["id"], "contentSha256": content_sha, "runner": "ci-report" if execution_report is not None else runner, "passed": not errors, "errors": errors, "warnings": warnings, "referenceVerified": executed, "questionCount": len(questions)}
    except (PackError, TypeError, KeyError, ValueError) as exc:
        return {"formatVersion": 1, "passed": False, "errors": [str(exc)], "warnings": [], "referenceVerified": []}


def approve(root, reviewer, runner="none", compilers=None, execution_report=None):
    # A reviewer may attest a downloaded CI report without running code locally.
    # This is not a signed attestation: build() ALWAYS reruns execution itself.
    report = audit(root, runner, compilers, execution_report=execution_report)
    if not report["passed"]:
        raise PackError("Audit failed; review not recorded:\n" + "\n".join(report["errors"]))
    if not reviewer.strip():
        raise PackError("Reviewer identity required")
    record = {"formatVersion": 1, "approved": True, "reviewer": reviewer, "contentSha256": report["contentSha256"], "copyrightChecked": True, "contentChecked": True, "reviewedAt": datetime.now(timezone.utc).isoformat()}
    if execution_report is not None:
        record["ciReportSha256"] = digest(canonical(execution_report))
    atomic_json(Path(root) / "review.json", record)
    return record


def build(root, output, runner="none", compilers=None, against=()):
    if Path(output).resolve().is_relative_to(Path(root).resolve()):
        raise PackError("Build output must be outside the package source")
    manifest, _ = load_pack(root, approved=True)
    report = audit(root, runner, compilers, against)
    if not report["passed"]:
        raise PackError("Publication gate failed:\n" + "\n".join(report["errors"]))
    files = payload_files(root)
    manifest = {**manifest, "files": files}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{manifest['id']}-{manifest['version']}.zip"
    # Deterministic archive; timestamps/permission bits do not depend on build machine.
    with tempfile.NamedTemporaryFile(dir=output, suffix=".zip", delete=False) as stream:
        temp = Path(stream.name)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            payload = {name: inside(root, name).read_bytes() for name in files}
            payload["pack.json"] = canonical(manifest) + b"\n"
            payload["review.json"] = canonical(read_json(Path(root) / "review.json")) + b"\n"
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        sha = digest(temp.read_bytes())
        if target.exists() and digest(target.read_bytes()) != sha:
            raise PackError("Release already exists with different bytes; increment pack version")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    atomic_json(output / f"{manifest['id']}-{manifest['version']}.audit.json", report)
    (output / (target.name + ".sha256")).write_text(sha + "  " + target.name + "\n", encoding="utf-8")
    return {"id": manifest["id"], "title": manifest["title"], "version": manifest["version"], "minEngineVersion": manifest.get("minEngineVersion", "0.6.0"), "filename": target.name, "sha256": sha, "size": target.stat().st_size}
