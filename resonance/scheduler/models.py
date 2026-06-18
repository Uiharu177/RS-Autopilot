"""Task models for the scheduler."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class TaskType(Enum):
    ONETIME = "onetime"
    PERIODIC = "periodic"
    DAILY = "daily"
    LONG = "long"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A schedulable automation task.

    Attributes:
        solver_path: Dotted import path to the Solver class.
        priority: Lower number = higher priority.
        task_type: Type of scheduling (onetime/periodic/daily/long).
        name: Human-readable name.
        enabled: Whether this task should be scheduled.
        schedule_time: For ONETIME tasks — exact datetime to run.
        interval: For PERIODIC tasks — seconds between runs.
        daily_offset: For DAILY tasks — seconds after midnight to run.
        timeout: Max execution time in seconds (None = no limit).
    """
    solver_path: str
    priority: int = 100
    task_type: TaskType = TaskType.ONETIME
    name: str = ""
    enabled: bool = True
    schedule_time: Optional[datetime] = None
    interval: Optional[float] = None
    daily_offset: Optional[float] = None
    timeout: Optional[float] = None
    kwargs: dict = field(default_factory=dict)

    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0

    def __post_init__(self):
        if not self.name:
            self.name = self.solver_path.rsplit(".", 1)[-1]

    def compute_next_run(self) -> Optional[datetime]:
        """Calculate when this task should run next."""
        now = datetime.now()

        if self.task_type == TaskType.ONETIME:
            return self.schedule_time

        if self.task_type == TaskType.PERIODIC and self.interval:
            if self.last_run:
                return self.last_run + timedelta(seconds=self.interval)
            return now

        if self.task_type == TaskType.DAILY and self.daily_offset is not None:
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            candidate = today + timedelta(seconds=self.daily_offset)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        if self.task_type == TaskType.LONG:
            return now

        return None

    def mark_run(self):
        """Update state after a run attempt."""
        self.last_run = datetime.now()
        self.run_count += 1
        self.status = TaskStatus.PENDING
        self.next_run = self.compute_next_run()
