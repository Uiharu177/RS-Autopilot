"""SceneGraphSolver — navigate through scene graph to reach a target scene.

Usage:
    solver = SceneGraphSolver(target=Scene.MAIN_MAP)
    solver.run()
"""

from loguru import logger

from resonance.scene.graph import scene_graph
from resonance.scene.scene import Scene
from resonance.scene.waiting import WAITING_SCENES, waiting_solver
from resonance.solver.base import BaseSolver


class SceneGraphSolver(BaseSolver):
    """Navigate from current scene to target using scene graph."""

    solver_name = "场景图导航"

    def __init__(self, target: Scene):
        self.target_scene = target
        super().__init__()

    def transition(self):
        current = self.recog.scene

        if current == self.target_scene:
            logger.info(f"已到达目标场景: {current.name}")
            return True

        # Handle waiting scenes first
        if current in WAITING_SCENES:
            logger.info(f"场景图中遇到等待场景: {current.name}")
            if waiting_solver(self.recog):
                return self.transition()
            return False

        # Navigate one step
        if not scene_graph.navigate(current, self.target_scene):
            logger.error(f"无法导航: {current.name} -> {self.target_scene.name}")
            self.sleep(10)
            return False

        return False
