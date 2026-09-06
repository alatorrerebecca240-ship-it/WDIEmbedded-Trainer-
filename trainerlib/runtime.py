"""One discovery implementation shared by CLI and VS Code through the catalog command."""

import os
from pathlib import Path

from .common import PackError, inside, read_json
from .format import load_pack_snapshot
from .store import PackStore


def store_for(root):
    return PackStore(os.environ.get("TRAINER_PACK_HOME", str(Path(root) / ".trainer" / "knowledge")))


def configured_lessons(root):
    root = Path(root)
    config_file = root / "trainer-packs.json"
    config = read_json(config_file) if config_file.exists() else {"sources": [], "legacyContent": True}
    by_pack = {}
    for source in config.get("sources", []):
        directory = inside(root, source)
        manifest, lessons, sha = load_pack_snapshot(directory)
        if manifest["id"] in by_pack:
            raise PackError("Duplicate configured source package")
        by_pack[manifest["id"]] = [{**q, "_packId": manifest["id"], "_packVersion": manifest["version"], "_packSha256": sha, "_needsTrust": False} for q in lessons]
    # Explicit installed versions take precedence over the same editable source package.
    by_pack.update(store_for(root).lessons())
    return config.get("legacyContent", True), [q for lessons in by_pack.values() for q in lessons]
