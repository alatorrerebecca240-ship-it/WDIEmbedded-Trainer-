"""CI-only isolated verification: each question succeeds/fails independently."""
import tempfile
from pathlib import Path

from .audit import audit
from .common import PackError, atomic_json, canonical, digest, inside
from .format import fingerprint, load_pack
from .exercism import import_batch, scan
from .inbox import PIPELINE_VERSION, normalized_pack, validate_plan


def verify_plan(plan, output, project_license):
    validate_plan(plan)
    results, indexes = [], {}
    with tempfile.TemporaryDirectory(prefix="trainer-inbox-ci-") as name:
        root = Path(name)
        for number, entry in enumerate(plan["entries"]):
            try:
                if entry.get("mode") == "repository":
                    pack = inside(Path(project_license).resolve().parent, entry["path"])
                    _, questions = load_pack(pack)
                    if len(questions) != 1 or questions[0]["id"] != entry["id"] or fingerprint(pack) != entry["contentSha256"]:
                        raise PackError("请先把此修改后的草稿提交并推送到 main，云端文件与本地指纹必须一致。")
                    results.append({"id": entry["id"], "audit": audit(pack, runner="docker")})
                    continue
                lang = entry["key"].split("/")[0]
                group = (lang, entry["commit"])
                if group not in indexes:
                    index = root / f"{lang}-{entry['commit']}.json"
                    try:
                        scan(index, root / "cache", language=lang, refs={lang: entry["commit"]})
                        indexes[group] = index
                    except (PackError, OSError, ValueError) as exc:
                        indexes[group] = str(exc)
                if isinstance(indexes[group], str):
                    raise PackError(indexes[group])
                source = root / f"source-{number}"
                import_batch(indexes[group], source, root / "cache", keys=[entry["key"]], project_license=project_license)
                pack = root / f"normalized-{number}"
                sha = normalized_pack(source, pack, entry["id"])
                if sha != entry["contentSha256"]:
                    raise PackError("云端重建指纹与本地不同；不能验证本地编辑过或不同工具版本生成的草稿。")
                report = audit(pack, runner="docker")
                results.append({"id": entry["id"], "audit": report})
            except (PackError, OSError, ValueError, KeyError, TypeError) as exc:
                results.append({"id": entry["id"], "errors": [str(exc)]})
            finally:
                # Partial progress is retained even if the workflow is later cancelled.
                atomic_json(output, {"pipelineVersion": PIPELINE_VERSION, "requestId": plan["requestId"],
                    "planSha256": digest(canonical(plan)), "results": results})
    return {"verified": sum(v.get("audit", {}).get("passed") is True for v in results), "total": len(results)}
