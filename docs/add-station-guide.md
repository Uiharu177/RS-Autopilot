# 新增站点完整教程

## 一、需要修改的文件（9 个）

| # | 路径 | 加什么 | 备注 |
|---|------|--------|------|
| 1 | `resources/goods/CityGoodsSellData.json` | 城市 key → 商品 → 基础价 | 🤖 AI 抓取网站或提取截图 |
| 2 | `resources/goods/CityGoodsData.json` | 城市 key → 商品 → `isSpeciality` + `num` | 🤖 AI 辅助填写 |
| 3 | `resources/goods/CityPosData.json` | 城市 key → 世界坐标 `[x, y]` | 📸 截图 + AI OCR 标定（见第三节） |
| 4 | `resources/goods/CityData.json` | 城市 key → 收益阶梯数组 | 🤖 AI 复制已有站 |
| 5 | `resources/goods/CityTiredData.json` | 新站↔每站的疲劳值（双向） | 🤖 AI 格式化用户提供的原始记录 |
| 6 | `resources/goods/AttachedToCityData.json` | 子站→主站映射 | 🤖 用户告知归属后 AI 直接加 |
| 7 | `resources/stations/name2id.json` | 站名→文件名 | ✋ 截图后填 |
| 8 | `resources/stations/xxx.png` | 站名截图模板 | ✋ 手动截图裁剪 |
| 9 | `config/app.json` | `LoopCities` / `CityHaggle` / `CityBook` 三处加 key | 🤖 AI 直接改 |


## 二、各文件数据获取方法 + AI Prompt

### 2.1 CityGoodsSellData.json + CityGoodsData.json（商品数据）

**文件格式：**
```json
// CityGoodsSellData.json — 城市→商品→基础价
{
  "武林源": {
    "兽皮": { "price": 388 },
    "精油": { "price": 320 }
  }
}

// CityGoodsData.json — 商品属性
{
  "武林源": {
    "兽皮": { "isSpeciality": false, "num": 63 },
    "精油": { "isSpeciality": true, "num": 1 }
  }
}
```

`isSpeciality` = true 表示是该城特产，`num` = 每批次可买数量。

**AI Prompt：**
```
项目路径：resources/goods/CityGoodsSellData.json
格式：{"站名": {"商品名": {"price": 整数}}}

项目路径：resources/goods/CityGoodsData.json
格式：{"站名": {"商品名": {"isSpeciality": bool, "num": 整数}}}

任务：为新站点 "{new_station}" 获取商品数据

执行步骤：
1. 访问 https://www.resonance-columba.com/prices 提取 {new_station} 的商品列表
2. 如果网页抓取失败，等待用户提供游戏内价格截图，OCR 识别价格
3. 对于 CityGoodsData.json 中的 isSpeciality 和 num：
   - 参考同类型已有城市的商品结构进行合理填充
   - 如果没有参考依据，标注为 isSpeciality: false, num: 1
4. 输出两个 JSON 片段，直接可填入对应文件
```

### 2.2 CityData.json（收益阶梯）

**文件格式：**
```json
{
  "7号自由港": [
    { "buy_num": 0.0, "revenue": 0.07 },
    { "buy_num": 0.1, "revenue": 0.07 },
    { "buy_num": 0.2, "revenue": 0.065 }
  ]
}
```

`buy_num` = 购入比例，`revenue` = 税率。

**AI Prompt：**
```
项目路径：resources/goods/CityData.json
格式：{"站名": [{"buy_num": float, "revenue": float}, ...]}

任务：为 {new_station} 添加收益阶梯

操作步骤：
1. 读取文件中已有城市的数据结构
2. 找一个与 {new_station} 同类型的城市（参照 isSpeciality 商品数量、定位类似的城市）
3. 复制该城市的整个数组作为 {new_station} 的值
4. 输出："{new_station}": [...] 的 JSON 片段
```

### 2.3 CityTiredData.json（疲劳值）

**文件格式：**
```json
{
  "武林源-7号自由港": 13,
  "7号自由港-武林源": 13,
  "武林源-修格里城": 8,
  "修格里城-武林源": 8
}
```

键格式为 `"A站-B站"`，值为整数疲劳。**双向都要加**，但值相同。

**AI Prompt：**
```
项目路径：resources/goods/CityTiredData.json
格式：{"A站-B站": 疲劳整数, "B站-A站": 疲劳整数}

任务：为 {new_station} 填充到其他所有站的疲劳数据

执行步骤：
1. 读取 CityPosData.json 中所有已有城市名
2. 等待用户提供 {new_station} → 每个城市的疲劳原始记录
   - 期望格式：用户说"去某某站 13"
3. 输出完整的 JSON 片段，包含：
   - {new_station} → 每个已有城市
   - 每个已有城市 → {new_station}
   （双向值相同，键对称）
4. 新增的键不要覆盖已有数据
```

### 2.4 AttachedToCityData.json（子站映射）

**文件格式：**
```json
{
  "荒原站": "修格里城",
  "贡露城": "武林源",
  "塔图站": "武林源"
}
```

- 主城（自己就是一个城市）→ 映射到自己
- 子站（属于另一个主城的附属站）→ 映射到所属主城

**AI Prompt：**
```
项目路径：resources/goods/AttachedToCityData.json
格式：{"子站名": "所属主城名"}

任务：为 {new_station} 添加子站映射

操作步骤：
1. 读取文件中已有城市结构
2. 等待用户告知 {new_station} 是主城还是子站
   - 如果是主城：直接映射到自己，即 "{new_station}": "{new_station}"
   - 如果是子站：用户会说"属于某某城"，映射到所属主城
3. 输出一行 JSON 片段
```

### 2.5 name2id.json + 模板 PNG（站名截图）

**文件格式：**
```json
{
  "修格里城": "xglc.png",
  "贡露城": "glc.png"
}
```

截图步骤：
1. 打开地图，让新站名显示在屏幕上
2. 截取 1280×720 完整画面
3. 裁剪出站名文字区域（仅文字，不包含上下图标）
4. 保存为 PNG，文件名简短（如 `xxz.png`）
5. name2id.json 加一条 `"新站名": "xxz.png"`

### 2.6 config/app.json（配置）

需要修改三处：
```json
{
  "CityHaggle": { "武林源": 0, "新站名": 0 },
  "CityBook": { "武林源": 1, "新站名": 0 },
  "RunBuy": {
    "LoopCities": ["武林源", "新站名"]
  }
}
```

- `CityHaggle`：所有站都设 0
- `CityBook`：新站设 0（需手动测试确认有几本书后再改）
- `LoopCities`：按需求加入循环路线

**AI Prompt：**
```
项目路径：config/app.json

任务：为 {new_station} 更新配置

操作步骤：
1. 读取 config/app.json
2. 在 CityHaggle 对象中加一条 "{new_station}": 0
3. 在 CityBook 对象中加一条 "{new_station}": 0
4. 在 RunBuy.LoopCities 数组中添加 "{new_station}"
5. 输出修改后的 JSON 片段
```


## 三、AI 辅助标定坐标（Agent 参与）

通过截图 + OCR 自动计算新站点的世界坐标，需要至少 2 个已知站点同时出现在截图中。

### 3.1 AI Prompt（可执行的 Agent 指令）

```
任务：计算新站点 "{new_station}" 的世界坐标

## 已知数据
项目文件 resources/goods/CityPosData.json 中的已知站点世界坐标：
  {列出所有已知站点和坐标}

## 接收用户输入
用户会提供一张 1280×720 的地图截图（base64 编码），截图中需要：
- 新站点 "{new_station}" 的站名文字清晰可见
- 至少 2 个已知站点的站名文字也清晰可见

## 执行步骤
1. 接收截图后用 OCR 识别所有文字
2. 从 OCR 结果中找出已知站点的文字中心位置 (cx, cy)
3. 站点图标位置 = (cx - 176, cy - 27)
   原因：站名文字下方有对应的地图图标，文字→图标的固定偏移为 dx=-176, dy=-27
4. 用所有找到的已知站点的 {世界坐标, 图标屏幕位置} 计算地图标定：

   world_per_px_x = median(|Δworld_x / Δscreen_x|) 对任意两个站 x 差值
   world_per_px_y = median(|Δworld_y / Δscreen_y|) 对任意两个站 y 差值

   center_world_x = median(world_x - (screen_x - 640) * world_per_px_x)
   center_world_y = median(world_y + (screen_y - 360) * world_per_px_y)
   注：y 轴方向 world 向上为正，screen 向下为正

5. 从 OCR 结果中找出新站点 "{new_station}" 的文字中心位置 (cx, cy)
   计算图标位置：icon_x = cx - 176, icon_y = cy - 27
   如果图标位置不在画面合理范围内（x<0 或 x>1280 或 y<0 或 y>720），返回错误

6. 新站世界坐标：
   new_world_x = center_world_x + (icon_x - 640) * world_per_px_x
   new_world_y = center_world_y - (icon_y - 360) * world_per_px_y

7. 输出格式（保留 1 位小数）：
   "{new_station}": [x, y]

## 验证标准
- 计算出的 world_per_px_x 和 world_per_px_y 应在 1.3 ~ 1.7 之间
- 如果不在这个范围，说明 OCR 可能有误或截图不清晰，需要重新截图
```

### 3.2 验证坐标

将得到的坐标填入 `CityPosData.json` 后，用标定确认：

```python
from resonance.scene.recognizer import Recognizer
from resonance.solvers.navigation import _calibrate_map_from_known_stations
cal = _calibrate_map_from_known_stations(Recognizer().ocr())
print(f"scale=({cal.world_per_px_x:.3f}, {cal.world_per_px_y:.3f})")
```

输出 `world_per_px` 应在 `1.48~1.52` 之间。


## 四、完整流程总结

```
Step 1  ✋ 截图裁剪站名模板 → resources/stations/xxx.png
Step 2  ✋ name2id.json 加映射
────────────────────────────────────
Step 3  📸 截一张有新站 + ≥2已知站的地图
Step 4  🤖 执行第三节 AI Prompt → 得世界坐标
Step 5  ✋ 坐标填入 CityPosData.json
────────────────────────────────────
Step 6  🤖 执行 2.1 Prompt → 得商品数据 → 填 CityGoodsSellData.json + CityGoodsData.json
Step 7  🤖 执行 2.2 Prompt → 复制收益阶梯 → 填 CityData.json
Step 8  🤖 执行 2.3 Prompt → 格式化疲劳记录 → 填 CityTiredData.json
Step 9  🤖 告知归属 → AI 填 AttachedToCityData.json
Step 10 🤖 执行 2.6 Prompt → AI 改 config/app.json
────────────────────────────────────
Step 11 📸 运行标定验证 world_per_px ≈ 1.5
Step 12 📸 运行坐标验证文档以下部分
```


# 新站点坐标验证文档

## 概述

新增站点需要三步：1) 截图裁剪模板 2) 添加 name2id 映射 3) 添加 CityPosData 世界坐标。本文档记录验证坐标是否准确的测试方法。

## 验证流程

### 0. 确认数据完整性

检查三个文件是否齐全：

| 文件 | 示例 |
|------|------|
| `resources/stations/xxx.png` | 站点图标模板 |
| `resources/stations/name2id.json` | `"贡露城": "glc.png"` |
| `resources/goods/CityPosData.json` | `"贡露城": [-290, -1252]` |

### 1. 编译检查

```bash
python -m py_compile resonance\solvers\navigation.py
```

无输出即通过。

### 2. 多点标定验证比例

连接模拟器后执行标定，确认 `world_per_px` 在 1.5 附近：

```python
from resonance.scene.recognizer import Recognizer
from resonance.solvers.navigation import _calibrate_map_from_known_stations
cal = _calibrate_map_from_known_stations(Recognizer().ocr())
```

输出示例：
```
scale=(1.497, 1.503) center=(152.9, -85.7)
```

`world_per_px_x/y` 应在 `1.48~1.52` 之间。

### 3. 模板匹配检查

在当前视野找新站：

```python
from resonance.solvers.navigation import find_station_on_map
loc = find_station_on_map("贡露城")
```

如果不在当前视野（理论屏幕坐标超出 60~1240 x 60~700），需要导航过去。

### 4. 导航到目标站

用最近已知锚点做大步粗滑：

```python
from resonance.solvers.navigation import (
    _coarse_swipe_from_anchor, _known_station_observations,
    MAP_CENTER, STATION_POS_DATA, WORLD_TO_SCREEN
)
obs = _known_station_observations()
anchor = min(obs, key=lambda o: abs(o.screen_x-640)+abs(o.screen_y-360))
ok = _coarse_swipe_from_anchor(anchor, "贡露城")
```

### 5. 精校正到中心

模板匹配到目标后，用 `nudge_station_to_point` 把目标拉到屏幕中心，验证最终偏移在 deadzone (±35px) 内：

```python
from resonance.solvers.navigation import nudge_station_to_point, find_station_on_map
ok = nudge_station_to_point("贡露城", MAP_CENTER, max_steps=6, deadzone=35)
final = find_station_on_map("贡露城")
offset = (final[0] - 640, final[1] - 360)
assert abs(offset[0]) <= 35 and abs(offset[1]) <= 35
```

输出示例：
```
精确矫正: 贡露城 已到目标区域 loc=(652, 365), target=(640, 360)
最终位置: (652, 365) 偏移=(12, 5) 成功=True
```

### 6. 验证标准

| 指标 | 合格标准 |
|------|---------|
| 最终屏幕偏移 | `|dx| <= 35` 且 `|dy| <= 35` |
| 标定 world_per_px | `1.48 ~ 1.52` |
| 模板匹配成功率 | 导航后能识别到 |
| OCR 精确识别 | "立即出发" 弹窗内勾选框先点再出发 |

## 实测记录（贡露城/黑月游乐城/塔图站/维蒂林场）

| 站点 | 世界坐标 | 初始屏幕位置 | 矫正后位置 | 最终偏移 | 步数 |
|------|---------|-------------|-----------|---------|------|
| 贡露城 | [-290, -1252] | (652, 365) | (652, 365) | (12, 5) | 0（已在中心） |
| 维蒂林场 | [230, -1060] | (984, 232) | (643, 362) | (3, 2) | 3 |
| 塔图站 | [1489, -1111] | (756, 410) | (646, 358) | (6, -2) | 1 |
| 黑月游乐城 | [-899, 538] | (810, 167) | (643, 342) | (3, -18) | 2 |

全部通过 ✅
