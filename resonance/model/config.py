import json
from pathlib import Path
from typing import Dict, List

from loguru import logger
from pydantic import BaseModel

from resonance.utils.utils import ROOT_PATH

CONFIG_PATH = ROOT_PATH / "config" / "config.json"
CONFIG_PATH.parent.exists() or CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


class RunTimeModel(BaseModel):
    runtime: float = 0.0


class RestAreaModel(BaseModel):
    huashi: RunTimeModel = RunTimeModel()


class RSBModel(BaseModel):
    city: str = "7号自由港"
    levelSerialPos: List[int] = [635, 662]
    name: str = "所有"
    num: int = 1


class GlobalConfigModel(BaseModel):
    is_transit_assist: bool = False
    is_auto_pick: bool = False
    is_exit_on_failure: bool = False
    is_exit_on_fatigue: bool = False
    use_stamina_item: bool = False
    on_stop_action: str = "stay_there"


class Config(BaseModel):
    version: str = "1.0.0"
    rsb: RSBModel = RSBModel()
    rest_area: RestAreaModel = RestAreaModel()
    global_config: GlobalConfigModel = GlobalConfigModel()

    def save_config(self):
        try:
            str_data = self.model_dump_json(indent=4, by_alias=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(str_data)
        except (AttributeError, TypeError, ValueError, PermissionError):
            logger.exception(f"保存配置文件失败，请检查是否有权限读取和写入 {CONFIG_PATH}")
            raise
        else:
            logger.info(f"配置文件 {CONFIG_PATH} 已保存。")


if CONFIG_PATH.exists() and CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    config = Config.model_validate(data)
else:
    config = Config()
    try:
        str_data = config.model_dump_json(indent=4)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(str_data)
    except (AttributeError, TypeError, ValueError, PermissionError):
        logger.exception(f"创建配置文件失败，请检查是否有权限读取和写入 {CONFIG_PATH}")
        raise
    else:
        logger.info(f"配置文件 {CONFIG_PATH} 不存在，已创建默认插件配置文件。")
