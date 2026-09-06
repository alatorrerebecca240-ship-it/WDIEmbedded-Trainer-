// Serialize refreshes and replay changes arriving during an in-flight read.
// Full catalog refreshes dominate progress-only reads; watcher bursts are debounced.
class RefreshQueue {
  constructor(run, onError, delay = 150) {
    this.run = run;
    this.onError = onError;
    this.delay = delay;
    this.pending = undefined;
    this.running = undefined;
    this.timer = undefined;
    this.disposed = false;
  }

  enqueue(kind) {
    this.pending = this.pending === 'full' || kind === 'full' ? 'full' : 'progress';
  }

  schedule(kind = 'full') {
    if (this.disposed) return;
    this.enqueue(kind);
    clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = undefined;
      this.drain().catch(this.onError);
    }, this.delay);
  }

  request(kind = 'full') {
    if (this.disposed) return Promise.resolve();
    this.enqueue(kind);
    clearTimeout(this.timer);
    this.timer = undefined;
    return this.drain();
  }

  drain() {
    if (this.running) return this.running;
    this.running = (async () => {
      // Defer the first read so synchronous requests coalesce as well.
      await Promise.resolve();
      let failure;
      while (this.pending && !this.disposed) {
        const kind = this.pending;
        this.pending = undefined;
        try { await this.run(kind); }
        catch (error) { failure = error; }
      }
      if (failure) throw failure;
    })().finally(() => { this.running = undefined; });
    return this.running;
  }

  dispose() {
    this.disposed = true;
    this.pending = undefined;
    clearTimeout(this.timer);
  }
}

module.exports = { RefreshQueue };
