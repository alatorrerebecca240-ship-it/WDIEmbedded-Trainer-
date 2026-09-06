"""Render exact-snapshot review evidence locally or in Actions; never approve."""

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trainerlib.common import PackError, read_json
from trainerlib.review import render_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.is_relative_to(Path(args.pack).resolve()):
        raise PackError("Review sheet must be outside the package to preserve its fingerprint")
    report = read_json(args.report)
    text = render_review(args.pack, report, os.environ.get("GITHUB_REPOSITORY"),
                         os.environ.get("GITHUB_SHA"), Path.cwd())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(text.split("## 逐题核对", 1)[0])
            stream.write("\n完整题干、答案、参考实现和测试见本次 draft-audit artifact 中的 draft-review.md。\n")
    print(f"Review sheet written: {output}")


if __name__ == "__main__":
    main()
