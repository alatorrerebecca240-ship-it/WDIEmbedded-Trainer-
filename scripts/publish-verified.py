"""Publish reviewed snapshots using authenticated existing Actions evidence; no compiler."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trainerlib.audit import build_from_report
from trainerlib.cli import make_catalog
from trainerlib.common import PackError, canonical, digest, read_json
from trainerlib.format import fingerprint, load_pack
from trainerlib.store import PackStore


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, timeout=120)
    if result.returncode:
        raise PackError("GitHub read failed: " + " ".join(args[:3]))
    return result.stdout


def authenticated_reports(repo, evidence):
    reports = {}
    for expected in evidence["runs"]:
        run_id = expected["id"]
        run = json.loads(gh("api", f"repos/{repo}/actions/runs/{run_id}"))
        if (run["head_sha"] != expected["headSha"]
            or run["path"] != ".github/workflows/acquire-review.yml"
            or run["event"] != "workflow_dispatch"
            or run["head_repository"]["full_name"].lower() != repo.lower()
            or run["display_title"] != "trainer-review-" + expected["requestId"]
            or run["status"] != "completed" or run["conclusion"] != "success"):
            raise PackError(f"Evidence run identity/status mismatch: {run_id}")
        artifacts = json.loads(gh("api", f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100"))["artifacts"]
        selected = [a for a in artifacts if a["name"] == "trainer-review-" + expected["requestId"] and not a["expired"]]
        if len(selected) != 1 or selected[0]["size_in_bytes"] > 12 * 1024 * 1024:
            raise PackError("Evidence artifact missing, ambiguous or too large")
        artifact = selected[0]
        raw = gh("api", f"repos/{repo}/actions/artifacts/{artifact['id']}/zip")
        if artifact.get("digest") != "sha256:" + digest(raw):
            raise PackError("Evidence artifact checksum mismatch")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo("inbox-results.json")
            if info.file_size > 12 * 1024 * 1024:
                raise PackError("Evidence report exceeds size limit")
            obj = json.loads(archive.read(info))
        if obj.get("pipelineVersion") != 1 or obj.get("requestId") != expected["requestId"]:
            raise PackError("Evidence request mismatch")
        for result in obj["results"]:
            report = result.get("audit", {})
            if report.get("passed") is True and report.get("runner") == "docker":
                reports[digest(canonical(report))] = (report, {
                    "repository": repo, "runId": run_id, "headSha": run["head_sha"],
                    "artifactId": artifact["id"], "artifactSha256": digest(raw),
                    "url": run["html_url"]})
    return reports


def prepare(source, output, repo, tag, evidence):
    if evidence["tag"] != tag:
        raise PackError("Evidence manifest belongs to a different release")
    sources = sorted(Path(source).glob("*/pack.json"))
    sources = [p.parent for p in sources]
    all_questions = []
    ids = set()
    for root in sources:
        manifest, questions = load_pack(root, approved=True)
        if manifest["id"] in ids:
            raise PackError("Duplicate package ID")
        ids.add(manifest["id"])
        all_questions.extend(questions)
    if len({q["id"] for q in all_questions}) != len(all_questions):
        raise PackError("Duplicate question ID")
    reports = authenticated_reports(repo, evidence)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    imported = 0
    with tempfile.TemporaryDirectory(prefix="trainer-existing-release-") as temp:
        base = Path(temp)
        gh("release", "download", evidence["baseRelease"], "--repo", repo,
           "--pattern", "catalog.json", "--dir", str(base))
        old_catalog = read_json(base / "catalog.json")
        PackStore.validate_catalog(old_catalog)
        for root in sources:
            manifest, questions = load_pack(root, approved=True)
            if manifest["id"] == "foundation.core":
                matches = [v for v in old_catalog["packages"] if v["id"] == manifest["id"] and v["version"] == manifest["version"]]
                if len(matches) != 1:
                    raise PackError("Unchanged foundation missing from previous release")
                item = matches[0]
                filename = f"{manifest['id']}-{manifest['version']}.zip"
                gh("release", "download", evidence["baseRelease"], "--repo", repo,
                   "--pattern", filename, "--pattern", filename + ".sha256",
                   "--pattern", filename[:-4] + ".audit.json", "--dir", str(output))
                store = PackStore(base / "store")
                store.install(output / filename, item["sha256"], expected=item)
                installed = store.root / "versions" / manifest["id"] / manifest["version"]
                if fingerprint(installed) != fingerprint(root):
                    raise PackError("Foundation differs from previously published content")
                entries.append({**item, "filename": filename})
            else:
                sha = read_json(root / "review.json").get("ciReportSha256")
                if sha not in reports:
                    raise PackError("No authenticated passing evidence for " + manifest["id"])
                report, provenance = reports[sha]
                entry = build_from_report(root, output, report, provenance,
                                          against=[s for s in sources if s != root])
                entries.append(entry)
                imported += len(questions)
                print("Packaged existing verified content:", manifest["id"], flush=True)
    if imported != evidence["expectedImportedQuestions"]:
        raise PackError("Unexpected imported question count")
    make_catalog(entries, repo, tag, output / "catalog.json")
    print(json.dumps({"packages": len(entries), "questions": len(all_questions),
                      "importedQuestions": imported, "execution": "not-run; reused authenticated cloud reports"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    prepare(args.source, args.output, os.environ["GITHUB_REPOSITORY"], args.tag, read_json(args.evidence))
