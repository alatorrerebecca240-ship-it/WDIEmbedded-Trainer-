"""Build an allowlisted offline distribution from verified upstream archives.

No downloads, environment installation, question execution, or publishing.
Run after building the VSIX and rendering/reviewing the manual.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'apps/vscode-extension'


def digest(file):
    value = hashlib.sha256()
    with file.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(data)
    return value.hexdigest()


def checked(file, expected):
    if not file.is_file() or file.is_symlink() or digest(file) != expected:
        raise ValueError(f'Missing, linked or mismatched payload: {file.name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT / '.trainer/offline-assets')
    parser.add_argument('--packs', type=Path, default=ROOT / '.trainer/release-downloads/knowledge-v1.1.0')
    args = parser.parse_args()
    manifest = json.loads((APP / 'resources/offline-runtime.json').read_text('utf-8'))
    sources = json.loads((ROOT / 'scripts/offline-source-pins.json').read_text('utf-8'))
    if sources['compilerRelease'] != manifest['compiler']['version']:
        raise ValueError('Source bundle does not match compiler release')
    version = json.loads((APP / 'package.json').read_text('utf-8'))['version']
    vsix = APP / f'embedded-trainer-{version}.vsix'
    manual = ROOT / 'docs/Embedded-Trainer新生训练营图文使用说明书.docx'
    catalog = json.loads((args.packs / 'catalog.json').read_text('utf-8'))
    if len(catalog['packages']) != 51 or catalog['releaseTag'] != 'knowledge-v1.1.0':
        raise ValueError('Expected the reviewed 51-pack release catalog')
    for component in ('python', 'compiler', 'boost'):
        checked(args.assets / manifest[component]['file'], manifest[component]['sha256'])
    for source in sources['archives']:
        if not re.fullmatch(r'[\w.-]+', source['file']):
            raise ValueError('Unsafe source filename')
        checked(args.assets / source['file'], source['sha256'])
        if source['file'].endswith('.zip'):
            with zipfile.ZipFile(args.assets / source['file']) as archive:
                if archive.testzip():
                    raise ValueError('Corrupt source archive')
    with zipfile.ZipFile(vsix) as archive:
        if json.loads(archive.read('extension/package.json'))['version'] != version:
            raise ValueError('VSIX version does not match source')
        if json.loads(archive.read('extension/resources/offline-runtime.json')) != manifest:
            raise ValueError('VSIX contains stale environment pins')
        if archive.read('extension/scripts/install-offline-runtime.ps1') != (APP / 'scripts/install-offline-runtime.ps1').read_bytes():
            raise ValueError('VSIX installer differs from source')
        required = ['extension/src/environment.js', 'extension/src/environment-ui.js', 'extension/runtime/trainer.py']
        for name in required:
            archive.getinfo(name)
        if any('/node_modules/' in n or '/.trainer/' in n or '/exercises/' in n for n in archive.namelist()):
            raise ValueError('Unexpected private or development content in VSIX')
        if archive.testzip():
            raise ValueError('Corrupt VSIX')
    with zipfile.ZipFile(manual) as archive:
        archive.getinfo('word/document.xml')
    # A fixed script receives the installer path as an argument, never as shell text.
    powershell = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    verify_env = dict(os.environ, PSModulePath=str(powershell.parent / 'Modules'))
    subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-File',
                    str(ROOT / 'scripts/verify-python-publisher.ps1'),
                    '-Installer', str((args.assets / manifest['python']['file']).resolve())], check=True, env=verify_env)
    files = []
    question_count = 0
    for pack in catalog['packages']:
        if not re.fullmatch(r'[\w.-]+', pack['id']) or not re.fullmatch(r'\d+\.\d+\.\d+', pack['version']):
            raise ValueError('Unsafe pack filename')
        name = f"{pack['id']}-{pack['version']}.zip"
        source = (args.assets if pack['id'] == 'foundation.core' else args.packs) / name
        checked(source, pack['sha256'])
        if source.stat().st_size != pack['size']:
            raise ValueError(f'Incorrect pack size: {name}')
        with zipfile.ZipFile(source) as archive:
            question_count += len(json.loads(archive.read('questions.json'))['questions'])
            if not any(n.startswith('licenses/') for n in archive.namelist()):
                raise ValueError(f'Missing license records: {name}')
            if archive.testzip():
                raise ValueError(f'Corrupt pack: {name}')
        relative = Path('knowledge') / ('' if pack['id'] == 'foundation.core' else 'extras') / name
        files.append((source, relative, pack['sha256']))
    if question_count != 248:
        raise ValueError(f'Expected 248 questions, found {question_count}')
    python_license = args.assets / 'Python-LICENSE.txt'
    if 'PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2' not in python_license.read_text('utf-8'):
        raise ValueError('Missing Python license text')
    name = f'Embedded-Trainer-{version}-Windows-x64-offline'
    output = ROOT / 'dist' / name
    archive_path = output.parent / (name + '.zip')
    output.parent.mkdir(exist_ok=True)
    if output.exists() or archive_path.exists():
        raise ValueError(f'Output already exists; preserve or rename it before rebuilding: {output}')
    output.mkdir()
    def copy(source, relative):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target
    def write(relative, text):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8-sig' if str(relative).endswith('.txt') else 'utf-8')
    copy(vsix, Path('plugin') / vsix.name)
    copy(manual, Path('docs') / manual.name)
    copy(APP / 'docs/usage.md', 'docs/plugin-usage.md')
    copy(ROOT / 'docs/offline-bundle-notices.md', 'licenses/THIRD_PARTY_NOTICES.md')
    copy(ROOT / 'LICENSE', 'licenses/Embedded-Trainer-MIT.txt')
    copy(python_license, 'licenses/Python-LICENSE.txt')
    copy(ROOT / 'scripts/offline-source-pins.json', 'sources/source-manifest.json')
    for source in sources['archives']:
        copy(args.assets / source['file'], Path('sources') / source['file'])
    write('sources/README.txt', '''附带工具源码与构建说明

本目录仅用于保留编译器附带工具的对应源码，不需要新生安装或执行。
source-manifest.json 列出官方来源、固定版本或提交和本地归档 SHA-256。

LLVM-MinGW 20260826 源码包包含构建脚本、包装器源码和发布工作流。
build-busybox.sh 固定 BusyBox-w32 提交 1f493261d16be3d984fe8a689f5113dafb6eaaa7。
build-make.sh 固定 GNU Make 4.4.1，包含交叉编译配置。
build-mingw-w64.sh 固定 MinGW-w64 提交 a3d708261d5ba659205067cb82cae36e7ae8bbb0；
build-mingw-w64-tools.sh 构建其中的 gendef 与 widl。
BusyBox 包中含其源文件和配置；对应变更与构建参数见上述配方。
各源代码包内保留原始许可证，不应把它们改称 Embedded Trainer 的 MIT 源码。
重新分发完整离线包时，请保留本目录及 licenses，不要只留下编译器二进制。
''')
    for component in ('python', 'compiler', 'boost'):
        copy(args.assets / manifest[component]['file'], Path('environment') / manifest[component]['file'])
    # The entire original archives retain all upstream notices; additionally expose common license files.
    with zipfile.ZipFile(args.assets / manifest['boost']['file']) as archive:
        (output / 'licenses/Boost-LICENSE_1_0.txt').write_bytes(archive.read(manifest['boost']['directory'] + '/LICENSE_1_0.txt'))
    with zipfile.ZipFile(args.assets / manifest['compiler']['file']) as archive:
        notices = [n for n in archive.namelist() if not n.endswith('/') and
                   re.search(r'(^|/)(LICENSE[^/]*|COPYING[^/]*|NOTICE[^/]*)$', n, re.I)]
        if not notices:
            raise ValueError('Compiler archive has no license records')
        for index, entry in enumerate(notices):
            target = output / 'licenses/compiler' / f'{index:03}-{Path(entry).name}'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(entry))
        write('licenses/compiler/INDEX.txt', '\n'.join(f'{i:03}-{Path(n).name}: {n}' for i, n in enumerate(notices)))
    for source, relative, checksum in files:
        copy(source, relative)
        write(str(relative) + '.sha256', checksum + '  ' + source.name + '\n')
    copy(args.packs / 'catalog.json', 'knowledge/catalog.json')
    write('START-HERE.txt', f'''Embedded Trainer {version} 新生训练营离线包

适用 Windows 10/11 x64。请完整解压本 ZIP，预留至少 6 GB 安装空间。
VS Code 本体需预先安装，本包没有包含 VS Code。

1. 打开 VS Code，按 Ctrl+Shift+X，在扩展视图“…”选择“从 VSIX 安装”。
   选择 plugin\\{vsix.name}，按提示重新加载窗口。
2. 新建自己的 TrainerPractice 文件夹，在 VS Code 中用“文件 → 打开文件夹”打开。
3. 按 Ctrl+Shift+P，运行 Embedded Trainer: 检查训练环境。
   缺失时点“从离线包自动安装”，选择本文件所在目录或 environment 文件夹。
   核对安装位置后确认，等待安装和自动复检。已有可用环境会保留。
4. 打开“管理知识包 → 离线导入 ZIP”，选择 knowledge\\foundation.core-1.0.0.zip。
   从同名 .zip.sha256 文件复制前 64 位校验值，不含文件名。
5. 进入“新生训练营 · 路线图”，开始基础训练。编程题需另行核对来源并确认代码信任。

knowledge 根目录含 198 道基础题；extras 含 50 道拓展题的独立 ZIP，可按需导入。
只安装基础包即可完成路线的 49 道必做题。Boost 主要供部分 C++ 拓展题使用。
详细图示见 docs 中的 Word 说明书第 2 至 4 页。

Python 默认安装到 %LOCALAPPDATA%\\Programs\\Python\\Python313。
编译器与 Boost 安装到 %LOCALAPPDATA%\\Programs\\EmbeddedTrainer 下的版本目录。
不改系统 PATH，不覆盖已检测可用的环境，不需要管理员权限；这是电脑端训练工具链。
安装失败请保留日志并联系带教，不要自行删除已有开发环境。

本包不包含私人答案、进度、账号凭据或预先授予的题库代码信任。
软件与题库许可证分别见 licenses 和各知识包内的许可证，不能全部视为 MIT。
SHA256SUMS.txt 提供文件校验指纹，请从可信带教或发布者获取本包。
''')
    inventory = {
        'formatVersion': 1, 'name': name, 'pluginVersion': version, 'platform': 'Windows 10/11 x64',
        'knowledgeRelease': catalog['releaseTag'], 'packCount': len(files), 'questionCount': question_count,
        'runtimePins': manifest, 'sourceArchives': sources, 'containsPrivateProgress': False,
        'files': [{'path': p.relative_to(output).as_posix(), 'size': p.stat().st_size, 'sha256': digest(p)}
                  for p in sorted(output.rglob('*')) if p.is_file()]
    }
    write('bundle-manifest.json', json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    write('SHA256SUMS.txt', '\n'.join(f'{digest(p)}  {p.relative_to(output).as_posix()}' for p in sorted(output.rglob('*')) if p.is_file()) + '\n')
    with zipfile.ZipFile(archive_path, 'x', allowZip64=True) as archive:
        for file in sorted(output.rglob('*')):
            if file.is_file():
                compressed = zipfile.ZIP_STORED if file.suffix in ('.zip', '.gz', '.exe', '.vsix', '.docx') else zipfile.ZIP_DEFLATED
                archive.write(file, (Path(name) / file.relative_to(output)).as_posix(), compress_type=compressed)
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip():
            raise ValueError('Distribution archive CRC verification failed')
        expected = {f'{name}/{p.relative_to(output).as_posix()}' for p in output.rglob('*') if p.is_file()}
        if set(archive.namelist()) != expected:
            raise ValueError('Archive inventory mismatch')
    archive_path.with_suffix('.zip.sha256').write_text(digest(archive_path) + '  ' + archive_path.name + '\n', encoding='ascii')
    print(json.dumps({'path':str(archive_path), 'bytes':archive_path.stat().st_size, 'packs':len(files), 'questions':question_count, 'sha256':digest(archive_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
