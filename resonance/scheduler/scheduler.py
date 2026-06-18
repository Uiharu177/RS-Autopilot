"""Scheduler — manages task execution with priority and time-based queues.

Architecture:
  - priority_queue: tasks ready to run now, ordered by priority (ascending)
  - time_queue: tasks scheduled for future, ordered by next_run (ascending)
  - update_queue(): moves due tasks from time_queue to priority_queue
  - schedule(): main loop — pick highest priority task, execute, re-queue
"""

import importlib
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Set

from loguru import logger

from resonance.scheduler.models import Task, TaskStatus, TaskType
from resonance.utils.exceptions import StopExecution


class Scheduler:
    """Task scheduler with priority and time-based queues."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._priority_queue: List[Task] = []
        self._time_queue: List[Task] = []

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Current execution state
        self._current_solver_path: Optional[str] = None
        self._current_priority: int = 0

    # ---- Task management ----

    def register(self, task: Task):
        """Register a new task."""
        with self._lock:
            old_task = self._tasks.get(task.solver_path)
            if old_task and old_task.status == TaskStatus.RUNNING:
                logger.warning(f"替换正在运行的任务: {old_task.name}")
            task.next_run = task.compute_next_run()
            self._tasks[task.solver_path] = task
            self._rebuild_queues()
            logger.info(f"注册任务: {task.name} (优先级={task.priority}, 类型={task.task_type.value})")

    def unregister(self, solver_path: str):
        """Remove a task by solver path."""
        with self._lock:
            task = self._tasks.pop(solver_path, None)
            if task:
                task.enabled = False
                task.status = TaskStatus.CANCELLED
            self._rebuild_queues()

    def get_task(self, solver_path: str) -> Optional[Task]:
        return self._tasks.get(solver_path)

    @property
    def tasks(self) -> List[Task]:
        return list(self._tasks.values())

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_task(self) -> Optional[str]:
        return self._current_solver_path

    # ---- Queue management ----

    def _add_to_queue(self, task: Task):
        """Add a task to the appropriate queue."""
        if not task.enabled:
            return
        if task.next_run is None or task.next_run <= datetime.now():
            self._priority_queue.append(task)
            self._priority_queue.sort(key=lambda t: t.priority)
        else:
            self._time_queue.append(task)
            self._time_queue.sort(key=lambda t: t.next_run or datetime.max)

    def _rebuild_queues(self):
        """Rebuild both queues from scratch."""
        self._priority_queue.clear()
        self._time_queue.clear()
        for task in self._tasks.values():
            self._add_to_queue(task)

    def _update_queues(self):
        """Move tasks from time_queue to priority_queue when due."""
        now = datetime.now()
        due = []
        remaining = []
        for task in self._time_queue:
            if task.next_run and task.next_run <= now:
                due.append(task)
            else:
                remaining.append(task)

        if due:
            self._priority_queue.extend(due)
            self._priority_queue.sort(key=lambda t: t.priority)

        self._time_queue = remaining

    # ---- Scheduling loop ----

    def start(self):
        """Start the scheduler in a background thread."""
        if self._running:
            logger.warning("调度器已在运行")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("调度器已启动")

    def stop(self):
        """Stop the scheduler gracefully."""
        self._stop_event.set()
        self._running = False
        try:
            from resonance.device.device import stop as stop_device_actions

            stop_device_actions()
        except Exception as e:
            logger.warning(f"发送设备停止信号失败: {e}")
        logger.info("调度器停止信号已发送")

    def _run_loop(self):
        """Main scheduling loop (runs in background thread)."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.exception(f"调度器循环异常: {e}")
            time.sleep(1)

    def _tick(self):
        """One iteration of the scheduling loop."""
        self._update_queues()

        if not self._priority_queue:
            time.sleep(1)
            return

        task = self._priority_queue.pop(0)
        if not task.enabled:
            return

        logger.info(f"执行任务: {task.name} (优先级={task.priority})")
        task.status = TaskStatus.RUNNING
        self._current_solver_path = task.solver_path
        self._current_priority = task.priority

        try:
            solver = self._import_solver(task.solver_path)
            if solver is None:
                task.status = TaskStatus.FAILED
                self._current_solver_path = None
                return

            solver_instance = solver(**task.kwargs) if task.kwargs else solver()
            if task.timeout:
                solver_instance.solver_stop_time = datetime.now() + __import__("datetime").timedelta(seconds=task.timeout)

            result = solver_instance.run()
            if self._tasks.get(task.solver_path) is not task:
                logger.info(f"任务已被取消或替换，跳过后续重排: {task.name}")
                return

            task.mark_run()

            if result:
                logger.info(f"任务完成: {task.name}")
                task.status = TaskStatus.COMPLETED if task.task_type != TaskType.LONG else TaskStatus.PENDING

                if task.task_type == TaskType.ONETIME:
                    task.enabled = False

                self._add_to_queue(task)
            else:
                logger.info(f"任务让出: {task.name} (时间不够)")
                self._add_to_queue(task)

        except StopExecution:
            logger.info(f"任务已停止: {task.name}")
            task.status = TaskStatus.CANCELLED
            task.enabled = False
        except Exception as e:
            logger.exception(f"任务执行异常: {task.name} - {e}")
            task.status = TaskStatus.FAILED

        self._current_solver_path = None

        with self._lock:
            if self._running and not any(t.enabled for t in self._tasks.values()):
                logger.info("所有任务已完成，自动停止调度器")
                self._running = False
                self._stop_event.set()

    @staticmethod
    def _import_solver(solver_path: str):
        """Dynamically import a solver class by dotted path."""
        try:
            module_path, class_name = solver_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError, ValueError) as e:
            logger.error(f"导入Solver失败: {solver_path} - {e}")
            return None
