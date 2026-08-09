from queue import Full, Queue
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any, Callable


class QueueProxy:
    def __init__(self, name: str, func: Callable[[Any], None], maxsize: int = 64):
        self.name = name
        self.worker_thread: Thread | None = None
        self.func = func
        self.maxsize = maxsize
        self.init_queue()

    def worker(self):
        while True:
            self.func(self.queue.get())

    def init_queue(self):
        self.queue = Queue(maxsize=self.maxsize)
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = Thread(target=self.worker, daemon=True)
            self.worker_thread.start()

    def put(self, data):
        try:
            self.queue.put_nowait(data)
            return True
        except Full:
            # The caller must never be blocked by optional background output.
            # In particular, logging another error here would feed the same
            # WebSocket log queue and amplify an already-full queue.
            return False


class LatestValueProxy:
    """Asynchronous single-slot queue that keeps only the latest value.

    Suitable for previews: an old screenshot has no value once a newer one is
    available, so replacing it avoids delaying automation with stale frames.
    """

    def __init__(self, func: Callable[[Any], None], min_interval: float = 0.0):
        self.func = func
        self.min_interval = max(0.0, min_interval)
        self._lock = Lock()
        self._event = Event()
        self._latest: Any = None
        self._last_sent_at = 0.0
        self._worker = Thread(target=self._run, daemon=True)
        self._worker.start()

    def put(self, data: Any):
        with self._lock:
            self._latest = data
            self._event.set()

    def _run(self):
        while True:
            self._event.wait()
            while True:
                with self._lock:
                    data = self._latest
                    self._latest = None
                    self._event.clear()

                wait_seconds = self.min_interval - (monotonic() - self._last_sent_at)
                if wait_seconds > 0:
                    # A new frame during the rate-limit window supersedes the
                    # current one. This keeps the preview current, not queued.
                    self._event.wait(wait_seconds)
                    if self._event.is_set():
                        continue

                if data is not None:
                    self.func(data)
                    self._last_sent_at = monotonic()

                if not self._event.is_set():
                    break
