"""Validate workflow input before any draft is passed to the auditing engine."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trainerlib.common import PackError, inside

path = os.environ["DRAFT_PATH"]
if not path.startswith("knowledge/"):
    raise PackError("Draft must be below knowledge/")
resolved = inside(Path.cwd(), path)
if not (resolved / "pack.json").is_file():
    raise PackError("Selected draft does not contain pack.json")
