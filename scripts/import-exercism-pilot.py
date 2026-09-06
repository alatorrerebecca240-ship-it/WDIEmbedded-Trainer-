"""Reproduce the curated selection as data-only drafts; never execute upstream code."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trainerlib.common import PackError, canonical
from trainerlib.exercism import import_batch, scan


def main():
    index = ROOT / ".imports/exercism-index.json"
    cache = ROOT / ".imports/exercism-cache"
    scan(index, cache, refs={
        "c": "2e8a0022fd2a611adc08b4d6e70d07b988cc5364",
        "cpp": "413b80a9b94089e4588c50500b8553a59c48cda8",
    })
    result = import_batch(index, ROOT / "knowledge/drafts/exercism.pilot", cache,
                          recommended=True, project_license=ROOT / "LICENSE")
    print(canonical(result).decode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except (PackError, OSError, ValueError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        sys.exit(1)
