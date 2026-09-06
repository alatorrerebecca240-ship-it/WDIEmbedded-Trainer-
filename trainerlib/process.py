"""Bound process output as well as wall time during publication verification."""

import subprocess
import threading

from .common import PackError


def limited_run(command, cwd=None, timeout=30, limit=1024 * 1024):
    child = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    streams = [bytearray(), bytearray()]
    lock = threading.Lock()
    exceeded = threading.Event()

    def drain(pipe, target):
        while True:
            data = pipe.read(4096)
            if not data:
                break
            with lock:
                size = sum(map(len, streams))
                target.extend(data[:max(0, limit - size)])
                if size + len(data) > limit:
                    exceeded.set()
                    child.kill()
                    break
        pipe.close()

    threads = [threading.Thread(target=drain, args=(pipe, output), daemon=True) for pipe, output in zip((child.stdout, child.stderr), streams)]
    for thread in threads:
        thread.start()
    try:
        child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)
        raise
    finally:
        for thread in threads:
            thread.join(timeout=2)
    if exceeded.is_set():
        raise PackError("Compiler/test output limit exceeded")
    return subprocess.CompletedProcess(command, child.returncode, streams[0].decode("utf-8", errors="replace"), streams[1].decode("utf-8", errors="replace"))
