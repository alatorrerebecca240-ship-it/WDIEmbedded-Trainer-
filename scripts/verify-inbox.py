"""GitHub Actions entrypoint. No native execution option exists."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trainerlib.common import PackError
from trainerlib.inbox_ci import verify_plan

if __name__ == "__main__":
    try:
        raw = os.environ["TRAINER_INBOX_PLAN"]
        if len(raw.encode("utf-8")) > 40000:
            raise PackError("Plan exceeds size limit")
        result = verify_plan(json.loads(raw), ROOT / "inbox-results.json", ROOT / "LICENSE")
        print(json.dumps(result))
    except (PackError, ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
