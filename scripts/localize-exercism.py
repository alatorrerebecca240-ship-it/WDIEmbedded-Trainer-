"""Build the pinned 50-pack Chinese offline update; never execute exercise code.

This is a presentation-only derivative of already approved release archives, not
a general publication shortcut. Base archives, retained licenses, build settings,
tests, starter and reference files must match byte-for-byte. Translation review
is attributed to AI, never to the original human reviewer. Normal Docker release
gates are unchanged. Installing does not transfer code-execution trust.
"""
from pathlib import Path
import argparse
import copy
import difflib
import json
import re
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trainerlib.audit import _archive_reviewed, copyright_errors
from trainerlib.common import PackError, atomic_json, canonical, digest, inside, read_json
from trainerlib.format import fingerprint, load_pack, payload_files
from trainerlib.store import PackStore

CATALOG_SHA = 'b5c6625a22a1b5643b28e5473c931a16265559ccf8798fb3780754837b9e65c0'
VERSION = '1.0.1'
POLICY = 'exercism-50-zh-CN-presentation-only-v1'
REVIEWER = 'Codex AI 中文内容复核（非新增人工审核）'
NOTICE = '；中文更新 1.0.1：翻译并整理标题、题干、知识点和提示；保留英文原题及全部代码、测试、来源和许可证。中文内容由 Codex AI 复核，未重新执行参考答案。'
CHINESE = re.compile(r'[\u4e00-\u9fff]')


def ensure(condition, message):
    if not condition:
        raise PackError(message)


def parse_translation(document):
    """Parse deliberately small Markdown authoring format, not executable HTML."""
    text = document.replace('\r\n', '\n').strip() + '\n'
    ensure(not re.search(r'<\s*(script|iframe|object|img)\b|javascript:|data:text/html', text, re.I),
           'Active Markdown/HTML is not permitted')
    ensure(text.count('\n## 提示\n') == 1, 'Exactly one final hints section required')
    statement, tail = text.split('\n## 提示\n')
    paragraphs = statement.split('\n\n')
    ensure(len(paragraphs) >= 4 and paragraphs[0].startswith('# '), 'Missing title/summary/body')
    title, summary = paragraphs[0][2:].strip(), paragraphs[1].strip()
    topics = re.search(r'^知识点：(.+)$', statement, re.M)
    ensure(topics is not None, 'Missing knowledge topics')
    knowledge = topics.group(1).rstrip('。').split('、')
    hints = [line[2:].strip() for line in tail.splitlines() if line.startswith('- ')]
    ensure(all(not line.strip() or line.startswith('- ') for line in tail.splitlines()), 'Invalid hints syntax')
    ensure(len(hints) >= 2, 'At least two Chinese hints required')
    ensure(all(CHINESE.search(s) for s in [title, summary, *knowledge, *hints]), 'Untranslated display metadata')
    ensure(len(statement) >= 180, 'Statement is incomplete')
    ensure('未审核的导入草稿' not in statement and '中文题干精校' not in statement, 'Stale draft banner')
    return {'title': title, 'summary': summary, 'knowledge': knowledge, 'hints': hints}, statement.strip() + '\n'


def expected_payload(base, document, entry):
    """Whitelist exact transformations; all unspecified data remains identical."""
    manifest, _ = load_pack(base, integrity=True, approved=True)
    data = read_json(base / 'questions.json')
    ensure(len(data['questions']) == 1, 'Only pinned single-question packs supported')
    old = data['questions'][0]
    ensure(old['id'] == entry['id'].replace('review.', 'oss.', 1), 'Base question identity mismatch')
    fields, body = parse_translation(document)
    question = copy.deepcopy(old)
    question.update(fields)
    question['origin']['modifications'] += NOTICE
    translated = {**data, 'questions': [question]}
    statement_name = old['assetRoot'] + '/' + old['statement']
    english_name = old['assetRoot'] + '/README.en.md'
    original = inside(base, statement_name).read_text(encoding='utf-8')
    ensure('## 上游原题\n' in original, 'Expected pinned import layout')
    english = '# English source / 英文原题\n\n> 英文原文供离线对照；当前中文题目见 [README.md](README.md)。\n\n'
    english += original.split('## 上游原题\n', 1)[1].lstrip()
    source_path = next(s['path'].split('/.docs/')[0] for s in old['origin']['sourceFiles'] if '/.docs/' in s['path'])
    url = old['origin']['repository'] + '/tree/' + old['origin']['commit'] + '/' + source_path + '/'
    body += ('\n## 使用与来源\n\n在 VS Code 中点击“开始练习”，保留测试要求的接口，在自己的练习副本中完成实现；'
             '然后点击“运行评测”。题目、接口和测试输出中的英文标识符不能随意翻译。\n\n'
             '[英文原题（离线对照）](README.en.md) · [固定版本上游来源](' + url + ')\n\n'
             '本中文版本为基于 Exercism 原题的翻译与教学整理，非逐句直译；新撰中文采用项目 MIT 许可。'
             '上游原文、代码和各依赖的原许可证均随包保留。本次仅检查格式及与原版的代码一致性，'
             '未重新编译或执行第三方代码；不代表安全保证。\n')
    base_files = payload_files(base)
    unchanged = {k: v for k, v in base_files.items() if k not in {'questions.json', statement_name}}
    provenance = {
        'formatVersion': 1, 'policy': POLICY, 'locale': 'zh-CN',
        'baseArchiveSha256': entry['sha256'], 'baseArchiveUrl': entry['url'],
        'baseVersion': entry['version'], 'baseContentSha256': fingerprint(base),
        'baseReview': read_json(base / 'review.json'),
        'translationSha256': digest(document.encode('utf-8')),
        'translationReviewer': REVIEWER, 'newHumanReview': False,
        'execution': 'not-run', 'codeExecutionTrustTransferred': False,
        'unchangedPayloadFiles': unchanged,
        'scope': ['title', 'summary', 'knowledge', 'hints', 'statement', 'translation provenance'],
    }
    payload = {name: inside(base, name).read_bytes() for name in base_files}
    payload['questions.json'] = canonical(translated) + b'\n'
    payload[statement_name] = body.encode('utf-8')
    ensure(english_name not in payload and 'localization.json' not in payload, 'Base already localized')
    payload[english_name] = english.encode('utf-8')
    payload['localization.json'] = canonical(provenance) + b'\n'
    updated_manifest = {**manifest, 'title': fields['title'] + '（中文）', 'version': VERSION,
                        'files': {name: digest(content) for name, content in sorted(payload.items())}}
    return updated_manifest, payload


def verify_delta(base, target, document, entry):
    expected_manifest, expected_files = expected_payload(base, document, entry)
    actual, questions = load_pack(target, integrity=True)
    ensure(actual == expected_manifest, 'Unexpected manifest change')
    ensure(payload_files(target) == expected_manifest['files'], 'Non-presentation payload modification')
    for name, content in expected_files.items():
        ensure(inside(target, name).read_bytes() == content, 'Unexpected changed file: ' + name)
    for q in questions:
        ensure(not copyright_errors(q, target), 'Retained source/license validation failed')
    return {'formatVersion': 1, 'policy': POLICY, 'packId': actual['id'],
            'contentSha256': fingerprint(target), 'passed': True, 'runner': 'none',
            'referenceVerified': [], 'referenceReExecuted': False,
            'baseArchiveSha256': entry['sha256'], 'newHumanReview': False,
            'scope': 'presentation-only; exact byte comparison of all other payloads and build configuration',
            'warnings': ['AI translation review; original human review is retained under localization.json, not reassigned.',
                         'No fresh Docker execution evidence. Code execution trust is not inherited.']}


def build_one(entry, archive, document, output):
    ensure(entry['version'] == '1.0.0', 'Unexpected base version')
    raw = archive.read_bytes()
    ensure(digest(raw) == entry['sha256'] and len(raw) == entry['size'], 'Base archive SHA/size mismatch')
    with tempfile.TemporaryDirectory(prefix='trainer-zh-') as temp:
        base, target = Path(temp) / 'base', Path(temp) / 'translated'
        base.mkdir()
        target.mkdir()
        PackStore.extract(raw, base)
        manifest, payload = expected_payload(base, document, entry)
        for name, data in payload.items():
            file = inside(target, name)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        atomic_json(target / 'pack.json', manifest)
        report = verify_delta(base, target, document, entry)
        # A new, explicitly scoped AI localization record. Do NOT reuse Su's
        # identity or ciReportSha256 for a new content fingerprint.
        atomic_json(target / 'review.json', {
            'formatVersion': 1, 'approved': True, 'reviewer': REVIEWER,
            'reviewKind': POLICY, 'contentSha256': report['contentSha256'],
            'copyrightChecked': True, 'contentChecked': True,
            'reviewedAt': '2026-09-07', 'newHumanReview': False,
            'baseReviewLocation': 'localization.json', 'referenceReExecuted': False,
        })
        load_pack(target, integrity=True, approved=True)
        result = _archive_reviewed(target, output, manifest, report)
        result['questionId'] = entry['id'].replace('review.', 'oss.', 1)
        return result


def pinned_entries(catalog):
    ensure(digest(catalog.read_bytes()) == CATALOG_SHA, 'Base catalog is not the pinned published catalog')
    entries = [e for e in read_json(catalog)['packages'] if e['id'].startswith('review.exercism.')]
    ensure(len(entries) == 50 and len({e['id'] for e in entries}) == 50, 'Expected 50 unique base packs')
    return sorted(entries, key=lambda e: e['id'])


def bundle_path(output):
    output = Path(output)
    return output.parent / (output.name + '.zip')


def create_bundle(args):
    entries = pinned_entries(args.catalog)
    documents = {}
    for entry in entries:
        key = entry['id'].removeprefix('review.exercism.')
        documents[key] = (args.translations / (key + '.md')).read_text('utf-8')
        parse_translation(documents[key])
    ensure({p.stem for p in args.translations.glob('*.md')} == set(documents), 'Missing or unexpected translations')
    summaries = [(k, parse_translation(v)[0]['summary']) for k, v in documents.items()]
    for i, (key, text) in enumerate(summaries):
        for other, previous in summaries[:i]:
            ensure(difflib.SequenceMatcher(None, text, previous).ratio() < .93, f'Duplicate summary: {key}, {other}')
    output = args.output
    ensure(not output.exists(), 'Use a new output directory; existing releases are immutable')
    output.mkdir(parents=True)
    # Keep the original catalog as provenance, not as a download catalog for this offline update.
    (output / 'base-catalog.json').write_bytes(args.catalog.read_bytes())
    result = []
    for entry in entries:
        key = entry['id'].removeprefix('review.exercism.')
        archive = args.base / (entry['id'] + '-1.0.0.zip')
        result.append(build_one(entry, archive, documents[key], output / 'packages'))
        print('中文包完成：' + result[-1]['title'], flush=True)
    index = {'formatVersion': 1, 'kind': 'offline-bundle', 'locale': 'zh-CN',
             'version': VERSION, 'questionCount': 50, 'packages': result}
    atomic_json(output / 'offline-index.json', index)
    checksums = ''.join(e['sha256'] + '  packages/' + e['filename'] + '\n' for e in result)
    (output / 'SHA256SUMS.txt').write_text(checksums, 'utf-8')
    readme = ('# Exercism 50 道中文离线题库\n\n版本 1.0.1；26 道 C、24 道 C++。'
              '这是原 50 道题的中文更新，不是另外新增 50 道。题目 ID 不变。\n\n'
              '## 导入\n\n先解压本合集。VS Code 中打开 Embedded Trainer → 管理知识包 → 离线导入，'
              '选择 packages 中对应的知识包 ZIP，再使用旁边 .zip.sha256 中的 SHA-256 校验值。'
              '当前插件按单包导入，不要把外层合集 ZIP 当成一个知识包导入。导入不会自动授权代码执行。\n\n'
              '维护者可在本项目中运行 scripts/localize-exercism.py install，并明确指定 --bundle 与 --store，'
              '一次同步全部 50 个包；脚本先校验所有包并备份安装索引，不修改练习代码或进度。\n\n'
              '## 变更和限制\n\n标题、题干、知识点、提示已中文化；英文原文和原许可证随各包保留。'
              '函数名、测试输出和“十二天”题的英文文本常量保持原样。三环电阻及学生名单题附有原题/旧测试差异说明。'
              '旧练习副本不会被覆盖，已打开的旧题页面可重新打开或刷新课程。\n\n'
              '本次为 AI 翻译及静态一致性复核，不是新增人工审核或重新运行云端测试。'
              '代码、参考答案、测试、编译配置、来源文件及许可证与已审核的 1.0.0 版一致。'
              '原人工审核记录保存在每包 localization.json，不冒用原审核人。新版本哈希变化，需按插件提示确认执行信任；'
              '安装保留旧版与旧信任记录，可在管理知识包中回退。没有推送或发布到 GitHub。\n\n'
              '## 题目列表\n\n' + '\n'.join('- ' + e['title'] + ' — `' + e['questionId'] + '`' for e in result) + '\n')
    (output / '使用说明.md').write_text(readme, 'utf-8')
    # A directory ending in 1.0.1-offline has a pathlib suffix too. Append,
    # never replace, or the patch version and offline marker would disappear.
    bundle = bundle_path(output)
    ensure(not bundle.exists(), 'Outer ZIP already exists')
    with zipfile.ZipFile(bundle, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(output.rglob('*')):
            if file.is_file():
                info = zipfile.ZipInfo(file.relative_to(output).as_posix(), (2020, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, file.read_bytes())
    sha = digest(bundle.read_bytes())
    Path(str(bundle) + '.sha256').write_text(sha + '  ' + bundle.name + '\n', 'utf-8')
    print(json.dumps({'bundle': str(bundle), 'sha256': sha, 'size': bundle.stat().st_size}, ensure_ascii=False))


def install_bundle(bundle, store_root):
    """Preflight all 50 packs, use normal immutable installation, never trust()."""
    index = read_json(bundle / 'offline-index.json')
    ensure(index.get('kind') == 'offline-bundle' and index.get('version') == VERSION, 'Unexpected offline index')
    entries = index['packages']
    ensure(len(entries) == 50 and len({e['id'] for e in entries}) == 50, 'Expected 50 unique packages')
    store = PackStore(store_root)
    original = store.index()
    # No partial synchronization caused by corrupt archives, stale approvals or downgrades.
    with tempfile.TemporaryDirectory(prefix='trainer-zh-preflight-') as temp:
        for i, entry in enumerate(entries):
            raw = inside(bundle / 'packages', entry['filename']).read_bytes()
            ensure(digest(raw) == entry['sha256'] and len(raw) == entry['size'], 'Offline archive checksum mismatch')
            folder = Path(temp) / str(i)
            folder.mkdir()
            PackStore.extract(raw, folder)
            manifest, lessons = load_pack(folder, integrity=True, approved=True)
            ensure(manifest['id'] == entry['id'] and manifest['version'] == VERSION, 'Offline identity mismatch')
            ensure([q['id'] for q in lessons] == [entry['questionId']], 'Offline question identity mismatch')
            ensure(entry['id'] not in original['active'] or original['active'][entry['id']] in {'1.0.0', VERSION}, 'Unexpected installed version; refusing replacement')
    store.root.mkdir(parents=True, exist_ok=True)
    backup = store.root / 'backups' / 'before-exercism-zh-1.0.1.json'
    if not backup.exists():
        atomic_json(backup, original)
    result = []
    for entry in entries:
        result.append(store.install(inside(bundle / 'packages', entry['filename']), entry['sha256'],
                                    source='offline-zh-CN', expected=entry))
        print('已同步：' + entry['title'], flush=True)
    current = store.index()
    ensure(current.get('trusted', {}) == original.get('trusted', {}), 'Trust unexpectedly changed')
    for pack_id, versions in original['versions'].items():
        for release, record in versions.items():
            # A repeated import refreshes installedAt for the same new version only.
            if release != VERSION or pack_id not in {e['id'] for e in entries}:
                ensure(current['versions'][pack_id][release] == record, 'Old version unexpectedly changed')
    print(json.dumps({'installed': len(result), 'store': str(store.root), 'backup': str(backup),
                      'trustTransferred': False, 'oldVersionsPreserved': True}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build')
    build.add_argument('--base', type=Path, default=ROOT / 'dist/Embedded-Trainer-0.12.0-Windows-x64-offline/knowledge/extras')
    build.add_argument('--catalog', type=Path, default=ROOT / '.trainer/release-downloads/knowledge-v1.1.0/catalog.json')
    build.add_argument('--translations', type=Path, default=ROOT / 'knowledge/translations/exercism-zh-cn')
    build.add_argument('--output', type=Path, default=ROOT / 'dist/Embedded-Trainer-Exercism-50-zh-CN-1.0.1-offline')
    install = sub.add_parser('install')
    install.add_argument('--bundle', type=Path, required=True, help='Extracted offline bundle directory')
    install.add_argument('--store', type=Path, required=True, help='Explicit CLI or VS Code knowledge store')
    args = parser.parse_args()
    if args.command == 'build':
        create_bundle(args)
    else:
        install_bundle(args.bundle, args.store)


if __name__ == '__main__':
    main()
