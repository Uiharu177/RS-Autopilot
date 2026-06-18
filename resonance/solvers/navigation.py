"""地图导航模块：地图滑动、站点定位与居中、发车、行车监听。

  核心功能：
    click_station(city) — 完整导航流程：开地图→滑到目标站→居中→点详情→发车
    travel_monitor() — 行车监听直到到站或进入巡航
    go_city(city) — 从主界面进入进城入口
    center_station_on_map(name) — 将站点图标滑动到屏幕中央

  恢复机制：
    各入口处调用 _guard_for_navigation → 失败则 _recover_for_navigation → recovery.recover_to_expected
"""

import time
import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from loguru import logger

from resonance.device.adb import ADB
from resonance.device.device import input_back, input_swipe, input_swipe_hold, input_tap, screenshot, screenshot_image, wait_stopped
from resonance.model import app
from resonance.preset.control import blurry_ocr_click, click_image, go_home, ocr_click
from resonance.scene.recognizer import Recognizer
from resonance.scene.scene import Scene
from resonance.vision.ocr import merge_ocr_text, predict
from resonance.utils.utils import RESOURCES_PATH, read_json

# ── Station data ────────────────────────────────────

STATION_NAME2PNG: Dict[str, str] = read_json(RESOURCES_PATH / "stations/name2id.json")
STATION_POS_DATA: Dict[str, Tuple[int, int]] = read_json(RESOURCES_PATH / "goods/CityPosData.json")

CITY_OUTLET_MARKERS = (
    "交易所",
    "商会",
    "市集",
    "工会",
    "俱乐部",
    "铁安局",
    "市政厅",
    "奶茶店",
    "研究所",
    "休息区",
    "市场",
)


def _adb_tap(pos: Tuple[int, int]) -> bool:
    adb = ADB()
    try:
        if not adb.connect(app.Global.device.port):
            return False
        adb.device.shell(f"input tap {pos[0]} {pos[1]}")
        return True
    finally:
        adb.kill()


def _is_visit_city_entry(pos: Tuple[int, int]) -> bool:
    x, y = pos
    return 1100 <= x <= 1245 and 430 <= y <= 560


def _is_visit_city_text(text: str) -> bool:
    return "访问城市" in text or "访问地区" in text


COARSE_RESERVE_PX = 0.0
MAP_CENTER = (640, 360)
WORLD_TO_SCREEN = 1.5
DIRECT_STEP_PX = 430.0
MAP_SWIPE_GAIN = 1.0
FAST_RESPONSE_X = 0.96
FAST_RESPONSE_Y = 0.93
MAX_FAST_HAND_X = 300.0
MAX_FAST_HAND_Y = 220.0
COARSE_EXTRA_STEPS = 3
NUDGE_RESPONSE_X = 0.9
NUDGE_RESPONSE_Y = 0.9
MAX_NUDGE_HAND_X = 150.0
MAX_NUDGE_HAND_Y = 120.0
NUDGE_DEADZONE_PX = 35


# ── Result type ─────────────────────────────────────

@dataclass
class TravelResult:
    ok: bool = False
    is_destine: bool = False


@dataclass
class MapAnchor:
    name: str
    screen_x: int
    screen_y: int


@dataclass
class MapCalibration:
    world_per_px_x: float
    world_per_px_y: float
    center_world_x: float
    center_world_y: float


# ═══════════════════════════════════════════════════════
# 2.1  open_map
# ═══════════════════════════════════════════════════════

def open_map():
    go_home()
    time.sleep(0.3)
    input_tap((1201, 666))
    time.sleep(0.5)
    wait_stopped(threshold=7100000)
    recog = Recognizer()
    ocr_results = recog.ocr()
    return is_navigation_map_open(ocr_results) or is_station_detail_open(ocr_results=ocr_results)


def _ocr_results(cropped_pos1=(0, 0), cropped_pos2=(0, 0), ocr_results: Optional[list[dict]] = None) -> list[dict]:
    if ocr_results is not None:
        return ocr_results
    return predict(screenshot_image(), cropped_pos1=cropped_pos1, cropped_pos2=cropped_pos2)


def is_navigation_map_open(ocr_results: Optional[list[dict]] = None) -> bool:
    results = _ocr_results(ocr_results=ocr_results)
    _, text = merge_ocr_text(results)
    if "前往目的地" in text:
        return False
    return "图示" in text


def is_station_detail_open(name: Optional[str] = None, ocr_results: Optional[list[dict]] = None) -> bool:
    results = _ocr_results(cropped_pos1=(650, 90), cropped_pos2=(1280, 680), ocr_results=ocr_results)
    _, text = merge_ocr_text(results)
    if "前往目的地" not in text:
        return False
    detail_markers = ("路程", "推荐等级", "发展度", "声望")
    if name:
        return name in text
    return any(marker in text for marker in detail_markers)


def _brake_map():
    input_swipe((640, 300), (640, 300), swipe_time=800)
    wait_stopped(threshold=7100000)


def _is_target_central(loc: Tuple[int, int]) -> bool:
    x, y = loc
    return 196 <= x <= 1084 and 100 <= y <= 620


def _is_map_station_point(x: int, y: int) -> bool:
    return 196 <= x <= 1084 and 100 <= y < 620


def _find_station_template_on_map(name: str) -> Optional[Tuple[int, int]]:
    if name not in STATION_NAME2PNG:
        return None
    image = screenshot()
    image.crop_image((196, 100), (1084, 620))
    result = image.match_template(RESOURCES_PATH / "stations" / STATION_NAME2PNG[name], 0.95)
    if result and _is_map_station_point(*result.loc):
        return result.loc
    return None


def _known_station_observations(ocr_results: Optional[list[dict]] = None) -> list[MapAnchor]:
    observations: dict[str, MapAnchor] = {}

    image = screenshot()
    image.crop_image((196, 100), (1084, 620))
    for name, png in STATION_NAME2PNG.items():
        result = image.match_template(RESOURCES_PATH / "stations" / png, 0.95)
        if result and _is_map_station_point(*result.loc):
            observations[name] = MapAnchor(name, result.loc[0], result.loc[1])

    OCR_TO_ICON_DX = -176
    OCR_TO_ICON_DY = -27
    results = ocr_results if ocr_results is not None else predict(screenshot_image())
    for item in results:
        text = item["text"]
        matched_name = next((name for name in STATION_POS_DATA if name in text), None)
        if not matched_name or matched_name in observations:
            continue
        pos = item["position"]
        cx = int((pos[0][0] + pos[2][0]) / 2)
        cy = int((pos[0][1] + pos[2][1]) / 2)
        # 文字本身必须在地图区域内，排除 UI 列表
        if not _is_map_station_point(cx, cy):
            continue
        icon_x = cx + OCR_TO_ICON_DX
        icon_y = cy + OCR_TO_ICON_DY
        if _is_map_station_point(icon_x, icon_y):
            observations[matched_name] = MapAnchor(matched_name, icon_x, icon_y)

    return list(observations.values())


def _median(values: list[float]) -> Optional[float]:
    if not values:
        return None
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _calibrate_map_from_known_stations(ocr_results: Optional[list[dict]] = None) -> Optional[MapCalibration]:
    observations = _known_station_observations(ocr_results=ocr_results)
    if not observations:
        return None

    x_scales: list[float] = []
    y_scales: list[float] = []
    for i, a in enumerate(observations):
        aw = STATION_POS_DATA[a.name]
        for b in observations[i + 1:]:
            bw = STATION_POS_DATA[b.name]
            dsx = b.screen_x - a.screen_x
            dsy = b.screen_y - a.screen_y
            dwx = bw[0] - aw[0]
            dwy = bw[1] - aw[1]
            if abs(dsx) >= 80 and abs(dwx) >= 100:
                x_scales.append(abs(dwx / dsx))
            if abs(dsy) >= 60 and abs(dwy) >= 100:
                y_scales.append(abs(dwy / dsy))

    world_per_px_x = _median(x_scales) or WORLD_TO_SCREEN
    world_per_px_y = _median(y_scales) or world_per_px_x

    center_x_values = []
    center_y_values = []
    for obs in observations:
        world = STATION_POS_DATA[obs.name]
        center_x_values.append(world[0] - (obs.screen_x - MAP_CENTER[0]) * world_per_px_x)
        center_y_values.append(world[1] + (obs.screen_y - MAP_CENTER[1]) * world_per_px_y)

    center_world_x = _median(center_x_values)
    center_world_y = _median(center_y_values)
    if center_world_x is None or center_world_y is None:
        return None

    logger.info(f"地图标定: {len(observations)}点 center=({center_world_x:.1f},{center_world_y:.1f})")
    return MapCalibration(world_per_px_x, world_per_px_y, center_world_x, center_world_y)


def _swipe_calibrated_target_to_center(calibration: MapCalibration, target: str) -> bool:
    target_world = STATION_POS_DATA.get(target)
    if not target_world:
        return False

    target_screen_x = MAP_CENTER[0] + (target_world[0] - calibration.center_world_x) / calibration.world_per_px_x
    target_screen_y = MAP_CENTER[1] + (calibration.center_world_y - target_world[1]) / calibration.world_per_px_y
    move_dx = target_screen_x - MAP_CENTER[0]
    move_dy = target_screen_y - MAP_CENTER[1]
    dist = math.sqrt(move_dx**2 + move_dy**2)
    if dist < 40:
        return True

    steps = max(1, math.ceil(dist / DIRECT_STEP_PX))
    step_dx = move_dx / steps
    step_dy = move_dy / steps
    logger.info(f"投影导航: {target} steps={steps}")
    for step in range(steps):
        end_x, end_y = _clamp_map_swipe_start(MAP_CENTER[0] - step_dx, MAP_CENTER[1] - step_dy)
        logger.info(f"导航分步 {step + 1}/{steps}")
        input_swipe_hold(MAP_CENTER, (end_x, end_y), swipe_time=700, hold_ms=800)
        wait_stopped(threshold=7100000)
        _log_navigation_step_observation(step + 1, steps, target)

    target_loc = _find_station_template_on_map(target)
    if target_loc:
        if _is_target_central(target_loc):
            logger.info(f"{target} 已居中")
            return True
        _center_visible_target_once(target_loc)
        centered_loc = _find_station_template_on_map(target)
        if centered_loc and _is_target_central(centered_loc):
            logger.info(f"{target} 居中(微调后)")
            return True
    return False


def _coarse_swipe_from_anchor(anchor: MapAnchor, target: str) -> bool:
    anchor_world = STATION_POS_DATA.get(anchor.name)
    target_world = STATION_POS_DATA.get(target)
    if not anchor_world or not target_world:
        return False

    target_screen_x = anchor.screen_x + (target_world[0] - anchor_world[0]) / WORLD_TO_SCREEN
    target_screen_y = anchor.screen_y + (anchor_world[1] - target_world[1]) / WORLD_TO_SCREEN
    need_x = MAP_CENTER[0] - target_screen_x
    need_y = MAP_CENTER[1] - target_screen_y
    hand_x = need_x / FAST_RESPONSE_X
    hand_y = need_y / FAST_RESPONSE_Y

    steps = max(1, math.ceil(max(abs(hand_x) / MAX_FAST_HAND_X, abs(hand_y) / MAX_FAST_HAND_Y)))
    step_x = hand_x / steps
    step_y = hand_y / steps
    logger.info(f"粗滑导航: {anchor.name}->{target} steps={steps}")

    for step in range(steps):
        logger.info(f"粗滑分步 {step + 1}/{steps}")
        input_swipe_hold(
            MAP_CENTER,
            _clamp_map_swipe_start(MAP_CENTER[0] + step_x, MAP_CENTER[1] + step_y),
            swipe_time=750,
            hold_ms=900,
        )
        wait_stopped(threshold=7100000)

    loc = find_station_on_map(target)
    if loc:
        logger.info(f"粗滑结束: {target} loc={loc}")
        return True


def _clamp_map_swipe_start(x: float, y: float) -> Tuple[int, int]:
    if x > 1084: x = 1084
    if x < 196: x = 196
    if y > 620: y = 620
    if y < 100: y = 100
    return int(x), int(y)


def _project_target_from_anchor(anchor: MapAnchor, target: str) -> Optional[Tuple[float, float, float, float]]:
    anchor_world = STATION_POS_DATA.get(anchor.name)
    target_world = STATION_POS_DATA.get(target)
    if not anchor_world or not target_world:
        return None

    target_screen_x = anchor.screen_x + (target_world[0] - anchor_world[0]) / WORLD_TO_SCREEN
    target_screen_y = anchor.screen_y + (anchor_world[1] - target_world[1]) / WORLD_TO_SCREEN
    move_dx = target_screen_x - MAP_CENTER[0]
    move_dy = target_screen_y - MAP_CENTER[1]
    return target_screen_x, target_screen_y, move_dx, move_dy


def _log_navigation_step_observation(step: int, steps: int, target: str) -> None:
    target_loc = _find_station_template_on_map(target)
    visible_anchor = find_visible_station_on_map()
    try:
        ocr_results = Recognizer().ocr()
        texts = [item["text"] for item in ocr_results]
    except Exception as exc:
        logger.warning(f"投影导航观测 {step}/{steps}: OCR失败: {exc}")
        texts = []

    logger.info(
        f"投影导航观测 {step}/{steps}: target_loc={target_loc}, "
        f"central={bool(target_loc and _is_target_central(target_loc))}, "
        f"visible_anchor={visible_anchor}, ocr={texts}"
    )


def _swipe_projection_to_center(anchor: MapAnchor, target: str) -> bool:
    projection = _project_target_from_anchor(anchor, target)
    if projection is None:
        return False

    target_screen_x, target_screen_y, move_dx, move_dy = projection
    dist = math.sqrt(move_dx**2 + move_dy**2)
    if dist < 40:
        return True

    planned_dx = move_dx * MAP_SWIPE_GAIN
    planned_dy = move_dy * MAP_SWIPE_GAIN
    planned_dist = math.sqrt(planned_dx**2 + planned_dy**2)
    steps = max(1, math.ceil(planned_dist / DIRECT_STEP_PX))
    step_dx = planned_dx / steps
    step_dy = planned_dy / steps
    logger.info(
        f"已知站点投影: anchor={anchor.name}@({anchor.screen_x},{anchor.screen_y}) "
        f"target={target}理论屏幕=({int(target_screen_x)},{int(target_screen_y)}) "
        f"move=({int(move_dx)},{int(move_dy)}) gain={MAP_SWIPE_GAIN} steps={steps}"
    )

    for step in range(steps):
        end_x, end_y = _clamp_map_swipe_start(MAP_CENTER[0] - step_dx, MAP_CENTER[1] - step_dy)
        logger.info(f"投影分步 {step + 1}/{steps}")
        input_swipe_hold(MAP_CENTER, (end_x, end_y), swipe_time=700, hold_ms=800)
        wait_stopped(threshold=7100000)
        _log_navigation_step_observation(step + 1, steps, target)

    target_loc = _find_station_template_on_map(target)
    if target_loc:
        if _is_target_central(target_loc):
            logger.info(f"{target} 已居中")
            return True
        _center_visible_target_once(target_loc)
        centered_loc = _find_station_template_on_map(target)
        if centered_loc and _is_target_central(centered_loc):
            logger.info(f"{target} 居中(微调后)")
            return True
    return False


def _center_visible_target_once(loc: Tuple[int, int]) -> bool:
    x, y = loc
    if _is_target_central(loc):
        return True

    dx = x - 640
    dy = y - 360
    if abs(dx) < 40 and abs(dy) < 40:
        return True

    move_x = max(-360, min(360, dx * 0.85))
    move_y = max(-260, min(260, dy * 0.85))
    end_x = 640 - move_x
    end_y = 360 - move_y

    if end_x > 1084: end_x = 1084
    if end_x < 196: end_x = 196
    if end_y > 620: end_y = 620
    if end_y < 100: end_y = 100

    logger.info(f"偏离中心，微调滑动: ({x},{y})->({int(end_x)},{int(end_y)})")
    input_swipe_hold((640, 360), (end_x, end_y), swipe_time=500, hold_ms=700)
    wait_stopped(threshold=7100000)
    return False


def nudge_station_to_point(
    name: str,
    target_pos: Tuple[int, int] = MAP_CENTER,
    max_steps: int = 4,
    deadzone: int = NUDGE_DEADZONE_PX,
) -> bool:
    """Precise visible-station movement helper for calibration/tests.

    Formal coarse navigation does not use this for every step. Keep it as a
    reusable utility for testing future points or precisely moving a visible
    station to a desired screen position.
    """
    for step in range(max_steps):
        loc = find_station_on_map(name)
        if not loc:
            logger.info(f"精确矫正: 未找到可见站点 {name}")
            return False

        dx = target_pos[0] - loc[0]
        dy = target_pos[1] - loc[1]
        if abs(dx) <= deadzone and abs(dy) <= deadzone:
            logger.info(f"精确矫正: {name} 已到目标区域 loc={loc}, target={target_pos}")
            return True

        hand_x = max(-MAX_NUDGE_HAND_X, min(MAX_NUDGE_HAND_X, dx / NUDGE_RESPONSE_X))
        hand_y = max(-MAX_NUDGE_HAND_Y, min(MAX_NUDGE_HAND_Y, dy / NUDGE_RESPONSE_Y))
        end = _clamp_map_swipe_start(MAP_CENTER[0] + hand_x, MAP_CENTER[1] + hand_y)
        logger.info(
            f"精确矫正 {name} [{step + 1}/{max_steps}]: loc={loc}, target={target_pos}, "
            f"hand=({int(hand_x)},{int(hand_y)}), end={end}"
        )
        input_swipe_hold(MAP_CENTER, end, swipe_time=600, hold_ms=800)
        wait_stopped(threshold=7100000)

    loc = find_station_on_map(name)
    return bool(loc and abs(target_pos[0] - loc[0]) <= deadzone and abs(target_pos[1] - loc[1]) <= deadzone)


# ═══════════════════════════════════════════════════════
# 2.3  swipe_to_target
# ═══════════════════════════════════════════════════════

def swipe_to_target(from_city: str, to_city: str) -> bool:
    target_world = STATION_POS_DATA.get(to_city)
    if not target_world:
        logger.error(f"无 {to_city} 的坐标信息")
        return False

    guard_recog = Recognizer()
    guard_ocr = guard_recog.ocr()
    if not is_navigation_map_open(guard_ocr):
        logger.warning("当前不在地图页，尝试重新打开地图")
        if not open_map():
            logger.error("无法进入地图页，取消地图滑动")
            return False

    target_loc = _find_station_template_on_map(to_city)
    if target_loc:
        if _is_target_central(target_loc):
            logger.info(f"{to_city} 已居中")
            return True
        _center_visible_target_once(target_loc)
        centered_loc = _find_station_template_on_map(to_city)
        if centered_loc and _is_target_central(centered_loc):
            logger.info(f"{to_city} 居中(微调后)")
            return True

    logger.info(f"已知站点导航开始: current_hint={from_city} -> {to_city} (目标: {target_world})")
    observations = _known_station_observations(ocr_results=guard_ocr)
    if observations:
        anchor = min(observations, key=lambda obs: abs(obs.screen_x - MAP_CENTER[0]) + abs(obs.screen_y - MAP_CENTER[1]))
        if _coarse_swipe_from_anchor(anchor, to_city):
            return True

    calibration = _calibrate_map_from_known_stations(ocr_results=guard_ocr)
    if calibration and _swipe_calibrated_target_to_center(calibration, to_city):
        return True

    anchor_tuple = find_visible_station_on_map(ocr_results=guard_ocr)
    if anchor_tuple:
        anchor = MapAnchor(anchor_tuple[0], anchor_tuple[1], anchor_tuple[2])
        if _swipe_projection_to_center(anchor, to_city):
            return True

    logger.info("当前画面未能通过投影确认目标，短搜索已知站点锚点")
    search_dirs = ((180, 0), (-180, 0), (0, 150), (0, -150), (180, 120), (-180, -120))
    for step, (dx, dy) in enumerate(search_dirs, start=1):
        wait_stopped(threshold=7100000)

        target_loc = _find_station_template_on_map(to_city)
        if target_loc:
            if _is_target_central(target_loc):
                logger.info(f"短搜索第 {step} 步：目标 {to_city} 已在中心区 {target_loc}")
                return True
            _center_visible_target_once(target_loc)
            centered_loc = _find_station_template_on_map(to_city)
            if centered_loc and _is_target_central(centered_loc):
                return True

        anchor_tuple = find_visible_station_on_map()
        if anchor_tuple:
            anchor = MapAnchor(anchor_tuple[0], anchor_tuple[1], anchor_tuple[2])
            if _swipe_projection_to_center(anchor, to_city):
                return True

        x1, y1 = _clamp_map_swipe_start(MAP_CENTER[0] + dx, MAP_CENTER[1] + dy)
        logger.info(f"短搜索第 {step} 步：未找到已知锚点，探测滑动起点({x1},{y1})")
        input_swipe_hold((x1, y1), MAP_CENTER, swipe_time=500, hold_ms=700)
        wait_stopped(threshold=7100000)

    final_loc = _find_station_template_on_map(to_city)
    return bool(final_loc and _is_target_central(final_loc))


def find_station_on_map(name: str, ocr_results: Optional[list[dict]] = None) -> Optional[Tuple[int, int]]:
    if name not in STATION_NAME2PNG:
        return None

    # 1. 优先 OCR 匹配（全图扫描）
    results = ocr_results if ocr_results is not None else predict(screenshot_image())

    # OCR 文字到图标的固定偏移（从修格里城校准得来）
    OCR_TO_ICON_DX = -176
    OCR_TO_ICON_DY = -27

    for item in results:
        if name in item["text"]:
            pos = item["position"]
            cx = int((pos[0][0] + pos[2][0]) / 2)
            cy = int((pos[0][1] + pos[2][1]) / 2)
            # 文字本身必须在地图区域内
            if not _is_map_station_point(cx, cy):
                continue
            icon_x = cx + OCR_TO_ICON_DX
            icon_y = cy + OCR_TO_ICON_DY
            if _is_map_station_point(icon_x, icon_y):
                return (icon_x, icon_y)
            continue

    # 尝试合并匹配（处理分词问题）
    _, compact = merge_ocr_text(results)
    if name in compact:
        first_char = name[0]
        for item in results:
            if first_char in item["text"]:
                pos = item["position"]
                cx = int((pos[0][0] + pos[2][0]) / 2)
                cy = int((pos[0][1] + pos[2][1]) / 2)
                if not _is_map_station_point(cx, cy):
                    continue
                icon_x = cx + OCR_TO_ICON_DX
                icon_y = cy + OCR_TO_ICON_DY
                if _is_map_station_point(icon_x, icon_y):
                    return (icon_x, icon_y)
                continue

    # 2. 模板匹配兜底
    image = screenshot()
    image.crop_image((196, 100), (1084, 620))
    result = image.match_template(RESOURCES_PATH / "stations" / STATION_NAME2PNG[name], 0.95)
    if result and _is_map_station_point(*result.loc):
        return result.loc

    return None


def center_station_on_map(name: str, ocr_results: Optional[list[dict]] = None) -> bool:
    max_attempts = 3
    for attempt in range(max_attempts):
        loc = find_station_on_map(name, ocr_results=ocr_results if attempt == 0 else None)
        if not loc:
            if attempt == 0:
                logger.info(f"未找到 {name}")
            else:
                logger.info(f"丢失 {name}")
            return False

        x, y = loc
        if _is_target_central(loc):
            logger.info(f"站点 {name} 已在点击安全区: ({x},{y})")
            return True

        dx = x - 640
        dy = y - 360
        if abs(dx) < 40 and abs(dy) < 40:
            logger.info(f"站点 {name} 已在中心区域: ({x},{y})")
            return True

        factor_x = 0.8
        factor_y = 0.8
        
        # 计算终点。起点固定在中心 640,360
        # 目标在右(dx>0)，我们要向左划(end_x < 640)
        move_x = max(-320, min(320, dx * factor_x))
        move_y = max(-240, min(240, dy * factor_y))
        end_x = 640 - move_x
        end_y = 360 - move_y
        
        # 终点 Clamp 到安全区，但尽量给够空间
        if end_x > 1084: end_x = 1084
        if end_x < 196: end_x = 196
        if end_y > 620: end_y = 620
        if end_y < 100: end_y = 100
        if end_x > 800 and end_y > 520: end_y = 520  # 右下角UI区域，避免滑动终点落在站点列表上

        logger.info(f"{name} 居中滑动 [{attempt+1}/{max_attempts}]")
        input_swipe_hold((640, 360), (end_x, end_y), swipe_time=500, hold_ms=700)
        wait_stopped(threshold=7100000)
        # 第一次滑动后必须重新 OCR
        ocr_results = None
    
    return False


def find_visible_station_on_map(ocr_results: Optional[list[dict]] = None) -> Optional[Tuple[str, int, int]]:
    """Scan current map for any known station closest to center.

    Navigation anchors must be known station templates. OCR text can be
    garbled or UI text, so it is intentionally not used as an anchor source.
    Returns: (name, x, y) or None
    """
    _ = ocr_results
    image = screenshot()
    image.crop_image((196, 100), (1084, 620))
    template_candidates = []
    for name, png in STATION_NAME2PNG.items():
        result = image.match_template(RESOURCES_PATH / "stations" / png, 0.95)
        if not result:
            continue
        x, y = result.loc
        dist = abs(x - 640) + abs(y - 360)
        template_candidates.append((name, x, y, dist))
    if template_candidates:
        best = min(template_candidates, key=lambda c: c[3])
        return (best[0], best[1], best[2])
    return None


def refine_navigation_by_visible_stations(target: str) -> bool:
    """Iteratively recalibrate position using visible stations until target is found."""
    max_jumps = 2
    for jump in range(max_jumps):
        # 每次跃迁前重新检测
        recog = Recognizer()
        ocr = recog.ocr()
        
        # 1. 如果能看到目标了，直接居中并退出
        if find_station_on_map(target, ocr_results=ocr):
            logger.info(f"重定位发现目标 {target}")
            return center_station_on_map(target, ocr_results=ocr)
            
        # 2. 找当前最接近中心的可见站作为基准
        visible = find_visible_station_on_map(ocr_results=ocr)
        if not visible:
            logger.warning(f"重定位第 {jump+1} 次尝试：地图上无可见站点")
            return False
            
        v_name, v_x, v_y = visible
        logger.info(f"重定位第 {jump+1} 次：以可见站 {v_name} 为基准滑向 {target}")
        
        # 3. 先居中这个可见站
        if not center_station_on_map(v_name, ocr_results=ocr):
            return False
            
        # 4. 从居中的可见站滑动到目标
        if not swipe_to_target(v_name, target):
            return False
            
    # 最后再试一次找目标
    return center_station_on_map(target)


# ═══════════════════════════════════════════════════════
# 2.4  tap_station
# ═══════════════════════════════════════════════════════

def tap_station(name: str, ocr_results: Optional[list[dict]] = None) -> bool:
    if name not in STATION_NAME2PNG:
        logger.error(f"未找到站点 {name} 的图片")
        return False

    # 1. 优先 OCR 匹配（只考虑地图区域内文本，排除 UI 列表）
    results = ocr_results if ocr_results is not None else predict(screenshot_image())
    for item in results:
        if name not in item["text"]:
            continue
        pos = item["position"]
        cx = int((pos[0][0] + pos[2][0]) / 2)
        cy = int((pos[0][1] + pos[2][1]) / 2)
        # 文字本身必须在地图区域内
        if not _is_map_station_point(cx, cy):
            continue
        input_tap((cx, cy))
        time.sleep(0.5)
        detail_recog = Recognizer()
        return is_station_detail_open(name, ocr_results=detail_recog.ocr())

    # 2. 模板匹配兜底
    image = screenshot()
    image.crop_image((196, 100), (1084, 620))
    result = image.match_template(RESOURCES_PATH / "stations" / STATION_NAME2PNG[name], 0.95)
    if result and _is_map_station_point(*result.loc):
        input_tap(result.loc)
        time.sleep(0.5)
        detail_recog = Recognizer()
        return is_station_detail_open(name, ocr_results=detail_recog.ocr())

    return False


def _dismiss_departure_reminder() -> bool:
    for _ in range(3):
        for item in predict(screenshot_image()):
            text = item["text"]
            if "立即出发" in text:
                pos = item["position"]
                cx = int((pos[0][0] + pos[2][0]) / 2)
                cy = int((pos[0][1] + pos[2][1]) / 2)
                logger.info(f"检测到出发提醒弹窗，先勾选本周不再提示，再点击立即出发")
                input_tap((900, 521))
                time.sleep(0.3)
                input_tap((cx, cy))
                time.sleep(1.0)
                return True
        time.sleep(1.0)
    return False


# ═══════════════════════════════════════════════════════
# 2.5  click_go_station
# ═══════════════════════════════════════════════════════

def click_go_station(target: Optional[str] = None, ocr_results: Optional[list[dict]] = None) -> bool:
    logger.info("点击前往目的地按钮")
    results = ocr_results
    if results is None:
        results = Recognizer().ocr()
    if not is_station_detail_open(target, ocr_results=results):
        logger.warning("未检测到目标站点详情，取消点击前往目的地按钮")
        return False
    if not click_image(
        RESOURCES_PATH / "map/go_station.png",
        cropped_pos1=(937, 605),
        cropped_pos2=(1218, 679),
        trynum=5,
    ):
        return False

    time.sleep(1.0)
    _dismiss_departure_reminder()
    return True


def _capture_navigation_snapshot(reason: str, target: str):
    try:
        from resonance.debug.snapshot import capture_debug_snapshot

        templates: list[str | dict] = [
            {"template": "map/go_station.png", "threshold": 0.8},
            {"template": "scene/main_map.png", "threshold": 0.96},
        ]
        if target in STATION_NAME2PNG:
            templates.append({"template": f"stations/{STATION_NAME2PNG[target]}", "threshold": 0.95})
        return capture_debug_snapshot(templates=templates, reason=f"NAVIGATION:{target}:{reason}")
    except Exception as exc:
        logger.warning(f"导航纠错快照失败: {exc}")
        return None


def _recover_for_navigation(step: str, target: str) -> bool:
    try:
        from resonance.solvers.recovery import RecoveryContext, recover_to_expected

        result = recover_to_expected(
            RecoveryContext(
                step=f"NAVIGATION:{target}:{step}",
                expected_scenes={Scene.MAIN_MAP, Scene.CITY_VIEW},
                target_city=target,
                allow_travel=True,
                max_attempts=12,
            )
        )
        if not result.ok:
            logger.error(f"导航纠错失败: target={target}, step={step}, reason={result.reason}")
            return False
        return True
    except Exception as exc:
        logger.exception(f"导航纠错异常: target={target}, step={step}, error={exc}")
        _capture_navigation_snapshot(f"recovery_exception:{step}", target)
        return False


def _guard_for_navigation(step: str, target: str) -> bool:
    """Lightweight guard before map navigation; full recovery only on unusable pages."""
    scene = Recognizer().scene
    usable = {
        Scene.MAIN_MAP,
        Scene.CITY_VIEW,
        Scene.STATION_LIST,
        Scene.STATION_DETAIL,
    }
    if scene in usable:
        logger.debug(f"导航入口轻量放行: target={target}, step={step}, scene={scene.name}")
        return True

    if scene in (Scene.EXCHANGE, Scene.EXCHANGE_BUY, Scene.EXCHANGE_SELL):
        from resonance.solvers.exchange import leave_exchange

        leave_exchange()
        scene = Recognizer().scene
        if scene in usable:
            logger.info(f"导航入口交易所leave: target={target}, step={step}")
            return True
        logger.warning(f"导航入口交易所leave后未到主界面, 进入重恢复: scene={scene.name}")

    logger.info(f"导航入口需要恢复: target={target}, step={step}, scene={scene.name}")
    return _recover_for_navigation(step, target)


# ═══════════════════════════════════════════════════════
# 2.1~2.5  click_station（组合入口）
# ═══════════════════════════════════════════════════════

def click_station(name: str, cur_station: Optional[str] = None) -> TravelResult:
    logger.info(f"点击站点 => {name}")
    if not _guard_for_navigation("before_open_map", name):
        return TravelResult(ok=False)

    detail_recog = Recognizer()
    detail_ocr_results = detail_recog.ocr()
    if is_station_detail_open(name, ocr_results=detail_ocr_results):
        logger.info(f"已在目标站点详情，直接点击前往目的地: {name}")
        if not click_go_station(name, ocr_results=detail_ocr_results):
            _capture_navigation_snapshot("click_go_station_from_existing_detail_failed", name)
            return TravelResult(ok=False)
        time.sleep(5.0)
        return TravelResult(ok=True)

    if not cur_station:
        station = get_station(is_go_home=False)
    else:
        station = cur_station

    if name == station:
        logger.info("已在目标站点")
        return TravelResult(ok=True, is_destine=True)

    if name not in STATION_NAME2PNG:
        logger.error(f"未找到站点 {name} 的图片")
        _capture_navigation_snapshot("missing_station_template", name)
        return TravelResult(ok=False)

    if not open_map():
        _capture_navigation_snapshot("open_map_failed", name)
        return TravelResult(ok=False)
    if not swipe_to_target(station, name):
        _capture_navigation_snapshot("swipe_failed", name)
        return TravelResult(ok=False)
    map_recog = Recognizer()
    map_ocr_results = map_recog.ocr()
    safe_loc = find_station_on_map(name, ocr_results=map_ocr_results)
    if safe_loc and _is_target_central(safe_loc):
        logger.info(f"{name} 已居中，点击")
    elif not center_station_on_map(name, ocr_results=map_ocr_results):
        logger.info(f"{name} 未居中，锚点重定位")
        if not refine_navigation_by_visible_stations(name):
            _capture_navigation_snapshot("station_not_found_after_swipe", name)
        map_ocr_results = None
    else:
        map_ocr_results = None
    
    if not tap_station(name, ocr_results=map_ocr_results):
        _capture_navigation_snapshot("tap_station_failed", name)
        if not _recover_for_navigation("tap_station_failed", name):
            return TravelResult(ok=False)
        station = get_station(is_go_home=False)
        if name == station:
            logger.info("纠错后已在目标站点")
            return TravelResult(ok=True, is_destine=True)
        if not open_map():
            _capture_navigation_snapshot("retry_open_map_failed", name)
            return TravelResult(ok=False)
        if not swipe_to_target(station, name):
            _capture_navigation_snapshot("retry_swipe_failed", name)
            return TravelResult(ok=False)
        retry_map_recog = Recognizer()
        retry_map_ocr_results = retry_map_recog.ocr()
        center_station_on_map(name, ocr_results=retry_map_ocr_results)
        if not tap_station(name, ocr_results=retry_map_ocr_results):
            _capture_navigation_snapshot("retry_tap_station_failed", name)
            return TravelResult(ok=False)
    detail_recog = Recognizer()
    detail_ocr_results = detail_recog.ocr()
    if not click_go_station(name, ocr_results=detail_ocr_results):
        _capture_navigation_snapshot("click_go_station_failed", name)
        return TravelResult(ok=False)

    time.sleep(5.0)
    return TravelResult(ok=True)


def open_station_detail(name: str, cur_station: Optional[str] = None) -> TravelResult:
    """Open target station detail without clicking 'go station'."""
    logger.info(f"打开站点详情 => {name}")
    if not _guard_for_navigation("before_open_station_detail", name):
        return TravelResult(ok=False)

    detail_recog = Recognizer()
    if is_station_detail_open(name, ocr_results=detail_recog.ocr()):
        logger.info(f"已在目标站点详情，不点击前往目的地: {name}")
        return TravelResult(ok=True)

    if not cur_station:
        station = get_station(is_go_home=False)
    else:
        station = cur_station

    if name == station:
        logger.info("目标站点就是当前站点，跳过站点详情导航")
        return TravelResult(ok=True, is_destine=True)

    if name not in STATION_NAME2PNG:
        logger.error(f"未找到站点 {name} 的图片")
        _capture_navigation_snapshot("detail_missing_station_template", name)
        return TravelResult(ok=False)

    if not open_map():
        _capture_navigation_snapshot("detail_open_map_failed", name)
        return TravelResult(ok=False)
    if not swipe_to_target(station, name):
        _capture_navigation_snapshot("detail_swipe_failed", name)
        return TravelResult(ok=False)
    map_recog = Recognizer()
    map_ocr_results = map_recog.ocr()
    safe_loc = find_station_on_map(name, ocr_results=map_ocr_results)
    if safe_loc and _is_target_central(safe_loc):
        logger.info(f"{name} 已居中，点击")
    elif not center_station_on_map(name, ocr_results=map_ocr_results):
        logger.info(f"{name} 未居中，锚点重定位")
        if not refine_navigation_by_visible_stations(name):
            _capture_navigation_snapshot("detail_station_not_found_after_swipe", name)
        map_ocr_results = None
    else:
        map_ocr_results = None
    if not tap_station(name, ocr_results=map_ocr_results):
        _capture_navigation_snapshot("detail_tap_station_failed", name)
        return TravelResult(ok=False)

    detail_recog = Recognizer()
    if not is_station_detail_open(name, ocr_results=detail_recog.ocr()):
        _capture_navigation_snapshot("detail_not_open_after_tap", name)
        return TravelResult(ok=False)

    logger.info(f"已打开站点详情，不点击前往目的地: {name}")
    return TravelResult(ok=True)


# ═══════════════════════════════════════════════════════
# 2.7  travel_monitor
# ═══════════════════════════════════════════════════════

CHECK_INTERVAL = 3
MISS_LIMIT = 30
MAP_WAIT_TIME = 3000


def travel_monitor() -> bool:
    logger.info("进入行车监听（到站后自动回到主界面）")
    recog = Recognizer()
    start = time.perf_counter()
    state = "pre_cruise"
    miss_count = 0
    battle_ignored_logged = False

    while time.perf_counter() - start < MAP_WAIT_TIME:
        recog.update()
        current = recog.scene
        texts = recog.ocr()

        for item in texts:
            if "访问城市" not in item["text"]:
                continue
            position = item["position"]
            center_x = int((position[0][0] + position[2][0]) / 2)
            center_y = int((position[0][1] + position[2][1]) / 2)
            if _is_visit_city_entry((center_x, center_y)):
                logger.info("检测到访问城市按钮，已到达目标城市主页面")
                return True

        # 2.7.3 到站检测：从行车状态回到主地图即视为到站
        if state != "pre_cruise" and current == Scene.MAIN_MAP:
            logger.info("检测到主地图，到站")
            return True

        # 2.7.4 崩溃检测
        if state != "pre_cruise":
            if current in (Scene.UNKNOWN,):
                miss_count += 1
                if miss_count >= MISS_LIMIT:
                    logger.error(f"连续 {miss_count} 次未检测到有效状态，判定游戏崩溃")
                    return False
            else:
                miss_count = 0

        # 状态转换
        if state == "pre_cruise":
            if current == Scene.TRAVEL_CRUISE:
                logger.info("巡航开始")
                state = "cruise"
            elif current == Scene.TRAVEL_MAP:
                logger.info("检测到行驶界面")
                state = "travel"
        elif state == "travel":
            pass
        elif state == "cruise":
            if current == Scene.BATTLE_CARD:
                if not battle_ignored_logged:
                    logger.info("行车监听忽略战斗场景，继续等待到站")
                    battle_ignored_logged = True
            else:
                if battle_ignored_logged and current in (Scene.TRAVEL_CRUISE, Scene.TRAVEL_MAP):
                    logger.info("战斗场景已恢复到行车状态")
                battle_ignored_logged = False

        time.sleep(CHECK_INTERVAL)

    logger.error("行车超时")
    return False


# ═══════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════

def get_station(is_go_home: bool = True) -> str:
    go_home()
    input_tap((1170, 493))
    time.sleep(1.0)
    frame = screenshot_image()
    result = []
    for pos1, pos2 in (
        ((166, 370), (470, 450)),
        ((166, 520), (470, 600)),
    ):
        result = predict(frame, cropped_pos1=pos1, cropped_pos2=pos2)
        if result:
            break
    if len(result) == 0:
        raise ValueError("未识别到当前城市")
    logger.info(f"当前站点: {result[0]['text']}")
    if is_go_home:
        go_home()
    return result[0]["text"]


def go_city(max_attempts: int = 10) -> bool:
    for _ in range(max_attempts):
        if Recognizer().scene == Scene.CITY_VIEW:
            return True

        results = predict(screenshot_image())
        outlet_hits = sum(
            1
            for item in results
            if any(marker in item["text"] for marker in CITY_OUTLET_MARKERS)
        )
        if outlet_hits >= 2:
            return True

        image = screenshot()
        is_city = image.crop_image(
            cropped_pos1=(25, 634), cropped_pos2=(99, 707)
        ).match_template(RESOURCES_PATH / "scene/fame.png", 0.95)
        if is_city:
            return True

        clicked = False
        has_task_detail = False
        for item in results:
            text = item["text"]
            if any(marker in text for marker in ("推荐等级", "累计", "迎战", "报酬", "任务")):
                has_task_detail = True
            if not _is_visit_city_text(text):
                continue
            position = item["position"]
            center_x = int((position[0][0] + position[2][0]) / 2)
            center_y = int((position[0][1] + position[2][1]) / 2)
            if _is_visit_city_entry((center_x, center_y)):
                pos = (center_x, center_y)
                logger.info(f"检测到右下进城入口 {text}: {(center_x, center_y)}，点击 {pos}")
                input_tap(pos)
                clicked = True
                break
        if not clicked:
            logger.info("主界面未定位右下访问城市/访问地区入口")
        if not clicked and has_task_detail:
            input_back()
        time.sleep(2.0)
    logger.error("进入城市界面失败")
    return False


def go_outlets(name: str) -> bool:
    def ocr_click_outlet(text: str, log: bool = False):
        score = 0.30 if name == "交易所" else 0.45
        offset = 35 if name == "交易所" else 80
        return blurry_ocr_click(text, excursion_pos=(0, offset), log=log, score=score) or ocr_click(
            text, excursion_pos=(0, offset), log=log
        )

    outlet_names = [name]
    if name == "交易所":
        outlet_names.extend(["平交易所", "亚交易所", "交易所-武林市集"])

    def try_ocr_click(log: bool = False):
        for outlet_name in outlet_names:
            if result := ocr_click_outlet(outlet_name, log=log and outlet_name == outlet_names[-1]):
                return result
        return False

    if not go_city():
        return False
    logger.info(f"前往 => {name}")

    input_swipe((900, 260), (420, 560), swipe_time=700)
    time.sleep(0.5)
    if result := try_ocr_click():
        return result

    swipe_paths = [
        ((900, 260), (420, 560)),
        ((640, 260), (640, 610)),
        ((640, 610), (640, 260)),
        ((900, 360), (260, 360)),
        ((380, 360), (1020, 360)),
        ((910, 260), (360, 570)),
        ((370, 260), (920, 570)),
        ((920, 570), (360, 260)),
        ((360, 570), (920, 260)),
    ]
    for index, (start_pos, end_pos) in enumerate(swipe_paths):
        input_swipe(start_pos, end_pos, swipe_time=700)
        time.sleep(0.5)
        if result := try_ocr_click(log=index == len(swipe_paths) - 1):
            return result
    logger.error(f"未找到门店: {name}")
    return False
