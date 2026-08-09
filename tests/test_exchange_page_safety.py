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


if __name__ == "__main__":
    unittest.main()
