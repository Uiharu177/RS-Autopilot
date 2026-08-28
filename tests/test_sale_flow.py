import unittest
from unittest.mock import call, patch

from resonance.solvers import sale


class SaleFlowTests(unittest.TestCase):
    def test_sale_load_parses_dynamic_concatenated_value_and_capacity(self):
        cases = {
            "62711073": 627,
            "250824": 250,
            "12001500": 1200,
        }
        for text, expected in cases.items():
            with self.subTest(text=text), patch(
                "resonance.solvers.sale.number_predict", return_value=[{"text": text}]
            ), patch("resonance.solvers.sale.screenshot_image"):
                self.assertEqual(sale._read_sale_load(), expected)

    def test_sale_load_rejects_invalid_concatenated_value_and_capacity(self):
        for text in ("100001000", "9999", "not-a-number"):
            with self.subTest(text=text), patch(
                "resonance.solvers.sale.number_predict", return_value=[{"text": text}]
            ), patch("resonance.solvers.sale.screenshot_image"):
                self.assertIsNone(sale._read_sale_load())

    def test_concatenated_sale_load_completes_sale_flow(self):
        with patch(
            "resonance.solvers.sale._is_sale_page_ready", return_value=True
        ), patch(
            "resonance.solvers.sale.predict",
            side_effect=[[{"text": "62711073"}], [{"text": "62711073"}]],
        ), patch(
            "resonance.solvers.sale.number_predict",
            side_effect=[[{"text": "62711073"}], [{"text": "62711073"}]],
        ), patch("resonance.solvers.sale.screenshot_image"), patch(
            "resonance.solvers.sale._select_all_for_sale"
        ), patch(
            "resonance.solvers.sale.negotiate_sale_price", return_value=True
        ), patch(
            "resonance.solvers.sale._is_sell_settlement_visible", return_value=False
        ), patch("resonance.solvers.sale._is_sale_page_visible", return_value=True), patch(
            "resonance.solvers.sale.input_tap"
        ) as tap, patch("resonance.solvers.sale.time.sleep"):
            self.assertTrue(sale.execute_sale_flow())
        tap.assert_called_once_with((1056, 647))

    def test_empty_cargo_skips_all_sale_controls(self):
        with patch(
            "resonance.solvers.sale._is_sale_page_ready", return_value=True
        ), patch(
            "resonance.solvers.sale._read_sale_load", return_value=0
        ), patch("resonance.solvers.sale._select_all_for_sale") as select_all, patch(
            "resonance.solvers.sale.negotiate_sale_price"
        ) as negotiate, patch("resonance.solvers.sale._confirm_sale") as confirm:
            self.assertTrue(sale.execute_sale_flow())
        select_all.assert_not_called()
        negotiate.assert_not_called()
        confirm.assert_not_called()

    def test_sale_settlement_visible_by_title_or_profit_and_tax(self):
        with patch(
            "resonance.solvers.sale._sale_ocr_texts", return_value=["卖出结算报告"]
        ):
            self.assertTrue(sale._is_sell_settlement_visible())
        with patch(
            "resonance.solvers.sale._sale_ocr_texts", return_value=["总利润", "纳税"]
        ):
            self.assertTrue(sale._is_sell_settlement_visible())

    def test_sale_clicks_once_and_closes_settlement_once(self):
        with patch(
            "resonance.solvers.sale._is_sell_settlement_visible", side_effect=[True, False]
        ), patch("resonance.solvers.sale.input_tap") as tap, patch(
            "resonance.solvers.sale.time.sleep"
        ):
            self.assertTrue(sale._confirm_sale(1073))
        self.assertEqual(tap.call_args_list, [call((1056, 647)), call((896, 676))])

    def test_sale_closes_settlement_twice_only_when_still_visible(self):
        with patch(
            "resonance.solvers.sale._is_sell_settlement_visible", side_effect=[False, True, True]
        ), patch("resonance.solvers.sale.input_tap") as tap, patch(
            "resonance.solvers.sale.time.sleep"
        ):
            self.assertTrue(sale._confirm_sale(1073))
        self.assertEqual(tap.call_args_list, [call((1056, 647)), call((896, 676)), call((896, 676))])

    def test_sale_page_with_unchanged_cargo_completes_clearance_without_extra_input(self):
        with patch(
            "resonance.solvers.sale._is_sell_settlement_visible", return_value=False
        ), patch(
            "resonance.solvers.sale._is_sale_page_visible", return_value=True
        ), patch(
            "resonance.solvers.sale._read_sale_load", return_value=1073
        ), patch("resonance.solvers.sale.input_tap") as tap, patch(
            "resonance.solvers.sale.time.sleep"
        ):
            self.assertTrue(sale._confirm_sale(1073))
        tap.assert_called_once_with((1056, 647))

    def test_sale_page_with_increased_cargo_fails_safely(self):
        with patch(
            "resonance.solvers.sale._is_sell_settlement_visible", return_value=False
        ), patch(
            "resonance.solvers.sale._is_sale_page_visible", return_value=True
        ), patch(
            "resonance.solvers.sale._read_sale_load", return_value=1074
        ), patch("resonance.solvers.sale.input_tap") as tap, patch(
            "resonance.solvers.sale.time.sleep"
        ):
            self.assertFalse(sale._confirm_sale(1073))
        tap.assert_called_once_with((1056, 647))

    def test_unknown_page_fails_without_extra_input(self):
        with patch(
            "resonance.solvers.sale._is_sell_settlement_visible", return_value=False
        ), patch(
            "resonance.solvers.sale._is_sale_page_visible", return_value=False
        ), patch("resonance.solvers.sale._read_sale_load") as load, patch(
            "resonance.solvers.sale.input_tap"
        ) as tap, patch("resonance.solvers.sale.time.sleep"):
            self.assertFalse(sale._confirm_sale(1073))
        tap.assert_called_once_with((1056, 647))
        load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
