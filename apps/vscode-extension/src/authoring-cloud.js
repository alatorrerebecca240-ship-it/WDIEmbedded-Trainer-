const vscode = require('vscode');
const https = require('node:https');
const crypto = require('node:crypto');
const path = require('node:path');

const DEFAULT_REPOSITORY = 'alatorrerebecca240-ship-it/WDIEmbedded-Trainer-';
const WORKFLOW = 'acquire-review.yml';
const WORKFLOW_PATH = `.github/workflows/${WORKFLOW}`;
const JOBS_KEY = 'trainer.inbox.cloudJobs.v1';
const MAX_BYTES = 8 * 1024 * 1024;

function repository(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(value)
      || value.split('/').some((v) => v === '.' || v === '..')) throw new Error('GitHub 仓库格式应为 owner/repo。');
  return value;
}

function requestRaw(url, { token, method = 'GET', body } = {}) {
  const target = new URL(url);
  const isApi = target.hostname === 'api.github.com';
  const asset = target.hostname.endsWith('.blob.core.windows.net') || target.hostname.endsWith('.actions.githubusercontent.com')
    || ['release-assets.githubusercontent.com', 'objects.githubusercontent.com'].includes(target.hostname);
  if (target.protocol !== 'https:' || target.username || target.password || target.port || (!isApi && !asset)
      || (token && !isApi)) return Promise.reject(new Error('拒绝不可信下载地址或跨站凭据转发。'));
  return new Promise((resolve, reject) => {
    const headers = { 'User-Agent': 'Embedded-Trainer', Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const bytes = body === undefined ? undefined : Buffer.from(JSON.stringify(body));
    if (bytes) { headers['Content-Type'] = 'application/json'; headers['Content-Length'] = bytes.length; }
    const req = https.request(target, { method, headers }, (res) => {
      const chunks = []; let size = 0;
      res.on('data', (chunk) => {
        size += chunk.length;
        if (size > MAX_BYTES) { res.destroy(); req.destroy(new Error('GitHub 响应超过大小限制。')); }
        else chunks.push(chunk);
      });
      res.on('error', () => reject(new Error('GitHub 下载中断；缓存和草稿已保留。')));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
    });
    const deadline = setTimeout(() => req.destroy(new Error('GitHub 请求超时；请稍后重试。')), 30000);
    req.on('close', () => clearTimeout(deadline));
    // Do not log request URLs, signed artifact URLs, headers or tokens.
    req.on('error', () => reject(new Error('无法连接 GitHub；草稿已保留，可稍后重试。')));
    req.end(bytes);
  });
}

class AuthoringCloud {
  constructor(context, backend, transport = requestRaw, timers = { setTimeout, clearTimeout }) {
    this.context = context; this.backend = backend; this.transport = transport;
    this.busy = false; this.timer = undefined; this.timers = timers;
    this.started = false; this.failures = 0; this.retryAt = 0;
  }
  jobs() { return this.context.workspaceState.get(JOBS_KEY, []); }
  async save(job) {
    const jobs = this.jobs().filter((v) => v.requestId !== job.requestId);
    jobs.push(job);
    await this.context.workspaceState.update(JOBS_KEY, jobs.filter((v) => !v.done || Date.now() - v.createdAt < 7 * 86400000));
  }
  async command(args) {
    const result = await this.backend.run(['packs', ...args], { silent: true });
    if (result.code !== 0) throw new Error(result.output || '审核收件箱操作失败。');
    return JSON.parse(result.stdout);
  }
  async api(repo, endpoint, token, options = {}) {
    repository(repo);
    const response = await this.transport(`https://api.github.com/repos/${repo}/${endpoint}`, { ...options, token });
    if (response.status < 200 || response.status >= 300) {
      const error = new Error(response.status === 404
        ? '云端工作流尚未部署或无权访问。请先推送本轮工具和 acquire-review.yml；本地草稿已保留。'
        : `GitHub 返回 HTTP ${response.status}。请检查登录权限、限流或稍后重试。`);
      error.status = response.status;
      const retry = Number(response.headers?.['retry-after']);
      const reset = Number(response.headers?.['x-ratelimit-reset']) * 1000 - Date.now();
      error.retryAfterMs = Number.isFinite(retry) && retry > 0 ? retry * 1000
        : response.headers?.['x-ratelimit-remaining'] === '0' && reset > 0 ? reset : 0;
      throw error;
    }
    return response.body.length ? JSON.parse(response.body.toString('utf8')) : {};
  }
  async dispatch() {
    if (this.busy) return;
    this.busy = true;
    try {
      const repo = repository(vscode.workspace.getConfiguration('embeddedTrainer').get('authoringRepository', DEFAULT_REPOSITORY));
      const consentKey = `trainer.inbox.cloudConsent.${repo}`;
      if (!this.context.workspaceState.get(consentKey, false)) {
        const choice = await vscode.window.showWarningMessage(
          `允许为 ${repo} 自动启动 GitHub Actions 验证吗？仅发送公开上游题目标识、固定提交和校验值，不上传本地源码或学习答案。首次需要 GitHub 登录授权；后续点击“获取新题”会自动验证，但不会自动审批、推送或发布。`,
          { modal: true }, '允许云端验证');
        if (choice !== '允许云端验证') return;
        await this.context.workspaceState.update(consentKey, true);
      }
      const session = await vscode.authentication.getSession('github', ['repo'], { createIfNone: true });
      const workflow = await this.api(repo, `actions/workflows/${WORKFLOW}`, session.accessToken);
      if (workflow.path !== WORKFLOW_PATH || workflow.state !== 'active') throw new Error('不是预期的已启用审核工作流。');
      const head = await this.api(repo, 'commits/main', session.accessToken);
      if (!/^[a-f0-9]{40}$/.test(head.sha)) throw new Error('无法固定云端工具提交。');
      const requestId = crypto.randomBytes(16).toString('hex');
      const plan = await this.command(['inbox-plan', '--request', requestId]);
      if (!plan.entries.length) return;
      const job = { requestId, repo, headSha: head.sha, workflowId: workflow.id, createdAt: Date.now(), done: false };
      // Save before POST: if the response is lost, resume by unique run-name, not another dispatch.
      await this.save(job);
      try {
        const result = await this.api(repo, `actions/workflows/${WORKFLOW}/dispatches`, session.accessToken,
          { method: 'POST', body: { ref: 'main', inputs: { request_id: requestId, plan: JSON.stringify(plan) } } });
        if (Number.isSafeInteger(result.workflow_run_id) && result.workflow_run_id > 0) job.runId = result.workflow_run_id;
        await this.save(job);
        vscode.window.showInformationMessage(`已提交 ${plan.entries.length} 道题到云端验证。完成后会自动更新集中审核列表。`);
      } catch (error) {
        if (error.status >= 400 && error.status < 500) {
          await this.command(['inbox-fail', '--request', requestId, '--reason', error.message]);
          await this.save({ ...job, done: true });
        }
        // Network/5xx ambiguity: keep the unique job and poll; never blindly POST twice.
        throw error;
      }
    } finally { this.busy = false; this.schedule(); }
  }
  start() {
    if (this.started) return;
    this.started = true;
    this.context.subscriptions.push({ dispose: () => {
      this.started = false; this.timers.clearTimeout(this.timer); this.timer = undefined;
    } });
    this.schedule();
  }
  schedule() {
    this.timers.clearTimeout(this.timer); this.timer = undefined;
    if (!this.started || this.busy || !this.jobs().some((v) => !v.done)) return;
    const delay = Math.max(15000, this.retryAt - Date.now());
    this.timer = this.timers.setTimeout(() => {
      this.timer = undefined;
      this.poll(true).catch(() => {});
    }, Math.min(delay, 2147483647));
  }
  backoff(error) {
    this.failures = Math.min(this.failures + 1, 5);
    this.retryAt = Math.max(this.retryAt, Date.now() + Math.max(
      Math.min(300000, 15000 * 2 ** this.failures), error?.retryAfterMs || 0));
  }
  async poll(silent = false) {
    if (this.busy) return;
    if (Date.now() < this.retryAt) { this.schedule(); return; }
    const pending = this.jobs().filter((v) => !v.done);
    if (!pending.length) return;
    this.busy = true;
    try {
      const session = await vscode.authentication.getSession('github', ['repo'], { silent: true });
      if (!session) {
        this.retryAt = Date.now() + 60000;
        if (!silent) vscode.window.showInformationMessage('请通过“重新验证”登录 GitHub；本地审核列表仍可使用。');
        return;
      }
      let failed = false;
      for (const job of pending) {
        try { await this.pollJob(job, session.accessToken); }
        catch (error) {
          failed = true; this.backoff(error);
          if (!silent) vscode.window.showWarningMessage(error.message);
          // Transient failures retain both the current state and pending job.
          if (error.status === 429 || error.status === 403) break;
        }
      }
      if (!failed) { this.failures = 0; this.retryAt = 0; }
    } catch (error) {
      this.backoff(error);
      if (!silent) vscode.window.showWarningMessage(error.message);
    } finally { this.busy = false; this.schedule(); }
  }
  async pollJob(job, token) {
    repository(job.repo);
    let run;
    if (job.runId) run = await this.api(job.repo, `actions/runs/${job.runId}`, token);
    else {
      const list = await this.api(job.repo, `actions/workflows/${WORKFLOW}/runs?event=workflow_dispatch&per_page=100`, token);
      run = (list.workflow_runs || []).find((v) => v.display_title === `trainer-review-${job.requestId}`);
    }
    if (!run) {
      if (Date.now() - job.createdAt > 30 * 60000) return this.finishFailed(job, '30 分钟内未找到对应云端任务，请确认 GitHub 状态后手动重试。');
      return;
    }
    if (run.head_sha !== job.headSha || run.path !== WORKFLOW_PATH || run.workflow_id !== job.workflowId
        || run.event !== 'workflow_dispatch' || run.display_title !== `trainer-review-${job.requestId}`
        || run.head_repository?.full_name?.toLowerCase() !== job.repo.toLowerCase()) {
      return this.finishFailed(job, '云端任务身份或提交不匹配，拒绝接收验证结果。');
    }
    if (!Number.isSafeInteger(run.id) || run.id <= 0) throw new Error('无效的 GitHub 任务编号。');
    job.runId = run.id;
    await this.save(job);
    if (run.status !== 'completed') return;
    if (run.conclusion !== 'success') return this.finishFailed(job, `云端任务未完整结束（${run.conclusion}）；没有题目因此获得审核资格。`);
    const name = `trainer-review-${job.requestId}`;
    const list = await this.api(job.repo, `actions/runs/${run.id}/artifacts?per_page=100&name=${name}`, token);
    const artifacts = (list.artifacts || []).filter((v) => v.name === name && !v.expired);
    if (artifacts.length !== 1) return this.finishFailed(job, '验证报告缺失、过期或不唯一，请重新验证。');
    const artifact = artifacts[0];
    if (!Number.isSafeInteger(artifact.id) || artifact.id <= 0 || artifact.size_in_bytes > MAX_BYTES
        || !/^sha256:[a-f0-9]{64}$/.test(artifact.digest || '')) throw new Error('云端报告缺少有效校验信息。');
    const redirect = await this.transport(`https://api.github.com/repos/${job.repo}/actions/artifacts/${artifact.id}/zip`, { token });
    if (redirect.status !== 302 || !redirect.headers.location) throw new Error('无法获取云端报告下载地址。');
    const response = await this.transport(redirect.headers.location); // NO GitHub token on redirect!
    if (response.status !== 200 || response.body.length > MAX_BYTES) throw new Error('云端报告下载失败。');
    const sha = crypto.createHash('sha256').update(response.body).digest('hex');
    if (`sha256:${sha}` !== artifact.digest) throw new Error('云端报告 SHA-256 不匹配，拒绝接收。');
    // Private extension storage, not a directory/link supplied by an untrusted draft.
    const folder = vscode.Uri.file(path.join(this.context.globalStorageUri.fsPath, 'authoring-downloads'));
    await vscode.workspace.fs.createDirectory(folder);
    const file = vscode.Uri.file(path.join(folder.fsPath, `${job.requestId}.zip`));
    await vscode.workspace.fs.writeFile(file, response.body);
    const result = await this.command(['inbox-results', '--request', job.requestId, '--archive', file.fsPath, '--sha256', sha]);
    await this.save({ ...job, done: true });
    vscode.window.showInformationMessage(`云端结果已接收：当前 ${result.counts.ready || 0} 道待人工审核，${result.counts['validation-failed'] || 0} 道需处理。`, '集中审核')
      .then((choice) => { if (choice) vscode.commands.executeCommand('embeddedTrainer.reviewInbox'); });
  }
  async finishFailed(job, reason) {
    await this.command(['inbox-fail', '--request', job.requestId, '--reason', reason]);
    await this.save({ ...job, done: true });
    vscode.window.showWarningMessage(reason);
  }
}

module.exports = { AuthoringCloud, requestRaw, repository, WORKFLOW_PATH };
