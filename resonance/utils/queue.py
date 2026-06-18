from queue import Full, Queue
from threading import Thread
from typing import Any, Callable


class QueueProxy:
    def __init__(self, name: str, func: Callable[[Any], None]):
        self.name = name
        self.worker_thread: Thread | None = None
        self.func = func
        self.init_queue()

    def worker(self):
        while True:
            self.func(self.queue.get())

    def init_queue(self):
        self.queue = Queue(maxsize=64)
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = Thread(target=self.worker, daemon=True)
            self.worker_thread.start()

    def put(self, data):
        try:
            self.queue.put_nowait(data)
        except Full:
            from resonance.utils.logger import logger

            self.init_queue()
            logger.error(f"{self.name}队列已满")
