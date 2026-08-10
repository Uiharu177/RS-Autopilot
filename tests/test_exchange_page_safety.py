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
            side_effect=[["交易所", "我要买", "我要卖", "预计卖出"], ["预计买入"]],
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertTrue(exchange._switch_exchange_tab("buy"))
        tap.assert_called_once_with((120, 670))

    def test_entry_page_uses_its_own_buy_and_sell_buttons(self):
        for tab, expected_pos, marker in (
            ("buy", (960, 321), "预计买入"),
            ("sell", (960, 405), "预计卖出"),
        ):
            with self.subTest(tab=tab), patch(
                "resonance.solvers.exchange._current_exchange_texts",
                side_effect=[["交易所", "我要买", "我要卖"], [marker]],
            ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
                "resonance.solvers.exchange.time.sleep"
            ):
                self.assertTrue(exchange._switch_exchange_tab(tab))
            tap.assert_called_once_with(expected_pos)

    def test_failed_bottom_tab_switch_does_not_retry_entry_button(self):
        sell_page = ["交易所", "我要买", "我要卖", "预计卖出"]
        with patch(
            "resonance.solvers.exchange._current_exchange_texts", side_effect=[sell_page, sell_page]
        ), patch("resonance.solvers.exchange.input_tap") as tap, patch(
            "resonance.solvers.exchange.time.sleep"
        ):
            self.assertFalse(exchange._switch_exchange_tab("buy"))
        tap.assert_called_once_with((120, 670))

    def test_exchange_outlet_matching_uses_the_common_keyword(self):
        self.assertIn(exchange.EXCHANGE_OCR_KEYWORD, "巫交易所")
        self.assertIn(exchange.EXCHANGE_OCR_KEYWORD, "交易所-武林市集")


if __name__ == "__main__":
    unittest.main()
