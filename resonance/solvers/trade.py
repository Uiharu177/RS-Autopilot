"""跑商编排：端点模式 / 环线模式的完整跑商自动化。

  TradeRouteSolver 是 BaseSolver 子类，编排以下流程：
  1. ensure_connected() → boot_game()（统一启动入口）
  2. takeover_current_city() → recovery.takeover_to_station()（接管到当前城市）
  3. normalize_takeover_city() → 如不在环线则归位（不计轮次）
  4. 循环 N 轮：导航到买货城市→交易所买→导航到卖货城市→交易所卖
  5. _execute_on_stop_action() → 按 on_stop_action 配置执行后置动作

  支持端点（2 城往返）和环线（N 城循环）两种模式。
  互斥锁 _trade_route_lock 防止并发执行。
"""

import time
import threading
from typing import Any, Optional

from loguru import logger

from resonance.device import device as device_state
from resonance.device.device import get_device, input_tap, screenshot, screenshot_image
from resonance.model import app
from resonance.model.city_goods import RouteModel, RoutesModel
from resonance.model.config import config
from resonance.solver.base import BaseSolver
from resonance.solvers.city import identify_city_from_current_screen, is_city_view, _pick_city_name
from resonance.solvers.exchange import enter_exchange, leave_exchange, buy_goods, sell_goods
from resonance.solvers.strength import check_shop_strength as check_strength, use_strength
from resonance.solvers.recovery import skip_travel_by_returning_main, takeover_to_station, wait_or_recover_travel
from resonance.vision.ocr import predict
from resonance.solvers.navigation import click_station, open_station_detail, travel_monitor
from resonance.preset.control import click, go_home
from resonance.utils.utils import read_json, RESOURCES_PATH

_city_sell_data: Any = read_json(RESOURCES_PATH / "goods/CityGoodsSellData.json")
city_sell_data = {
    city: dict(sorted(goods.items(), key=lambda item: item[1]["price"], reverse=True))
    for city, goods in _city_sell_data.items()
}

_trade_route_lock = threading.Lock()


class TradeRouteSolver(BaseSolver):
    """Full trade route automation: buy → travel → sell → repeat.

    Supports both 2-city endpoint mode and N-city loop mode.
    - Endpoint: cities=["A", "B"] → A→B, B→A
    - Loop:     cities=["A", "B", "C", "D"] → A→B, B→C, C→D, D→A
    """

    solver_name = "跑商"

    def __init__(self, cities: Optional[list[str]] = None, buy_city: str = "", sell_city: str = ""):
        if cities and len(cities) >= 2:
            self.cities = list(cities)
        elif buy_city and sell_city:
            self.cities = [buy_city, sell_city]
        else:
            self.cities = []
        self.routes: Optional[RoutesModel] = None
        super().__init__()

    def _build_routes(self):
        routes = []
        n = len(self.cities)
        for i in range(n):
            buy = self.cities[i]
            sell = self.cities[(i + 1) % n]
            haggle = app.CityHaggle.get(buy, 0)
            book = app.CityBook.get(buy, 0)
            routes.append(RouteModel(
                buy_city_name=buy,
                sell_city_name=sell,
                haggle_num=haggle,
                book=book,
                goods_data=city_sell_data.get(buy, {}),
            ))
        self.routes = RoutesModel(city_data=routes)

    def _route_for_city(self, buy_city: str, sell_city: str) -> Optional[RouteModel]:
        goods = city_sell_data.get(buy_city)
        if not goods:
            logger.error(f"未找到 {buy_city} 商品配置")
            return None
        return RouteModel(
            buy_city_name=buy_city,
            sell_city_name=sell_city,
            haggle_num=app.CityHaggle.get(buy_city, 0),
            book=app.CityBook.get(buy_city, 0),
            goods_data=goods,
        )

    def ensure_connected(self) -> Optional[str]:
        from resonance.solvers.boot import boot_game
        return boot_game()

    def _takeover_current_city(self) -> Optional[str]:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                city_name = takeover_to_station()
                if not city_name:
                    raise ValueError("未识别到当前城市")
                return city_name
            except (ValueError, RuntimeError) as e:
                logger.error(f"无法确定当前城市 ({attempt+1}/{max_attempts}): {e}")
                if attempt == max_attempts - 1:
                    return None
                time.sleep(2)
        return None

    def _check_strength_and_use(self) -> bool:
        if check_strength():
            logger.debug("体力检查通过")
            return True

        logger.warning(f"体力不足: use_stamina_item={config.global_config.use_stamina_item}, is_exit_on_fatigue={config.global_config.is_exit_on_fatigue}")

        if config.global_config.use_stamina_item:
            logger.info("尝试使用体力药")
            click((974, 32))
            if use_strength():
                logger.info("使用体力药成功")
                return True
            logger.error("使用体力药失败")

        if config.global_config.is_exit_on_fatigue:
            logger.warning("疲劳保护触发，停止脚本")
            device_state.STOP = True
            return False

        logger.warning("体力不足但未启用体力药和疲劳保护，继续执行（可能无法议价）")
        return True

    def _sell_current_goods(self, haggle_num: int) -> bool:
        if not enter_exchange("sell"):
            return False
        if not self._check_strength_and_use():
            return False
        return sell_goods(haggle_num)

    def _buy_current_city_goods(self, route: RouteModel) -> bool:
        if not enter_exchange("buy"):
            return False
        if not self._check_strength_and_use():
            return False
        goods_data = list(route.goods_data.keys())
        if not buy_goods(goods_data[:1], goods_data[1:], route.haggle_num, book=route.book):
            return False
        return leave_exchange()

    def _travel_to_city(self, target_city: str, current_city: str) -> bool:
        result = click_station(target_city, cur_station=current_city)
        if not result.ok:
            return False
        if result.is_destine:
            return True
        return wait_or_recover_travel(target_city, current_city)

    def _normalize_takeover_city(self, city_name: str) -> Optional[str]:
        """Route to loop entry: if city is in loop, start from there; otherwise cargo to first city."""
        if city_name in self.cities:
            logger.info(f"{city_name} 在环线中，先清空车厢")
            self._sell_current_goods(0)
            return city_name

        target = self.cities[0]
        logger.info(f"{city_name} 不在环线，归位至 {target}")
        route = self._route_for_city(city_name, target)
        if route is None:
            return None

        logger.info(f"归位：{city_name} 卖货")
        if not self._sell_current_goods(0):
            return None

        logger.info(f"归位：{city_name} 买货")
        if not self._buy_current_city_goods(route):
            return None

        logger.info(f"归位：{city_name}->{target}")
        if not self._travel_to_city(target, city_name):
            return None

        logger.info(f"归位：到达 {target}，卖出")
        if not self._sell_current_goods(route.haggle_num):
            return None

        logger.info(f"归位完成，从 {target} 开始（归位段不计次数）")
        return target

    def _identify_city(self):
        city = identify_city_from_current_screen()
        if city:
            return city
        input_tap((1170, 493))
        time.sleep(1.0)
        res = predict(screenshot_image(), cropped_pos1=(166, 370), cropped_pos2=(470, 450))
        city = _pick_city_name(res)
        if not city:
            raise ValueError("未识别到当前城市")
        logger.info(f"当前站点: {city}")
        return city

    def _identify_from_city_view(self):
        city = identify_city_from_current_screen()
        if city:
            return city
        return None

    def _ensure_at_station(self):
        is_main = screenshot().match_template(RESOURCES_PATH / "scene/main_map.png", 0.75)
        is_city = is_city_view()
        frame = screenshot_image()
        results = predict(frame)
        has_arrive = any("访问城市" in r["text"] or "访问地区" in r["text"] for r in results)
        has_cruise = any("自动巡航中" in r["text"] for r in results)
        has_battle = any(r["text"] in ("弃牌", "max", "MAX") for r in results)
        has_travel = any("目的地" in r["text"] or "剩余行程" in r["text"] for r in results)

        if has_arrive:
            logger.info("到站 → 点击访问城市")
            clicked = False
            for r in results:
                if "访问城市" in r["text"] or "访问地区" in r["text"]:
                    cx = int((r["position"][0][0] + r["position"][2][0]) / 2)
                    cy = int((r["position"][0][1] + r["position"][2][1]) / 2)
                    if not (1100 <= cx <= 1245 and 430 <= cy <= 560):
                        logger.debug(f"忽略非进城入口访问城市文本: {(cx, cy)}")
                        continue
                    device = get_device()
                    device.input_tap(int(device.ratio * cx), int(device.ratio * cy))
                    clicked = True
                    break
            if clicked:
                time.sleep(2)
                return self._identify_city()
            logger.info("未检测到右下访问城市入口，忽略任务栏访问城市文本")

        if has_travel or has_cruise or has_battle:
            logger.info("列车在途，等待到站")
            if not travel_monitor():
                raise RuntimeError("列车到站超时")
            time.sleep(2)
            return self._identify_city()

        if is_main:
            logger.info("已到主界面")
            return self._identify_city()

        if is_city:
            logger.info("已在城市界面，直接识别城市")
            name = self._identify_from_city_view()
            if name:
                logger.info(f"当前站点: {name}")
                return name

        go_home()
        return self._identify_city()

    def _run_one_round(self, round_index: int, total_rounds: int, start_city: Optional[str] = None) -> Optional[str]:
        """Execute one complete round (all legs of the loop)."""
        n = len(self.cities)
        mode = "环线" if n > 2 else "端点"
        logger.info(f"开始第 {round_index}/{total_rounds} 轮{mode}跑商")

        city_name = start_city or self._takeover_current_city()
        if not city_name:
            return None

        if not self.routes:
            self._build_routes()

        # Rotate so current city is the first leg's buy_city
        for idx, leg in enumerate(self.routes.city_data):
            if leg.buy_city_name == city_name:
                if idx > 0:
                    self.routes.city_data = self.routes.city_data[idx:] + self.routes.city_data[:idx]
                break

        for i, city in enumerate(self.routes.city_data):
            logger.info(f"{city.buy_city_name}->{city.sell_city_name}")
            if city_name == city.buy_city_name:
                logger.info(f"已在出发站点 {city.buy_city_name}，跳过导航确认")
            else:
                result = click_station(city.buy_city_name, cur_station=city_name)
                if not result.ok:
                    return None
                if not result.is_destine and not wait_or_recover_travel(city.buy_city_name, city_name):
                    return None
                city_name = city.buy_city_name

            if not enter_exchange("buy"):
                return None

            if not self._check_strength_and_use():
                return None

            goods_data = list(city.goods_data.keys())
            if not buy_goods(goods_data[:1], goods_data[1:], city.haggle_num, book=city.book):
                return None
            if not leave_exchange():
                return None

            result = click_station(city.sell_city_name, cur_station=city_name)
            if not result.ok:
                return None
            if not result.is_destine and not wait_or_recover_travel(city.sell_city_name, city_name):
                return None
            city_name = city.sell_city_name

            if not enter_exchange("sell"):
                return None

            if not self._check_strength_and_use():
                return None

            if not sell_goods(city.haggle_num):
                return None

        logger.info(f"第 {round_index}/{total_rounds} 轮{mode}跑商完成")
        return city_name

    def _run_one_round_page_flow(self, round_index: int, total_rounds: int) -> bool:
        """Debug flow: visit known pages in order, but do not start real travel."""
        n = len(self.cities)
        mode = "环线" if n > 2 else "端点"
        logger.info(f"开始第 {round_index}/{total_rounds} 轮{mode}跑商页面流程")

        city_name = takeover_to_station(allow_travel=False)
        if not city_name:
            logger.error("页面流程：未识别到当前城市")
            return False

        if not self.routes:
            self._build_routes()

        for idx, leg in enumerate(self.routes.city_data):
            if leg.buy_city_name == city_name:
                if idx > 0:
                    self.routes.city_data = self.routes.city_data[idx:] + self.routes.city_data[:idx]
                break

        for i, city in enumerate(self.routes.city_data):
            logger.info(f"页面流程：{city.buy_city_name}->{city.sell_city_name}")
            result = open_station_detail(city.buy_city_name, cur_station=city_name)
            if not result.ok:
                return False
            if not result.is_destine and not skip_travel_by_returning_main(city.buy_city_name):
                return False
            city_name = city.buy_city_name

            if not enter_exchange("buy"):
                return False

            if not self._check_strength_and_use():
                return False

            goods_data = list(city.goods_data.keys())
            if not buy_goods(goods_data[:1], goods_data[1:], city.haggle_num, book=city.book):
                return False
            if not leave_exchange():
                return False

            result = open_station_detail(city.sell_city_name, cur_station=city_name)
            if not result.ok:
                return False
            if not result.is_destine and not skip_travel_by_returning_main(city.sell_city_name):
                return False
            city_name = city.sell_city_name

            if not enter_exchange("sell"):
                return False

            if not self._check_strength_and_use():
                return False

            if not sell_goods(city.haggle_num):
                return False

        logger.info(f"第 {round_index}/{total_rounds} 轮{mode}跑商页面流程完成")
        return True

    def run_page_flow(self, rounds: int = 1) -> bool:
        """Run the debug page flow synchronously without real train travel."""
        if not _trade_route_lock.acquire(blocking=False):
            logger.error("已有跑商任务正在执行，页面流程不启动")
            return False
        try:
            return self._run_page_flow_locked(rounds)
        finally:
            _trade_route_lock.release()

    def _run_page_flow_locked(self, rounds: int = 1) -> bool:
        if not self.ensure_connected():
            return False
        if rounds <= 0:
            logger.info("页面流程轮数为 0，不启动")
            return True

        n = len(self.cities)
        mode = "环线" if n > 2 else "端点"
        logger.info(f"准备运行{mode}跑商页面流程，轮数: {rounds}")
        try:
            for round_index in range(1, rounds + 1):
                if device_state.STOP:
                    logger.info("收到停止信号，结束页面流程")
                    return True
                if not self._run_one_round_page_flow(round_index, rounds):
                    logger.error(f"第 {round_index}/{rounds} 轮{mode}跑商页面流程失败")
                    return False
            return True
        finally:
            self._execute_on_stop_action()

    def _cleanup_game(self):
        from resonance.device.adb import ADB
        adb_killer = ADB()
        port = app.Global.device.port
        if port:
            adb_killer.connect(port)
            adb_killer.device.shell("am force-stop com.hermes.goda")
            adb_killer.kill()

    def _execute_on_stop_action(self):
        action = config.global_config.on_stop_action
        if action == "close_game":
            logger.info("停止后动作：关闭游戏")
            self._cleanup_game()
        elif action == "goto_main":
            logger.info("停止后动作：返回主界面")
            from resonance.solvers.recovery import safe_go_home
            if not safe_go_home():
                logger.warning("返回主界面失败")
        else:
            if action != "stay_there":
                logger.warning(f"未知的 on_stop_action: {action}，默认停在原地")

    def transition(self):
        """Execute configured number of complete trade route round trips."""
        if not _trade_route_lock.acquire(blocking=False):
            logger.error("已有跑商任务正在执行，新任务不启动")
            return True
        try:
            return self._transition_locked()
        finally:
            _trade_route_lock.release()

    def _transition_locked(self):
        city_name = self.ensure_connected()
        if not city_name:
            return True

        count = app.RunBuy.BuyCount
        if count <= 0:
            logger.info("运行次数为 0，跑商不启动")
            return True

        n = len(self.cities)
        mode = "环线" if n > 2 else "端点"
        logger.info(f"准备运行{mode}跑商，运行次数: {count}，路线: {' → '.join(self.cities)}")

        if not self.routes:
            self._build_routes()

        normalized_city = self._normalize_takeover_city(city_name)
        if not normalized_city:
            logger.error("归位失败，结束跑商")
            return True

        try:
            for round_index in range(1, count + 1):
                if device_state.STOP:
                    logger.info("收到停止信号，结束跑商")
                    return True

                next_city = self._run_one_round(round_index, count, start_city=normalized_city)
                if not next_city:
                    logger.error(f"第 {round_index}/{count} 轮{mode}跑商失败")
                    return True
                normalized_city = next_city

            logger.info(f"{mode}跑商完成，共运行 {count} 轮")
            return True
        finally:
            self._execute_on_stop_action()
