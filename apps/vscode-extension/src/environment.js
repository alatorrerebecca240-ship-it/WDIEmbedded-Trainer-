// Environment discovery is independent of Python and question-bank loading.
// Install only pinned offline payloads after explicit confirmation in environment-ui.js.
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { execFile } = require('node:child_process');
const manifest = require('../resources/offline-runtime.json');

function execute(file, args, options = {}) {
  return new Promise((resolve) => execFile(file, args, { windowsHide: true, shell: false, timeout: 15000,
    maxBuffer: 1024 * 1024, encoding: 'utf8', ...options }, (error, stdout, stderr) =>
    resolve({ code: error ? (typeof error.code === 'number' ? error.code : -1) : 0, stdout: stdout || '', stderr: stderr || '', error })));
}
function defaults(env = process.env) {
  if (!env.LOCALAPPDATA || !path.win32.isAbsolute(env.LOCALAPPDATA)) throw Error('无法确定当前用户的 LocalAppData 目录。');
  return { python: path.join(env.LOCALAPPDATA, 'Programs', 'Python', manifest.python.directory),
    base: path.join(env.LOCALAPPDATA, 'Programs', 'EmbeddedTrainer'),
    compiler: path.join(env.LOCALAPPDATA, 'Programs', 'EmbeddedTrainer', manifest.compiler.directory),
    boost: path.join(env.LOCALAPPDATA, 'Programs', 'EmbeddedTrainer', manifest.boost.directory) };
}
function launchEnvironment(runtime = {}, original = process.env) {
  const env = { ...original };
  const pathKey = Object.keys(env).find(k => k.toLowerCase() === 'path') || 'PATH';
  const bins = [runtime.c, runtime.cpp].filter(p => p && path.isAbsolute(p)).map(p => path.dirname(p));
  if (bins.length) env[pathKey] = [...new Set(bins), env[pathKey] || ''].join(path.delimiter);
  if (runtime.c) env.TRAINER_CC = runtime.c;
  if (runtime.cpp) env.TRAINER_CXX = runtime.cpp;
  if (runtime.boost) env.CPLUS_INCLUDE_PATH = [runtime.boost, env.CPLUS_INCLUDE_PATH].filter(Boolean).join(path.delimiter);
  return env;
}
async function sha256(file) {
  const hash = crypto.createHash('sha256');
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}
async function verifyPayload(root, component) {
  const asset = manifest[component];
  if (!asset || !/^[\w.+-]+$/.test(asset.file)) throw Error('不支持的环境组件。');
  const folder = await fsp.realpath(root);
  const target = path.join(folder, asset.file);
  const stat = await fsp.lstat(target);
  if (!stat.isFile() || stat.isSymbolicLink() || path.dirname(await fsp.realpath(target)) !== folder)
    throw Error('环境安装包不允许符号链接或路径跳转。');
  if (await sha256(target) !== asset.sha256) throw Error(`${asset.file} 校验失败，未执行安装。请重新取得完整配套包。`);
  return target;
}
function requiredComponents(report) {
  return [...(!report.python ? ['python'] : []), ...(!report.c || !report.cpp ? ['compiler'] : []),
    ...(!report.boost ? ['boost'] : [])];
}
function resolveExecutable(candidate, env, platform) {
  if (!candidate) return undefined;
  if (path.isAbsolute(candidate)) return fs.existsSync(candidate) ? candidate : undefined;
  // Never search the workspace/current directory or launch Windows Store aliases.
  const value = Object.entries(env).find(([key]) => key.toLowerCase() === 'path')?.[1] || '';
  const suffixes = platform === 'win32' && !path.extname(candidate) ? ['.exe'] : [''];
  for (const directory of value.split(path.delimiter).filter(p => p && path.isAbsolute(p))) {
    for (const suffix of suffixes) {
      const full = path.join(directory, candidate + suffix);
      if (!/WindowsApps[\\/]python/i.test(full) && fs.existsSync(full)) return full;
    }
  }
  return undefined;
}

class RuntimeEnvironment {
  constructor(context, output, options = {}) {
    this.context = context;
    this.output = output;
    this.exec = options.execute || execute;
    this.verify = options.verifyPayload || verifyPayload;
    this.platform = options.platform || process.platform;
    this.arch = options.arch || process.arch;
    this.env = options.env || process.env;
    this.runtime = context.globalState.get('offlineRuntime', {});
    this.busy = false;
  }
  launch() { return { ...this.runtime }; }
  async detect(pythonSetting, root) {
    const targets = this.platform === 'win32' ? defaults(this.env) : {};
    const candidates = [pythonSetting, this.runtime.python, targets.python && path.join(targets.python, 'python.exe'), 'python', 'python3'];
    if (this.platform === 'win32') {
      for (const version of ['314','313','312','311','310','39'])
        candidates.push(path.join(this.env.LOCALAPPDATA, 'Programs', 'Python', 'Python' + version, 'python.exe'));
    }
    let python;
    const script = 'import sys,json; print(json.dumps({"path":sys.executable,"ok":sys.version_info >= (3,9),"version":sys.version.split()[0]}))';
    for (const candidate of [...new Set(candidates.map(p => resolveExecutable(p, this.env, this.platform)).filter(Boolean))]) {
      // Avoid triggering the Microsoft Store App Execution Alias.
      if (/WindowsApps[\\/]python/i.test(candidate)) continue;
      const r = await this.exec(candidate, ['-I', '-c', script], { cwd: os.tmpdir(), timeout: 5000 });
      try { const value = JSON.parse(r.stdout); if (!r.code && value.ok) { python = value.path; break; } } catch (_) { /* next candidate */ }
    }
    const launcher = resolveExecutable('py', this.env, this.platform);
    if (!python && this.platform === 'win32' && launcher) {
      const r = await this.exec(launcher, ['-3', '-I', '-c', script], { cwd: os.tmpdir(), timeout: 5000 });
      try { const value = JSON.parse(r.stdout); if (!r.code && value.ok) python = value.path; } catch (_) { /* unavailable */ }
    }
    let projectCompiler;
    try {
      const config = JSON.parse(await fsp.readFile(path.join(root, '.vscode', 'c_cpp_properties.json'), 'utf8'));
      projectCompiler = config.configurations?.find(x => typeof x.compilerPath === 'string')?.compilerPath;
    } catch (_) { /* optional legacy compiler configuration */ }
    const compilerPaths = [this.runtime.c, this.runtime.cpp, this.env.TRAINER_CC, this.env.TRAINER_CXX, projectCompiler];
    const bins = [...new Set(compilerPaths.filter(p => p && path.isAbsolute(p)).map(p => path.dirname(p)))];
    if (targets.compiler) bins.push(path.join(targets.compiler, 'bin'));
    const report = { python, c: undefined, cpp: undefined, boost: undefined };
    for (const [language, names] of [['c',['gcc','clang','cc']],['cpp',['g++','clang++','c++']]]) {
      const choices = [this.runtime[language], language === 'c' ? this.env.TRAINER_CC : this.env.TRAINER_CXX,
        ...bins.flatMap(bin => names.map(name => path.join(bin, name + (this.platform === 'win32' ? '.exe' : '')))), ...names];
      for (const candidate of [...new Set(choices.map(p => resolveExecutable(p, this.env, this.platform)).filter(Boolean))]) {
        const r = await this.exec(candidate, ['--version'], { cwd: os.tmpdir(), timeout: 5000 });
        if (!r.code && /clang|gcc|g\+\+|Free Software Foundation/i.test(r.stdout + r.stderr)) {
          if (await this.smoke(candidate, language, this.runtime.boost)) { report[language] = candidate; break; }
        }
      }
    }
    for (const candidate of [this.runtime.boost, targets.boost].filter(Boolean)) {
      if (fs.existsSync(path.join(candidate, 'boost', 'date_time', 'posix_time', 'posix_time.hpp'))) { report.boost = candidate; break; }
    }
    // Remember working executables locally, not in Settings Sync or the workspace.
    this.runtime = { ...report, pythonSetting };
    await this.context.globalState.update('offlineRuntime', this.runtime);
    for (const [name, value] of Object.entries(report)) this.output.appendLine(`[${value ? 'OK' : name === 'boost' ? 'OPTIONAL' : 'MISSING'}] ${name}: ${value || '未找到可用环境'}`);
    return report;
  }
  async smoke(compiler, language, boost) {
    const dir = await fsp.mkdtemp(path.join(os.tmpdir(), 'embedded-trainer-check-'));
    try {
      const source = path.join(dir, language === 'c' ? 'check.c' : 'check.cpp');
      const binary = path.join(dir, this.platform === 'win32' ? 'check.exe' : 'check');
      await fsp.writeFile(source, language === 'c' ? '#include <stdio.h>\nint main(void){int a[2]={2,3};return a[0]+a[1]==5?0:1;}\n'
        : '#include <string>\n#include <vector>\nint main(){std::vector<int> a{2,3};std::string s="ok";return a[0]+a[1]==5 && s.size()==2?0:1;}\n');
      const env = launchEnvironment({ c: compiler, cpp: compiler, boost }, this.env);
      const build = await this.exec(compiler, [language === 'c' ? '-std=c11' : '-std=c++17', source, '-o', binary], { cwd: dir, env, timeout: 60000 });
      if (build.code) { this.output.appendLine(`编译器自检未通过：${compiler}\n${build.stderr}`); return false; }
      return (await this.exec(binary, [], { cwd: dir, env, timeout: 10000 })).code === 0;
    } finally {
      // Only the unique directory returned by mkdtemp above is removed.
      await fsp.rm(dir, { recursive: true, force: true }).catch(() => {});
    }
  }
  async install(folder, report, progress = () => {}) {
    if (this.platform !== 'win32' || this.arch !== 'x64' || /arm/i.test(`${this.env.PROCESSOR_ARCHITECTURE || ''} ${this.env.PROCESSOR_ARCHITEW6432 || ''}`))
      throw Error('配套自动安装仅支持 Windows 10/11 x64。其他系统请手动配置环境。');
    const components = requiredComponents(report);
    if (!components.length) return report;
    // Verify every requested component BEFORE installing any of them.
    for (const name of components) { progress(`校验 ${manifest[name].file}`); await this.verify(folder, name); }
    const powershell = path.join(this.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
    // Ignore third-party / PowerShell 7 module paths inherited by VS Code.
    const installEnv = { ...this.env, PSModulePath: path.join(path.dirname(powershell), 'Modules') };
    const scriptPath = path.join(this.context.extensionUri.fsPath, 'scripts', 'install-offline-runtime.ps1');
    progress('安装环境，请勿关闭 VS Code。完整日志保存在 Embedded Trainer 默认安装目录。');
    const result = await this.exec(powershell, ['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',scriptPath,
      '-BundleDirectory', folder, '-Components', components.join(',')], { timeout: 20 * 60 * 1000, env: installEnv });
    this.output.appendLine(result.stdout + result.stderr);
    if (result.code) throw Error('离线环境安装未完成，已有环境与题目未删除。请查看 Embedded Trainer 输出及安装日志后重试。');
    const targets = defaults(this.env);
    const next = { ...report };
    if (components.includes('python')) next.python = path.join(targets.python, 'python.exe');
    if (components.includes('compiler')) {
      // Keep each existing working compiler, repairing only missing ones.
      next.c ||= path.join(targets.compiler, 'bin', 'clang.exe');
      next.cpp ||= path.join(targets.compiler, 'bin', 'clang++.exe');
    }
    if (components.includes('boost')) next.boost = targets.boost;
    this.runtime = next;
    // Candidates stay in memory until detect() confirms they actually compile/run.
    return next;
  }
}
module.exports = { RuntimeEnvironment, execute, defaults, launchEnvironment, sha256, verifyPayload, requiredComponents, resolveExecutable, manifest };
