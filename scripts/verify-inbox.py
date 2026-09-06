"""GitHub Actions entrypoint. No native execution option exists."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trainerlib.common import PackError
from trainerlib.inbox_ci import verify_plan, source_cache_key

if __name__ == "__main__":
    try:
        raw = os.environ["TRAINER_INBOX_PLAN"]
        if len(raw.encode("utf-8")) > 40000:
            raise PackError("Plan exceeds size limit")
        plan = json.loads(raw)
        if sys.argv[1:] == ["--cache-key"]:
            print("cache-key=" + source_cache_key(plan))
            sys.exit(0)
        if sys.argv[1:]:
            raise PackError("Unsupported arguments")
        result = verify_plan(plan, ROOT / "inbox-results.json", ROOT / "LICENSE", cache=ROOT / ".imports/ci-blobs")
        report = json.loads((ROOT / "inbox-results.json").read_text(encoding="utf-8"))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write("\n## Question verification timings\n\n| Question | Result | Rebuild (s) | Audit (s) | Total (s) |\n|---|---|---:|---:|---:|\n")
                for item in report["results"]:
                    timing = item["timings"]
                    verdict = "passed" if item.get("audit", {}).get("passed") is True else "failed"
                    summary.write(f"| {item['id']} | {verdict} | {timing.get('rebuildSeconds', 0)} | {timing.get('auditSeconds', 0)} | {timing['totalSeconds']} |\n")
                summary.write(f"\nVerification wall time: {report['timings']['verificationSeconds']} s. Queue, image and cache preparation are separate Actions steps.\n")
        print(json.dumps(result))
    except (PackError, ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
