import unittest
from unittest.mock import patch

from resonance.solvers import buy, sell


class ModuleCompatibilityTests(unittest.TestCase):
    def test_buy_compatibility_wrappers_forward_to_purchase(self):
        with patch("resonance.solvers.buy.execute_purchase_flow", return_value=True) as execute:
            self.assertTrue(buy.buy_business(["A"], ["B"], 2, 1))
        execute.assert_called_once_with(["A"], ["B"], 2, 1)

        with patch("resonance.solvers.buy.select_product_card", return_value=(True, 0)) as select:
            self.assertEqual(buy.buy_good("A", 0, 1), (True, 0))
        select.assert_called_once_with("A", 0, 1, False)

    def test_sell_compatibility_wrappers_forward_to_sale(self):
        with patch("resonance.solvers.sell.execute_sale_flow", return_value=True) as execute:
            self.assertTrue(sell.sell_goods(2))
        execute.assert_called_once_with(2)

        with patch("resonance.solvers.sell.negotiate_sale_price", return_value=True) as negotiate:
            self.assertTrue(sell.click_bargain_button(2, 6))
        negotiate.assert_called_once_with(2, 6)


if __name__ == "__main__":
    unittest.main()
