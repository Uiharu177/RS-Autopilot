"""城市商品配置：从 JSON 文件加载各城市的可购买商品列表。
"""

from typing import Dict

from pydantic import BaseModel, RootModel

from resonance.utils.utils import ROOT_PATH, read_json

GOODSDATA_PATH = ROOT_PATH / "resources" / "goods" / "CityGoodsData.json"
goods_data = read_json(GOODSDATA_PATH)


class CityGoodsDataModel(BaseModel):
    isSpeciality: bool
    num: int


class CityGoodsModel(RootModel):
    root: Dict[str, Dict[str, CityGoodsDataModel]]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]


city_goods = CityGoodsModel.model_validate(goods_data)
