"""跑商路线数据模型：单段路线（RouteModel）和多段路线（RoutesModel）。

  RouteModel — 一段买卖路线：buy_city → sell_city，含议价次数和进货书数量。
  RoutesModel — 多段路线容器（支持环线 N 段）。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, RootModel


class RouteModel(BaseModel):
    class GoodsData(BaseModel):
        num: int = 0
        buy_price: int = 0
        sell_price: int = 0
        profit: int = 0

    buy_city_name: str = ""
    sell_city_name: str = ""
    haggle_num: int = 0
    goods_data: Dict[str, GoodsData] = {}
    buy_goods: Dict[str, int] = {}
    buy_price: int = 0
    sell_price: int = 0
    city_tired: int = 999
    tired_profit: int = 0
    book_profit: int = 0
    book: int = -1
    num: int = 0


class RoutesModel(BaseModel):
    city_data: List[RouteModel] = [RouteModel(), RouteModel()]


class CityDataModel(BaseModel):
    buy_num: float = 0.0
    revenue: float = 0.0


class SkillLevelModel(BaseModel):
    星花: int = 0
    卡洛琳: int = 0
    伊尔: int = 0
    菲妮娅: int = 0
    叶珏: int = 0
    黛丝莉: int = 0
    阿知波: int = 0
    塞西尔: int = 0
    瓦伦汀: int = 0
    魇: int = 0
    奈弥: int = 0
    甘雅: int = 0
    艾略特: int = 0
    朱利安: int = 0
    瑞秋: int = 0
    山岚: int = 0
    卡莲: int = 0
    静流: int = 0
    雷火: int = 0
    狮鬃: int = 0
