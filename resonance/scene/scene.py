"""场景枚举：定义游戏所有可能的页面状态。

  Recognizer 级联运行各 detector，返回第一个匹配的 Scene 值。
  TRAVEL_ARRIVED 已废弃（到站 = MAIN_MAP + OCR 访问城市按钮）。
"""

from enum import IntEnum


class Scene(IntEnum):
    """Game screen scene enumeration.

    Negative values = unknown/waiting/transient scenes.
    Positive values = known/stable scenes.
    Zero = UNDEFINED (internal cache flag, not yet evaluated).
    """

    # --- Internal cache flag ---
    UNDEFINED = 0

    # --- Unknown/transient scenes (negative) ---
    UNKNOWN = -1
    UNKNOWN_WITH_NAVBAR = -2
    TRANSIT = -3
    LOADING = -4
    CONNECTING = -5
    LOGIN = -6
    CRASH = -7

    # --- Known stable scenes ---
    MAIN_MAP = 1
    CITY_VIEW = 2
    STATION_DETAIL = 3
    STATION_LIST = 4
    TASK_DETAIL = 5

    # --- Travel ---
    TRAVEL_CRUISE = 10
    TRAVEL_ROUTE = 11
    TRAVEL_ARRIVED = 12
    TRAVEL_MAP = 13

    # --- Battle ---
    BATTLE_CARD = 20
    BATTLE_REWARD = 21
    BATTLE_RESULT = 22

    # --- Exchange ---
    EXCHANGE = 30
    EXCHANGE_BUY = 31
    EXCHANGE_SELL = 32

    # --- Shop ---
    SHOP = 40
    SHOP_CONFIRM = 41

    # --- UI dialogs ---
    DIALOG_CONFIRM = 50
    DIALOG_STAMINA = 51
    DIALOG_HAGGLE = 52
    DIALOG_BOOK_USE = 53
    DIALOG_CITY_INFO = 54
    DIALOG_REWARD = 55
    DIALOG_LOCAL_GOODS = 56
    DIALOG_ERROR = 57
