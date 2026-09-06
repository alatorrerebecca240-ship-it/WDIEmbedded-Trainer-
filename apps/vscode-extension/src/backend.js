const vscode = require('vscode');
const path = require('path');
const { spawn } = require('child_process');

function toCrlf(text) {
  return text.replace(/\r?\n/g, '\r\n');
}

class TrainerBackend {
  constructor(rootUri, output, diagnostics, options = {}) {
    this.rootUri = rootUri;
    this.output = output;
    this.diagnostics = diagnostics;
    this.enginePath = options.enginePath || path.join(rootUri.fsPath, 'trainer.py');
    this.packHome = options.packHome;
  }

  get pythonPath() {
    return vscode.workspace.getConfiguration('embeddedTrainer').get('pythonPath', 'python');
  }

  async run(args, options = {}) {
    const startedAt = Date.now();
    const commandArgs = [this.enginePath, ...args];
    if (!options.silent) this.output.appendLine(`\n> trainer ${args.join(' ')}`);

    return new Promise((resolve) => {
      let stdout = '';
      let stderr = '';
      let settled = false;
      const child = spawn(this.pythonPath, commandArgs, {
        cwd: this.rootUri.fsPath,
        windowsHide: true,
        shell: false,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8', TRAINER_PROJECT_ROOT: this.rootUri.fsPath,
          ...(this.packHome ? { TRAINER_PACK_HOME: this.packHome } : {}) }
      });

      const cancellation = options.token && options.token.onCancellationRequested(() => {
        if (!settled) {
          child.kill();
        }
      });

      child.stdout.setEncoding('utf8');
      child.stderr.setEncoding('utf8');
      child.stdout.on('data', (chunk) => {
        const text = chunk.toString('utf8');
        stdout += text;
        if (!options.silent) this.output.append(text);
      });
      child.stderr.on('data', (chunk) => {
        const text = chunk.toString('utf8');
        stderr += text;
        if (!options.silent) this.output.append(text);
      });
      child.on('error', (error) => {
        settled = true;
        cancellation && cancellation.dispose();
        const message = `无法启动训练核心：${error.message}`;
        this.output.appendLine(message);
        resolve({ code: -1, stdout, stderr: `${stderr}${message}`, output: `${stdout}${stderr}${message}`, duration: Date.now() - startedAt });
      });
      child.on('close', (code) => {
        if (settled) {
          return;
        }
        settled = true;
        cancellation && cancellation.dispose();
        const output = `${stdout}${stderr}`;
        if (options.collectDiagnostics) {
          this.updateDiagnostics(output);
        }
        resolve({ code: code ?? -1, stdout, stderr, output, duration: Date.now() - startedAt });
      });
    });
  }

  updateDiagnostics(output) {
    this.diagnostics.clear();
    const byFile = new Map();
    const pattern = /^(.+?):(\d+):(\d+):\s+(warning|error|fatal error|note):\s+(.+)$/;
    for (const line of output.split(/\r?\n/)) {
      const match = line.match(pattern);
      if (!match) {
        continue;
      }
      const [, fileName, lineText, columnText, kind, message] = match;
      const lineNumber = Math.max(0, Number(lineText) - 1);
      const column = Math.max(0, Number(columnText) - 1);
      const severity = kind.includes('error')
        ? vscode.DiagnosticSeverity.Error
        : kind === 'warning'
          ? vscode.DiagnosticSeverity.Warning
          : vscode.DiagnosticSeverity.Information;
      const diagnostic = new vscode.Diagnostic(
        new vscode.Range(lineNumber, column, lineNumber, column + 1),
        message,
        severity
      );
      diagnostic.source = 'Embedded Trainer';
      const uri = vscode.Uri.file(fileName);
      const key = uri.toString();
      const entry = byFile.get(key) || { uri, diagnostics: [] };
      entry.diagnostics.push(diagnostic);
      byFile.set(key, entry);
    }
    for (const entry of byFile.values()) {
      this.diagnostics.set(entry.uri, entry.diagnostics);
    }
  }
}

module.exports = { TrainerBackend, toCrlf };
