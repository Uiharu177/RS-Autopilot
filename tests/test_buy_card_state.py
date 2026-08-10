import unittest
from unittest.mock import call, patch

from resonance.solvers import purchase


def ocr_item(text: str, x: int, y: int) -> dict:
    return {
        "text": text,
        "position": [[x - 20, y - 10], [x + 20, y - 10], [x + 20, y + 10], [x - 20, y + 10]],
    }


class PurchaseFlowTests(unittest.TestCase):
    def test_buyable_card_accepts_percent_with_normal_ocr_vertical_jitter(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
            ocr_item("3333", 770, 352),
        ]
        state, pos = purchase._find_good_state(data, "黑毛牛排")
        self.assertEqual(state, "buyable")
        self.assertEqual(pos, (798, 286))

    def test_lock_marker_wins_even_when_percent_is_visible(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
            ocr_item("声望等级解锁", 780, 345),
        ]
        state, pos = purchase._find_good_state(data, "黑毛牛排")
        self.assertEqual(state, "locked")
        self.assertEqual(pos, (798, 286))

    def test_lock_marker_on_next_card_does_not_block_current_card(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
            ocr_item("金箔酒", 798, 405),
            ocr_item("声望等级解锁", 780, 455),
        ]
        state, pos = purchase._find_good_state(data, "黑毛牛排")
        self.assertEqual(state, "buyable")
        self.assertEqual(pos, (798, 286))

    def test_missing_card_evidence_is_uncertain_not_clickable(self):
        data = [ocr_item("黑毛牛排", 798, 286)]
        state, pos = purchase._find_good_state(data, "黑毛牛排")
        self.assertEqual(state, "uncertain")
        self.assertEqual(pos, (798, 286))
        self.assertIsNone(purchase._match_good_name(data, "黑毛牛排"))

    def test_uncertain_card_never_swipes_or_clicks(self):
        data = [ocr_item("黑毛牛排", 798, 286)]
        with patch("resonance.solvers.purchase._ocr_goods_list", return_value=data) as ocr, patch(
            "resonance.solvers.purchase.input_swipe_hold"
        ) as swipe, patch("resonance.solvers.purchase.click") as click, patch(
            "resonance.solvers.purchase.time.sleep"
        ):
            result, _ = purchase.select_product_card("黑毛牛排", 0, 0)
        self.assertFalse(result)
        self.assertEqual(ocr.call_count, 3)
        swipe.assert_not_called()
        click.assert_not_called()

    def test_full_boatload_stops_scanning_remaining_goods(self):
        with patch(
            "resonance.solvers.purchase.get_boatload", side_effect=[100, 100, 90, 90, 0]
        ), patch(
            "resonance.solvers.purchase.select_product_card", return_value=(True, 0)
        ) as select_card, patch("resonance.solvers.purchase.time.sleep"), patch(
            "resonance.solvers.purchase.is_purchase_list_empty", return_value=True
        ):
            self.assertTrue(purchase.execute_purchase_flow(["黑毛牛排", "行李箱包"], ["大龙虾"]))
        self.assertEqual(select_card.call_count, 2)
        self.assertEqual(select_card.call_args_list[0].args[0], "黑毛牛排")
        self.assertEqual(select_card.call_args_list[1].args[0], "黑毛牛排")

    def test_buy_settlement_visible_by_title_or_tax_and_total(self):
        with patch(
            "resonance.solvers.purchase._buy_settlement_texts", return_value=["买入结算报告"]
        ):
            self.assertTrue(purchase._is_buy_settlement_visible())
        with patch(
            "resonance.solvers.purchase._buy_settlement_texts", return_value=["纳税", "买入总价"]
        ):
            self.assertTrue(purchase._is_buy_settlement_visible())

    def test_purchase_clicks_once_and_closes_settlement_once(self):
        with patch(
            "resonance.solvers.purchase._is_buy_settlement_visible", side_effect=[True, False]
        ), patch("resonance.solvers.purchase.input_tap") as tap, patch(
            "resonance.solvers.purchase.time.sleep"
        ):
            self.assertTrue(purchase.confirm_purchase())
        self.assertEqual(tap.call_args_list, [call((1056, 647)), call((896, 676))])

    def test_purchase_closes_settlement_twice_only_when_still_visible(self):
        with patch(
            "resonance.solvers.purchase._is_buy_settlement_visible", side_effect=[False, True, True]
        ), patch("resonance.solvers.purchase.input_tap") as tap, patch(
            "resonance.solvers.purchase.time.sleep"
        ):
            self.assertTrue(purchase.confirm_purchase())
        self.assertEqual(tap.call_args_list, [call((1056, 647)), call((896, 676)), call((896, 676))])

    def test_purchase_without_settlement_fails_without_retrying_buy_button(self):
        with patch(
            "resonance.solvers.purchase._is_buy_settlement_visible", return_value=False
        ), patch("resonance.solvers.purchase.input_tap") as tap, patch(
            "resonance.solvers.purchase.time.sleep"
        ):
            self.assertFalse(purchase.confirm_purchase())
        tap.assert_called_once_with((1056, 647))


if __name__ == "__main__":
    unittest.main()
