"""商品数据模型：单商品（GoodModel）和商品集合（GoodsModel）。

  从 CityGoodsSellData.json 加载，包含价格、类别等属性。
  支持价格排序、分类筛选。
"""

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from pydantic import BaseModel, RootModel

from .city_data import city_goods


class GoodModel(BaseModel):
    name: str
    city: str
    type: str
    num: int = 0
    price: int
    profit: int = 0
    base_price: int
    isSpeciality: bool = False

    def __init__(self, **data: Any) -> None:
        if "station" in data:
            data["city"] = data.pop("station")
        super().__init__(**data)


class GoodInfoModel(BaseModel):
    name: str
    buy_price: int
    sell_price: int
    profit: int
    buy_num: int


LACK_DATA = []


class GoodsModel(BaseModel):
    goods: List[GoodModel]
    buy_goods: Dict[str, Dict[str, GoodModel]] = {}
    sell_goods: Dict[str, Dict[str, GoodModel]] = {}
    speciality_goods: Dict[str, Dict[str, GoodModel]] = {}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.set_goods()

    def set_goods(self) -> None:
        for good in self.goods:
            if good.city not in city_goods:
                if good.city not in LACK_DATA:
                    LACK_DATA.append(good.city)
                    logger.error(f"{good.city} 数据不存在")
                continue
            if good.type == "buy":
                if good.name in city_goods[good.city]:
                    city_good_data = city_goods[good.city][good.name]
                    good.num = city_good_data.num
                    good.isSpeciality = city_good_data.isSpeciality
                    self.buy_goods.setdefault(good.city, {}).setdefault(good.name, good)
                    if city_good_data.isSpeciality:
                        self.speciality_goods.setdefault(good.city, {}).setdefault(good.name, good)
                else:
                    logger.error(f"{good.city}不存在{good.name}")
            elif good.type == "sell":
                self.sell_goods.setdefault(good.city, {}).setdefault(good.name, good)

    def find(self, **kargs) -> List[GoodModel]:
        data = []
        for i in self.goods:
            if all(getattr(i, key) == value for key, value in kargs.items()):
                data.append(i)
        return data
