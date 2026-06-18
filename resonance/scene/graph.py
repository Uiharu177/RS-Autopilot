"""Scene graph for navigation between known game states.

Uses NetworkX directed graph. Each edge has:
  - weight: int (lower = preferred path)
  - transition: callable (the action to take)

Global instance `scene_graph` is used by all solvers.
"""

from typing import Callable, Dict, List, Optional, Tuple

import networkx as nx
from loguru import logger

from resonance.device.device import input_tap
from resonance.scene.scene import Scene


class SceneGraph:
    """Directed graph of valid scene transitions."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._transitions: Dict[Tuple[int, int], Callable] = {}
        self._build_defaults()

    def _build_defaults(self):
        """Define common navigation edges."""

        # --- Main map transitions ---
        self.add_edge(Scene.MAIN_MAP, Scene.CITY_VIEW, self._go_home)
        self.add_edge(Scene.CITY_VIEW, Scene.MAIN_MAP, self._go_home)

        # --- City → Exchange ---
        self.add_edge(Scene.CITY_VIEW, Scene.EXCHANGE_BUY, self._go_exchange_buy)
        self.add_edge(Scene.CITY_VIEW, Scene.EXCHANGE_SELL, self._go_exchange_sell)

        # --- Exchange → Main map ---
        self.add_edge(Scene.EXCHANGE_BUY, Scene.MAIN_MAP, self._back_to_main)
        self.add_edge(Scene.EXCHANGE_SELL, Scene.MAIN_MAP, self._back_to_main)

        # --- Shop → Main map ---
        self.add_edge(Scene.SHOP, Scene.MAIN_MAP, self._back_to_main)

        # --- Station detail → Main map ---
        self.add_edge(Scene.STATION_DETAIL, Scene.MAIN_MAP, self._back_to_main)

    # ---- Default navigation actions ----

    @staticmethod
    def _go_home():
        from resonance.device.device import input_tap
        input_tap((83, 36))

    @staticmethod
    def _go_exchange_buy():
        from resonance.solvers.exchange import enter_exchange
        enter_exchange("buy")

    @staticmethod
    def _go_exchange_sell():
        from resonance.solvers.exchange import enter_exchange
        enter_exchange("sell")

    @staticmethod
    def _back_to_main():
        # Tap back button twice
        input_tap((83, 36))
        import time
        time.sleep(0.5)
        input_tap((83, 36))

    # ---- Edge management ----

    def add_edge(
        self,
        from_scene: Scene,
        to_scene: Scene,
        action: Callable,
        weight: int = 1,
    ):
        self.graph.add_edge(from_scene, to_scene, weight=weight)
        self._transitions[(from_scene, to_scene)] = action

    def shortest_path(
        self, from_scene: Scene, to_scene: Scene
    ) -> Optional[List[Scene]]:
        if from_scene not in self.graph or to_scene not in self.graph:
            return None
        try:
            return nx.shortest_path(self.graph, from_scene, to_scene, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_action(self, from_scene: Scene, to_scene: Scene) -> Optional[Callable]:
        return self._transitions.get((from_scene, to_scene))

    def navigate(self, from_scene: Scene, to_scene: Scene) -> bool:
        """Execute one step of navigation from from_scene toward to_scene."""
        path = self.shortest_path(from_scene, to_scene)
        if not path or len(path) < 2:
            logger.warning(f"场景图中无路径: {from_scene.name} -> {to_scene.name}")
            return False

        next_scene = path[1]
        action = self.get_action(from_scene, next_scene)
        if action is None:
            logger.warning(f"场景图中无动作: {from_scene.name} -> {next_scene.name}")
            return False

        logger.info(f"场景导航: {from_scene.name} -> {next_scene.name}")
        try:
            action()
            return True
        except Exception as e:
            logger.exception(f"场景导航失败: {e}")
            return False


# Global instance used by all solvers
scene_graph = SceneGraph()
