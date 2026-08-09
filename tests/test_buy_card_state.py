import unittest
from unittest.mock import patch

from resonance.solvers import buy


def ocr_item(text: str, x: int, y: int) -> dict:
    return {
        "text": text,
        "position": [[x - 20, y - 10], [x + 20, y - 10], [x + 20, y + 10], [x - 20, y + 10]],
    }


class BuyCardStateTests(unittest.TestCase):
    def test_buyable_card_accepts_percent_with_normal_ocr_vertical_jitter(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
            ocr_item("3333", 770, 352),
        ]

        state, pos = buy._find_good_state(data, "黑毛牛排")

        self.assertEqual(state, "buyable")
        self.assertEqual(pos, (798, 286))

    def test_lock_marker_wins_even_when_percent_is_visible(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
            ocr_item("声望等级解锁", 780, 345),
        ]

        state, pos = buy._find_good_state(data, "黑毛牛排")

        self.assertEqual(state, "locked")
        self.assertEqual(pos, (798, 286))

    def test_lock_marker_on_next_card_does_not_block_current_card(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
            ocr_item("金箔酒", 798, 405),
            ocr_item("声望等级解锁", 780, 455),
        ]

        state, pos = buy._find_good_state(data, "黑毛牛排")

        self.assertEqual(state, "buyable")
        self.assertEqual(pos, (798, 286))

    def test_missing_card_evidence_is_uncertain_not_clickable(self):
        data = [ocr_item("黑毛牛排", 798, 286)]

        state, pos = buy._find_good_state(data, "黑毛牛排")

        self.assertEqual(state, "uncertain")
        self.assertEqual(pos, (798, 286))
        self.assertIsNone(buy._match_good_name(data, "黑毛牛排"))

    def test_uncertain_card_never_swipes_or_clicks(self):
        data = [ocr_item("黑毛牛排", 798, 286)]

        with patch("resonance.solvers.buy._ocr_goods_list", return_value=data) as ocr, patch(
            "resonance.solvers.buy.input_swipe_hold"
        ) as swipe, patch("resonance.solvers.buy.click") as click, patch(
            "resonance.solvers.buy.time.sleep"
        ):
            result, _ = buy.buy_good("黑毛牛排", 0, 0)

        self.assertFalse(result)
        self.assertEqual(ocr.call_count, 3)
        swipe.assert_not_called()
        click.assert_not_called()

    def test_uncertain_then_ocr_miss_still_never_swipes_or_clicks(self):
        uncertain = [ocr_item("黑毛牛排", 798, 286)]

        with patch("resonance.solvers.buy._ocr_goods_list", side_effect=[uncertain, [], []]), patch(
            "resonance.solvers.buy.input_swipe_hold"
        ) as swipe, patch("resonance.solvers.buy.click") as click, patch(
            "resonance.solvers.buy.time.sleep"
        ):
            result, _ = buy.buy_good("黑毛牛排", 0, 0)

        self.assertFalse(result)
        swipe.assert_not_called()
        click.assert_not_called()

    def test_load_not_changed_does_not_trigger_a_retry_click(self):
        data = [
            ocr_item("黑毛牛排", 798, 286),
            ocr_item("100%", 770, 325),
        ]

        # One click is the intentional money probe; one is the normal product
        # selection. A third click would be the old blind retry and is unsafe.
        with patch("resonance.solvers.buy.get_boatload", side_effect=[100, 100, 90, 90, 90, 90]), patch(
            "resonance.solvers.buy._ocr_goods_list", return_value=data
        ), patch("resonance.solvers.buy.click") as click, patch(
            "resonance.solvers.buy.time.sleep"
        ), patch("resonance.solvers.buy.is_empty_goods", return_value=True):
            self.assertTrue(buy.buy_business(["黑毛牛排"], []))

        self.assertEqual(click.call_count, 2)
        click.assert_called_with((798, 286))


if __name__ == "__main__":
    unittest.main()
