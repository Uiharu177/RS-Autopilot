"""兼容接口：实际买货实现位于 :mod:`resonance.solvers.purchase`。"""

from resonance.solvers.purchase import (
    _goods_signature,
    _is_locked,
    _match_good_name,
    _ocr_goods_list,
    _read_bargain_percent,
    _wait_bargain_stable,
    confirm_purchase,
    execute_purchase_flow,
    is_purchase_list_empty,
    negotiate_purchase_price,
    select_product_card,
)


def buy_business(primary_goods, secondary_goods, num=0, max_book=0):
    """Compatibility wrapper for :func:`execute_purchase_flow`."""
    return execute_purchase_flow(primary_goods, secondary_goods, num, max_book)


def buy_good(good, book, max_book, again=False):
    """Compatibility wrapper for :func:`select_product_card`."""
    return select_product_card(good, book, max_book, again)


def is_purchase_selection_empty():
    """Compatibility wrapper for :func:`is_purchase_list_empty`."""
    return is_purchase_list_empty()


def click_bargain_button(num=0, max_attempts=6):
    """Compatibility wrapper for :func:`negotiate_purchase_price`."""
    return negotiate_purchase_price(num, max_attempts)


def click_buy_button():
    """Compatibility wrapper for :func:`confirm_purchase`."""
    return confirm_purchase()
