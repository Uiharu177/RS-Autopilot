import unittest
from unittest.mock import patch

from resonance.solvers import exchange


class ExchangePageSafetyTests(unittest.TestCase):
    def test_main_screen_cargo_expansion_text_is_not_a_sell_page(self):
        self.assertFalse(exchange._is_exchange_tab("sell", ["货舱扩容", "任务"]))

    def test_sell_page_specific_markers_are_accepted(self):
        self.assertTrue(exchange._is_exchange_tab("sell", ["预计卖出"]))
        self.assertTrue(exchange._is_exchange_tab("sell", ["抬价幅度 5%"]))

    def test_exchange_entry_is_not_mistaken_for_a_sell_tab(self):
        texts = ["交易所", "我要买", "我要卖"]
        self.assertTrue(exchange._is_exchange_entry(texts))
        self.assertFalse(exchange._is_exchange_tab("sell", texts))

    def test_sell_page_with_bottom_tabs_is_not_an_exchange_entry(self):
        texts = ["交易所", "我要买", "我要卖", "预计卖出", "卖出总价"]

        self.assertTrue(exchange._is_exchange_tab("sell", texts))
        self.assertFalse(exchange._is_exchange_entry(texts))

    def test_sell_page_switches_to_buy_with_bottom_tab_only(self):
        with patch(
            "resonance.solvers.exchange._current_exchange_texts",
            side_effect=[
                ["交易所", "我要买", "我要卖", "预计卖出", "卖出总价"],
                ["预计买入", "买入总价"],
            ],
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertTrue(exchange._switch_exchange_tab("buy"))

        tap.assert_called_once_with((120, 670))

    def test_entry_page_uses_its_own_buy_and_sell_buttons(self):
        for tab, expected_pos, target_marker in (
            ("buy", (960, 321), "预计买入"),
            ("sell", (960, 405), "预计卖出"),
        ):
            with self.subTest(tab=tab), patch(
                "resonance.solvers.exchange._current_exchange_texts",
                side_effect=[["交易所", "我要买", "我要卖"], [target_marker]],
            ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
                "resonance.solvers.exchange.time.sleep"
            ):
                self.assertTrue(exchange._switch_exchange_tab(tab))

            tap.assert_called_once_with(expected_pos)

    def test_failed_bottom_tab_switch_does_not_retry_entry_button(self):
        sell_page = ["交易所", "我要买", "我要卖", "预计卖出"]
        with patch(
            "resonance.solvers.exchange._current_exchange_texts",
            side_effect=[sell_page, sell_page],
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertFalse(exchange._switch_exchange_tab("buy"))

        tap.assert_called_once_with((120, 670))

    def test_exchange_outlet_matching_uses_the_common_keyword(self):
        self.assertIn(exchange.EXCHANGE_OCR_KEYWORD, "巫交易所")
        self.assertIn(exchange.EXCHANGE_OCR_KEYWORD, "交易所-武林市集")

    def test_entry_page_opens_sell_with_its_own_button(self):
        with patch(
            "resonance.solvers.exchange._current_exchange_texts",
            side_effect=[["交易所", "我要买", "我要卖"], ["预计卖出"]],
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertTrue(exchange._switch_exchange_tab("sell"))

        tap.assert_called_once_with((960, 405))

    def test_sell_goods_refuses_input_when_sell_tab_is_not_confirmed(self):
        with patch(
            "resonance.solvers.exchange._is_sell_page_ready", return_value=False
        ), patch("resonance.solvers.exchange._select_all") as select_all, patch(
            "resonance.solvers.exchange.input_tap"
        ) as tap:
            self.assertFalse(exchange.sell_goods())

        select_all.assert_not_called()
        tap.assert_not_called()

    def test_empty_cargo_skips_all_sell_controls(self):
        with patch(
            "resonance.solvers.exchange._is_sell_page_ready", return_value=True
        ), patch(
            "resonance.solvers.exchange._read_sell_cargo_load", return_value=0
        ), patch("resonance.solvers.exchange._bargain_sell") as bargain, patch(
            "resonance.solvers.exchange._confirm_sell"
        ) as confirm, patch("resonance.solvers.exchange.input_tap") as tap:
            self.assertTrue(exchange.sell_goods())

        bargain.assert_not_called()
        confirm.assert_not_called()
        tap.assert_not_called()

    def test_settlement_visible_by_title_or_profit_and_tax(self):
        with patch(
            "resonance.solvers.exchange._ocr_texts_in_region", return_value=["卖出结算报告"]
        ):
            self.assertTrue(exchange._is_sell_settlement_visible())
        with patch(
            "resonance.solvers.exchange._ocr_texts_in_region", return_value=["总利润", "纳税"]
        ):
            self.assertTrue(exchange._is_sell_settlement_visible())

    def test_first_settlement_check_confirms_sale_and_closes_once(self):
        with patch(
            "resonance.solvers.exchange._is_sell_settlement_visible", side_effect=[True, False]
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertTrue(exchange._confirm_sell(1073))

        self.assertEqual(tap.call_args_list, [
            unittest.mock.call((1056, 647)),
            unittest.mock.call((896, 676)),
        ])

    def test_second_settlement_check_confirms_sale_and_closes_twice_if_needed(self):
        with patch(
            "resonance.solvers.exchange._is_sell_settlement_visible", side_effect=[False, True, True]
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertTrue(exchange._confirm_sell(1073))

        self.assertEqual(tap.call_args_list, [
            unittest.mock.call((1056, 647)),
            unittest.mock.call((896, 676)),
            unittest.mock.call((896, 676)),
        ])

    def test_no_sellable_goods_notice_returns_true_without_retrying_sell(self):
        with patch(
            "resonance.solvers.exchange._is_sell_settlement_visible", return_value=False
        ), patch(
            "resonance.solvers.exchange._is_sell_page_still_visible", return_value=True
        ), patch(
            "resonance.solvers.exchange._has_no_sellable_goods_notice", return_value=True
        ), patch("resonance.solvers.exchange._read_sell_cargo_load") as load, patch(
            "resonance.solvers.exchange.input_tap"
        ) as tap, patch("resonance.solvers.exchange.time.sleep"):
            self.assertTrue(exchange._confirm_sell(1073))

        tap.assert_called_once_with((1056, 647))
        load.assert_not_called()

    def test_sell_page_with_unchanged_cargo_fails_without_extra_input(self):
        with patch(
            "resonance.solvers.exchange._is_sell_settlement_visible", return_value=False
        ), patch(
            "resonance.solvers.exchange._is_sell_page_still_visible", return_value=True
        ), patch(
            "resonance.solvers.exchange._has_no_sellable_goods_notice", return_value=False
        ), patch(
            "resonance.solvers.exchange._read_sell_cargo_load", return_value=1073
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertFalse(exchange._confirm_sell(1073))

        tap.assert_called_once_with((1056, 647))

    def test_unknown_page_fails_without_extra_input(self):
        with patch(
            "resonance.solvers.exchange._is_sell_settlement_visible", return_value=False
        ), patch(
            "resonance.solvers.exchange._is_sell_page_still_visible", return_value=False
        ), patch("resonance.solvers.exchange._read_sell_cargo_load") as load, patch(
            "resonance.solvers.exchange.input_tap"
        ) as tap, patch("resonance.solvers.exchange.time.sleep"):
            self.assertFalse(exchange._confirm_sell(1073))

        tap.assert_called_once_with((1056, 647))
        load.assert_not_called()

    def test_sell_cargo_load_parser_reads_current_value(self):
        with patch(
            "resonance.solvers.exchange.predict",
            return_value=[{"text": "载货量"}, {"text": "282 / 1073"}],
        ), patch("resonance.solvers.exchange.screenshot_image"):
            self.assertEqual(exchange._read_sell_cargo_load(), 282)

    def test_sell_cargo_load_ocr_failure_is_not_treated_as_empty(self):
        with patch(
            "resonance.solvers.exchange._is_sell_page_ready", return_value=True
        ), patch(
            "resonance.solvers.exchange._read_sell_cargo_load", return_value=None
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertFalse(exchange.sell_goods())

        tap.assert_not_called()


if __name__ == "__main__":
    unittest.main()
