"""运行时配置模型：设备配置、跑商配置、全局状态。

  主模型 Config 包含：
    Global — 设备端口、截图/触控方式
    RunBuy — 跑商城市、环线列表、运行次数
    CityHaggle / CityBook — 各城市议价次数和进货书数量
  通过 config/app.json 持久化。
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field

from resonance.device.port_scanner import EmulatorInfo, EmulatorType
from resonance.utils.utils import ROOT_PATH, read_json

APP_PATH = ROOT_PATH / "config" / "app.json"
APP_PATH.parent.mkdir(parents=True, exist_ok=True)
city_sell_data: Dict[str, Dict[str, int]] = read_json(
    ROOT_PATH / "resources" / "goods" / "CityGoodsSellData.json"
)
CITYS = list(city_sell_data.keys())


class TouchMethod(str, Enum):
    ADB = "adb"
    NEMU = "nemu"
    SCRCPY = "scrcpy"


class ScreenshotMethod(str, Enum):
    ADB = "adb"
    NEMU = "nemu"
    DROIDCAST = "droidcast"
    SCRCPY = "scrcpy"


class GlobalModel(BaseModel):
    device: EmulatorInfo = EmulatorInfo(
        name="自定义端口", port=16384, path="", type=EmulatorType.CUSTOM, index=0
    )
    touch_method: TouchMethod = TouchMethod.ADB
    screenshot_method: ScreenshotMethod = ScreenshotMethod.ADB
    mirrorCdk: str = ""


class RunBuyModel(BaseModel):
    BuyCount: int = 0
    BuyCity: str = ""
    SellCity: str = ""
    LoopCities: List[str] = []


class Config(BaseModel):
    Global: GlobalModel = GlobalModel()
    CityBook: dict = Field(default_factory=lambda: {city: 0 for city in CITYS})
    CityHaggle: dict = Field(default_factory=lambda: {city: 0 for city in CITYS})
    RunBuy: RunBuyModel = RunBuyModel()

    def save_config(self):
        from resonance.utils.utils import save_json
        existing = read_json(APP_PATH, {})
        data = self.model_dump(mode="json")
        if isinstance(existing, dict):
            data = {**existing, **data}
            if isinstance(existing.get("Global"), dict):
                data["Global"] = {**existing["Global"], **data["Global"]}
        save_json(APP_PATH, data)


if APP_PATH.exists() and APP_PATH.is_file():
    data = read_json(APP_PATH)
    app = Config.model_validate(data)
else:
    app = Config()
    from resonance.utils.utils import save_json
    save_json(APP_PATH, app.model_dump(mode="json"))
