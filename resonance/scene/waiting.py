"""短暂/转场场景等待：为每种不稳定场景定义等待策略和超时时间。

  当 Recognizer 遇到 WAITING_SCENES 中的场景时，waiting_solver 持续轮询直到：
  1. 场景变化为已知的可操作场景（返回 True）
  2. 超时（返回 False，由调用方决定是否恢复）

Defines timeout and recovery strategy for each "unstable" scene type.
When the recognizer encounters a scene in the waiting list,
the waiting solver polls until either:
  - The scene changes to something known (return True)
  - The timeout expires (execute recovery action, return False)
"""

import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from loguru import logger

from resonance.device.device import restart_game
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene


@dataclass
class WaitingConfig:
    poll_interval: float = 1.0
    timeout: float = 120.0
    recovery: Optional[Callable] = None
    recovery_text: str = ""


def _kill_game_and_restart():
    restart_game()


# Default configs for each waiting scene type
WAITING_CONFIGS: Dict[Scene, WaitingConfig] = {
    Scene.UNKNOWN: WaitingConfig(
        poll_interval=1.0,
        timeout=120.0,
        recovery=_kill_game_and_restart,
        recovery_text="未知页面超时，重启游戏",
    ),
    Scene.UNKNOWN_WITH_NAVBAR: WaitingConfig(
        poll_interval=0.5,
        timeout=10.0,
        recovery_text="有导航栏的未知页面超时",
    ),
    Scene.TRANSIT: WaitingConfig(
        poll_interval=1.0,
        timeout=30.0,
        recovery_text="过渡动画超时",
    ),
    Scene.LOADING: WaitingConfig(
        poll_interval=3.0,
        timeout=120.0,
        recovery=_kill_game_and_restart,
        recovery_text="加载超时，重启游戏",
    ),
    Scene.CONNECTING: WaitingConfig(
        poll_interval=2.0,
        timeout=30.0,
        recovery=_kill_game_and_restart,
        recovery_text="连接超时，重启游戏",
    ),
    Scene.LOGIN: WaitingConfig(
        poll_interval=2.0,
        timeout=60.0,
        recovery=_kill_game_and_restart,
        recovery_text="登录界面超时，重启游戏",
    ),
    Scene.CRASH: WaitingConfig(
        poll_interval=1.0,
        timeout=3.0,
        recovery=_kill_game_and_restart,
        recovery_text="游戏崩溃页面，重启游戏",
    ),
    Scene.BATTLE_REWARD: WaitingConfig(
        poll_interval=1.0,
        timeout=30.0,
        recovery_text="战斗奖励界面超时",
    ),
    Scene.DIALOG_CONFIRM: WaitingConfig(
        poll_interval=0.5,
        timeout=10.0,
        recovery_text="确认对话框超时",
    ),
    Scene.DIALOG_ERROR: WaitingConfig(
        poll_interval=1.0,
        timeout=15.0,
        recovery_text="错误对话框超时",
    ),
}


# Set of all scenes that should be handled by waiting_solver
WAITING_SCENES = set(WAITING_CONFIGS.keys())


def waiting_solver(recog: Recognizer) -> bool:
    """Poll the current scene until it changes to a non-waiting scene.

    Returns True if the scene resolved (changed to a known scene).
    Returns False if timeout expired (recovery was executed or skipped).
    """
    current = recog.scene
    config = WAITING_CONFIGS.get(current)
    if config is None:
        logger.debug(f"场景 {current.name} 不在等待列表中")
        return True

    logger.info(f"等待场景 {current.name} 恢复 (超时={config.timeout}s, 间隔={config.poll_interval}s)")

    start = time.perf_counter()
    while time.perf_counter() - start < config.timeout:
        time.sleep(config.poll_interval)
        recog.update()
        new_scene = recog.scene

        if new_scene == current or new_scene in WAITING_SCENES:
            continue

        logger.info(f"场景已恢复: {current.name} -> {new_scene.name}")
        return True

    # Timeout — execute recovery
    logger.warning(f"等待超时: {current.name} ({config.recovery_text})")
    if config.recovery:
        try:
            config.recovery()
        except Exception as e:
            logger.exception(f"恢复动作失败: {e}")
    return False
