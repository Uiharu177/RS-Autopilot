"""兼容接口：实际卖货实现位于 :mod:`resonance.solvers.sale`。"""

from resonance.solvers.sale import execute_sale_flow, negotiate_sale_price


def sell_goods(haggle=0):
    """Compatibility wrapper for :func:`execute_sale_flow`."""
    return execute_sale_flow(haggle)


def click_bargain_button(num=0, max_attempts=6):
    """Compatibility wrapper for :func:`negotiate_sale_price`."""
    return negotiate_sale_price(num, max_attempts)
