"""BaseSolver — unified execution framework for all automation tasks.

Every business solver inherits from BaseSolver and implements transition().
The run() loop handles:
  - Scene detection and caching (via Recognizer)
  - Scene-specific handler dispatch (via @on decorator)
  - Scene graph navigation fallback
  - Timeout management (scheduler + solver)
  - Game freeze detection (7 min threshold)
  - Consecutive error counting (10 → abort)
"""

import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Dict, Optional, Set, Tuple

from loguru import logger

from resonance.device.device import get_device, input_tap, input_swipe, restart_game
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene
from resonance.scene.waiting import WAITING_SCENES, waiting_solver
from resonance.utils.exceptions import StopExecution


# Decorator to register scene transition handlers
_transition_registry: Dict[str, Dict[Scene, Callable]] = {}


def on(scene: Scene):
    """Decorator: register a method as handler for a specific scene.

    Usage:
        class MySolver(BaseSolver):
            @on(Scene.MAIN_MAP)
            def _handle_main(self):
                ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        wrapper._transition_on = scene
        return wrapper
    return decorator


class BaseSolver:
    """Base class for all automation solvers.

    Subclasses should:
      - Set solver_name for logging
      - Optionally set solver_default_scene (fallback navigation target)
      - Implement transition() or use @on decorators
    """

    solver_name = "BaseSolver"
    solver_default_scene: Optional[Scene] = None

    def __init__(self):
        self.recog = Recognizer()
        self.transition_func: Dict[Scene, Callable] = {}
        self._collect_transition_handlers()

        # Timeout management
        self.scheduler_stop_time: Optional[datetime] = None
        self.solver_stop_time: Optional[datetime] = None

        # Game freeze detection
        self._game_stuck_detection = True
        self._game_stuck_begin: Optional[datetime] = None
        self._last_return = None
        self._stuck_threshold = timedelta(minutes=7)

        # Error counting
        self._exception_budget = 10

    def _collect_transition_handlers(self):
        """Auto-collect methods decorated with @on."""
        for attr_name in dir(self):
            method = getattr(self, attr_name, None)
            if hasattr(method, "_transition_on"):
                scene = method._transition_on
                self.transition_func[scene] = method

    # ---- Main execution loop ----

    def run(self) -> bool:
        """Execute the solver. Returns True if completed, False if deferred."""
        logger.info(f"开始执行: {self.solver_name}")

        while True:
            try:
                # 1. Timeout checks
                now = datetime.now()
                if self.scheduler_stop_time and now > self.scheduler_stop_time:
                    logger.info("调度器时间到，让出执行")
                    return False
                if self.solver_stop_time and now > self.solver_stop_time:
                    logger.warning(f"{self.solver_name} 执行超时，终止")
                    return True

                # 2. Update recognizer (fresh screenshot for this cycle)
                self.recog.update()

                # 3. Execute transition
                result = self.transition()
                if result:
                    logger.info(f"{self.solver_name} 执行完成")
                    return True

                # 4. Game freeze detection
                if self._game_stuck_detection:
                    self._check_freeze(result)

                # 5. Reset error budget on success (no exception thrown)
                self._exception_budget = 10

            except StopExecution:
                raise
            except Exception as e:
                self._exception_budget -= 1
                if self._exception_budget > 0:
                    logger.debug(f"{self.solver_name} 执行异常 (剩余 {self._exception_budget}): {e}")
                else:
                    logger.exception(f"{self.solver_name} 连续异常过多，终止")
                    return True

    def _check_freeze(self, result):
        if result == self._last_return:
            if self._game_stuck_begin is None:
                self._game_stuck_begin = datetime.now()
            elif datetime.now() - self._game_stuck_begin > self._stuck_threshold:
                logger.warning("检测到游戏卡死，重启游戏")
                restart_game()
                self.recog.update()
                self._game_stuck_begin = None
        else:
            self._game_stuck_begin = None
        self._last_return = result

    # ---- Transition dispatch ----

    def transition(self):
        """Determine current scene and dispatch to appropriate handler.

        Dispatch priority:
          1. Direct handler in transition_func (registered via @on)
          2. Scene graph navigation if solver_default_scene is set
          3. Catch-all handler (None key)
        """
        scene = self.recog.scene

        # Direct handler
        if scene in self.transition_func:
            return self.transition_func[scene]()

        # Waiting scene — use waiting_solver
        if scene in WAITING_SCENES:
            logger.info(f"进入等待场景: {scene.name}")
            if waiting_solver(self.recog):
                return self.transition()  # re-dispatch after scene change
            return False

        # Scene graph navigation
        if self.solver_default_scene is not None and scene != self.solver_default_scene:
            return self._navigate_to(self.solver_default_scene)

        # Catch-all handler
        if None in self.transition_func:
            return self.transition_func[None]()

        logger.warning(f"未知场景，无处理程序: {scene.name}")
        return False

    def _navigate_to(self, target: Scene) -> bool:
        """Navigate one step toward target scene using scene graph."""
        from resonance.scene.graph import scene_graph
        return scene_graph.navigate(self.recog.scene, target)

    # ---- Convenience methods ----

    def scene(self) -> Scene:
        return self.recog.scene

    def tap(self, pos: Tuple[int, int]):
        input_tap(pos)

    def ctap(self, pos: Tuple[int, int], count: int = 1, interval: float = 0.3):
        """Click position multiple times."""
        for _ in range(count):
            input_tap(pos)
            if count > 1:
                time.sleep(interval)

    def find(self, template, **kwargs):
        return self.recog.find(template, **kwargs)

    def sleep(self, seconds: float):
        if seconds <= 0:
            return
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            time.sleep(min(0.5, seconds))
            # Allow interruption via StopExecution check
            if hasattr(self, '_check_stop'):
                self._check_stop()

    def wait_for(self, condition: Callable, timeout: float = 30, interval: float = 1.0) -> bool:
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            if condition():
                return True
            time.sleep(interval)
        return False

    def update_scene(self):
        """Force re-capture and re-detection."""
        self.recog.update()
