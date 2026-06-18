"""
恢复纠错模块 — 工作范围声明

职责：
1. 场景恢复循环（recover_to_expected）—— 无论当前在哪个场景，都能回到期望场景（MAIN_MAP / CITY_VIEW）
2. 启动接管（takeover_to_station）—— 游戏刚启动/重启后，处理登录/公告/更新/加载，到达可读页面
3. 行车恢复（wait_or_recover_travel）—— mid-travel 恢复，支持继续行驶或重新导航
4. 原子恢复工具 —— safe_go_home / close_station_list / identify_city / click_arrive_city

边界（不属于本模块）：
- 场景检测 → resonance/scene/ 各 detect() + Recognizer 调度
- 页面内操作 → resonance/solvers/ 下各自模块（buy.py / sell.py / exchange.py / city.py）
- 跑商编排 → trade.py（组合多个 recover_to_expected + 业务操作）
- 体力处理 → strength.py
- 地图导航 → navigation.py
- 启动游戏进程 → device.py (start_game / stop_game / restart_game + ensure_game_foreground)
- 第0章编排 → boot.py（调用 takeover_to_station 等）

关键设计约束：
- recover_to_expected 每次只做一件事 → 截屏 → 再检测，不假定重进游戏一定回到主页
- 启动上下文（STARTUP/BOOT）用 short_wait（6s）而非 waiting_solver（30s）
- 登录点击强制走 ADB shell tap（NEMU touch 在登录页不可靠）
"""

from dataclasses import dataclass, field
import time
from typing import Optional, Set

from loguru import logger

from resonance.debug.snapshot import capture_debug_snapshot
from resonance.device.adb import ADB
from resonance.device.device import get_device, input_back, input_tap, restart_game, screenshot
from resonance.model import app
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene
from resonance.scene.waiting import WAITING_SCENES, waiting_solver
from resonance.utils.utils import RESOURCES_PATH
from resonance.vision.ocr import predict


@dataclass
class CurrentState:
    scene: Scene
    city: Optional[str] = None
    in_travel: bool = False


@dataclass
class RecoveryContext:
    step: str
    expected_scenes: Set[Scene]
    target_city: Optional[str] = None
    allow_travel: bool = False
    max_attempts: int = 12


@dataclass
class RecoveryResult:
    ok: bool
    state: Optional[CurrentState] = None
    reason: str = ""
    attempts: int = 0
    snapshot: Optional[str] = None
    actions: list[str] = field(default_factory=list)


def _ocr_center(item: dict) -> tuple[int, int]:
    position = item["position"]
    return (
        int((position[0][0] + position[2][0]) / 2),
        int((position[0][1] + position[2][1]) / 2),
    )


def _raw_adb_tap(pos: tuple[int, int]) -> bool:
    adb = ADB()
    try:
        if not adb.connect(app.Global.device.port):
            return False
        adb.device.shell(f"input tap {int(pos[0])} {int(pos[1])}")
        return True
    except Exception as e:
        logger.warning(f"恢复流程：ADB直点失败: {e}")
        return False
    finally:
        adb.kill()


def _wait_scene_leave(scene: Scene, timeout: float = 8.0) -> bool:
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        time.sleep(1.0)
        current = Recognizer().scene
        if current != scene:
            logger.info(f"恢复流程：场景已离开 {scene.name} -> {current.name}")
            return True
    logger.warning(f"恢复流程：等待离开 {scene.name} 超时")
    return False


def _short_wait_scene_change(current: Scene, timeout: float = 6.0, interval: float = 1.0) -> bool:
    logger.info(f"恢复流程：短等场景 {current.name} 恢复 (超时={timeout}s)")
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        time.sleep(interval)
        new_scene = Recognizer().scene
        if new_scene != current and new_scene not in (Scene.TRANSIT, Scene.LOADING, Scene.CONNECTING):
            logger.info(f"恢复流程：短等恢复完成 {current.name} -> {new_scene.name}")
            return True
    logger.warning(f"恢复流程：短等场景 {current.name} 超时")
    return False


def _is_startup_context(context: RecoveryContext) -> bool:
    return "STARTUP" in context.step or "BOOT" in context.step


def _tap_login(recog: Recognizer) -> bool:
    login_markers = ("点击屏幕进入游戏", "点击进入", "TOUCH TO START", "TAP TO START")
    for item in recog.ocr():
        text = item["text"].upper()
        if any(marker in text for marker in login_markers):
            pos = _ocr_center(item)
            if not _raw_adb_tap(pos):
                input_tap(pos)
            logger.info("恢复流程：点击登录入口")
            return True
    if not _raw_adb_tap((640, 360)):
        input_tap((640, 360))
    logger.info("恢复流程：未定位登录文字，点击屏幕中心")
    return True


def _confirm_update_if_needed(recog: Recognizer) -> bool:
    results = recog.ocr()
    if not any("需要下载资源" in item["text"] or "资源包" in item["text"] for item in results):
        return False
    for item in results:
        if "确认" in item["text"] or "确定" in item["text"]:
            input_tap(_ocr_center(item))
            logger.info("恢复流程：确认资源更新")
            return True
    input_tap((666, 505))
    logger.info("恢复流程：点击默认资源更新确认位置")
    return True


def _tap_text(results: list, keywords: tuple[str, ...], log_text: str) -> bool:
    for item in results:
        if any(keyword in item["text"] for keyword in keywords):
            input_tap(_ocr_center(item))
            logger.info(log_text)
            return True
    return False


def handle_startup_interruption(recog: Recognizer) -> bool:
    """Handle login/update/news overlays before generic unknown-page recovery."""
    results = recog.ocr()
    has_update = any(
        "需要下载资源" in item["text"]
        or "资源包" in item["text"]
        or "下载资源" in item["text"]
        for item in results
    )
    if has_update:
        if _tap_text(results, ("确认", "确定"), "恢复流程：确认资源更新"):
            return True
        input_tap((666, 505))
        logger.info("恢复流程：资源更新未定位按钮，点击默认确认位置")
        return True

    has_blank_tap = any("触碰空白区域退出" in item["text"] for item in results)
    if has_blank_tap:
        if not _raw_adb_tap((100, 100)):
            input_tap((100, 100))
        logger.info("恢复流程：点击空白区域关闭公告弹窗")
        return True

    has_news = any(
        "游戏资讯" in item["text"]
        or "资讯" in item["text"]
        or "公告" in item["text"]
        or "活动" in item["text"]
        for item in results
    )
    if has_news:
        if _tap_text(
            results,
            ("关闭", "跳过", "我知道了", "知道了", "确定", "确认"),
            "恢复流程：关闭启动公告/资讯",
        ):
            return True
        input_tap((1200, 80))
        logger.info("恢复流程：启动公告未定位按钮，点击右上角关闭位置")
        return True

    return False


def click_arrive_city() -> bool:
    results = predict(Recognizer().image)
    for item in results:
        if "访问城市" in item["text"] or "访问地区" in item["text"]:
            position = item["position"]
            center_x = int((position[0][0] + position[2][0]) / 2)
            center_y = int((position[0][1] + position[2][1]) / 2)
            if not (1100 <= center_x <= 1245 and 430 <= center_y <= 560):
                logger.debug(f"恢复流程：忽略非进城入口访问城市文本: {(center_x, center_y)}")
                continue
            device = get_device()
            device.input_tap(int(device.ratio * center_x), int(device.ratio * center_y))
            logger.info("恢复流程：精确点击右侧访问城市入口")
            time.sleep(2.0)
            return True
    logger.info("恢复流程：未定位右下访问城市入口")
    return False


def identify_city() -> Optional[str]:
    from resonance.solvers.city import identify_city_from_current_screen, _pick_city_name

    city = identify_city_from_current_screen()
    if city:
        return city

    input_tap((1170, 493))
    time.sleep(1.0)
    frame = Recognizer().image
    regions = [
        ((166, 370), (470, 450)),
        ((166, 520), (470, 600)),
    ]
    for pos1, pos2 in regions:
        results = predict(frame, cropped_pos1=pos1, cropped_pos2=pos2)
        city = _pick_city_name(results)
        if city:
            logger.info(f"恢复流程：当前站点 {city}")
            return city
    logger.warning("恢复流程：未识别到当前城市")
    return None


def safe_go_home(max_attempts: int = 8) -> bool:
    for attempt in range(1, max_attempts + 1):
        recog = Recognizer()
        scene = recog.scene
        if scene == Scene.MAIN_MAP:
            return True
        if screenshot().match_template(RESOURCES_PATH / "scene/main_map.png", 0.96):
            return True
        logger.debug(f"恢复流程：尝试返回主界面 ({attempt}/{max_attempts}), 当前 {scene.name}")
        input_tap((83, 36))
        time.sleep(0.8)
        if attempt % 3 == 0:
            input_back()
            time.sleep(0.8)
    return Recognizer().scene == Scene.MAIN_MAP


def close_station_list(max_attempts: int = 4) -> bool:
    """Close the map/station-list overlay without treating it as a waiting scene."""
    for attempt in range(1, max_attempts + 1):
        scene = Recognizer().scene
        if scene in (Scene.MAIN_MAP, Scene.CITY_VIEW):
            return True
        if scene != Scene.STATION_LIST:
            return False
        logger.info(f"恢复流程：关闭站点/地图列表 ({attempt}/{max_attempts})")
        input_tap((83, 36))
        time.sleep(0.8)
        if attempt % 2 == 0:
            input_back()
            time.sleep(0.8)
    return Recognizer().scene in (Scene.MAIN_MAP, Scene.CITY_VIEW)


def inspect_current_state() -> CurrentState:
    recog = Recognizer()
    scene = recog.scene
    in_travel = scene in (Scene.TRAVEL_CRUISE, Scene.TRAVEL_MAP, Scene.BATTLE_CARD)
    city = identify_city() if scene == Scene.CITY_VIEW else None
    return CurrentState(scene=scene, city=city, in_travel=in_travel)


def recover_to_expected(context: RecoveryContext) -> RecoveryResult:
    actions: list[str] = []
    for attempt in range(1, context.max_attempts + 1):
        recog = Recognizer()
        if handle_startup_interruption(recog):
            actions.append("handle_startup_interruption")
            time.sleep(1.5)
            continue

        state = inspect_current_state()
        logger.info(
            f"恢复流程：step={context.step}, attempt={attempt}/{context.max_attempts}, "
            f"scene={state.scene.name}, city={state.city}"
        )

        if state.scene in context.expected_scenes:
            return RecoveryResult(ok=True, state=state, attempts=attempt, actions=actions)

        if state.scene == Scene.CRASH:
            snapshot = capture_debug_snapshot(reason=f"{context.step}:crash")
            actions.append("restart_game")
            restart_game()
            time.sleep(5.0)
            continue

        if state.scene == Scene.LOGIN:
            recog = Recognizer()
            _confirm_update_if_needed(recog)
            _tap_login(recog)
            actions.append("tap_login")
            _wait_scene_leave(Scene.LOGIN, timeout=10.0)
            continue

        if state.scene in (Scene.LOADING, Scene.TRANSIT, Scene.CONNECTING) or state.scene in WAITING_SCENES:
            if _is_startup_context(context):
                actions.append("short_wait_scene_change")
                _short_wait_scene_change(state.scene)
            else:
                actions.append("waiting_solver")
                waiting_solver(Recognizer())
            time.sleep(1.0)
            continue

        if state.scene in (Scene.TRAVEL_CRUISE, Scene.TRAVEL_MAP, Scene.BATTLE_CARD):
            if not context.allow_travel:
                snapshot = capture_debug_snapshot(reason=f"{context.step}:unexpected_travel")
                return RecoveryResult(
                    ok=False,
                    state=state,
                    reason="unexpected travel scene",
                    attempts=attempt,
                    snapshot=snapshot.get("screenshot"),
                    actions=actions,
                )
            from resonance.solvers.navigation import travel_monitor

            actions.append("travel_monitor")
            if not travel_monitor():
                capture_debug_snapshot(reason=f"{context.step}:travel_monitor_failed")
                restart_game()
                actions.append("restart_game")
                time.sleep(5.0)
            continue

        if state.scene == Scene.TASK_DETAIL:
            actions.append("close_task_detail")
            input_back()
            time.sleep(1.0)
            continue

        if state.scene == Scene.STATION_LIST:
            actions.append("close_station_list")
            if not close_station_list():
                actions.append("safe_go_home")
                if not safe_go_home():
                    input_back()
                    actions.append("input_back")
            time.sleep(1.0)
            continue

        if state.scene in (
            Scene.EXCHANGE,
            Scene.EXCHANGE_BUY,
            Scene.EXCHANGE_SELL,
            Scene.SHOP,
            Scene.STATION_DETAIL,
            Scene.UNKNOWN_WITH_NAVBAR,
        ):
            actions.append("safe_go_home")
            if not safe_go_home():
                input_back()
                actions.append("input_back")
            time.sleep(1.0)
            continue

        actions.append("escape_unknown")
        if attempt % 4 == 0:
            capture_debug_snapshot(reason=f"{context.step}:unknown_scene")
        input_back()
        time.sleep(0.8)
        input_tap((83, 36))
        time.sleep(0.8)

    snapshot = capture_debug_snapshot(reason=f"{context.step}:recovery_failed")
    return RecoveryResult(
        ok=False,
        state=inspect_current_state(),
        reason="recovery attempts exceeded",
        attempts=context.max_attempts,
        snapshot=snapshot.get("screenshot"),
        actions=actions,
    )


def takeover_to_station(allow_travel: bool = True) -> Optional[str]:
    time.sleep(2.0)
    result = recover_to_expected(
        RecoveryContext(
            step="STARTUP_TAKEOVER",
            expected_scenes={Scene.MAIN_MAP, Scene.CITY_VIEW},
            allow_travel=allow_travel,
            max_attempts=16,
        )
    )
    if result.ok and result.state:
        city = result.state.city or identify_city()
        if city:
            return city
        fallback = app.RunBuy.BuyCity or app.RunBuy.SellCity
        if fallback:
            logger.warning(f"城市识别失败，使用备用城市: {fallback}")
            return fallback
    return None


def wait_or_recover_travel(target_city: str, current_city: Optional[str] = None) -> bool:
    from resonance.solvers.navigation import click_station, travel_monitor

    if travel_monitor():
        city = takeover_to_station(allow_travel=True)
        return city is None or city == target_city

    capture_debug_snapshot(reason=f"TRAVEL_TO_{target_city}:monitor_failed")
    restart_game()
    time.sleep(5.0)

    city = takeover_to_station(allow_travel=True)
    if city == target_city:
        logger.info(f"恢复流程：已在目标城市 {target_city}")
        return True
    if not city:
        logger.error("恢复流程：行车恢复后无法识别城市")
        return False

    logger.info(f"恢复流程：当前 {city}，重新前往 {target_city}")
    result = click_station(target_city, cur_station=city or current_city)
    if not result.ok:
        return False
    if result.is_destine:
        return True
    return travel_monitor()


def skip_travel_by_returning_main(target_city: str) -> bool:
    """Debug page-flow helper: return from station detail and treat travel as complete."""
    if not safe_go_home():
        capture_debug_snapshot(reason=f"SKIP_TRAVEL:{target_city}:safe_go_home_failed")
        return False

    result = recover_to_expected(
        RecoveryContext(
            step=f"SKIP_TRAVEL:{target_city}:MAIN_MAP",
            expected_scenes={Scene.MAIN_MAP},
            target_city=target_city,
            allow_travel=False,
            max_attempts=6,
        )
    )
    if not result.ok:
        logger.error(f"跳过跑车回主界面失败: target={target_city}, reason={result.reason}")
        return False
    logger.info(f"跳过跑车：已回主界面，视为到达 {target_city}")
    return True
