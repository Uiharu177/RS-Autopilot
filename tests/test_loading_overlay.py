import unittest

from resonance.scene.scene import Scene
from resonance.scene.scenes import loading


def ocr_item(text, center_x, center_y):
    return {
        "text": text,
        "position": [
            [center_x - 20, center_y - 10],
            [center_x + 20, center_y - 10],
            [center_x + 20, center_y + 10],
            [center_x - 20, center_y + 10],
        ],
    }


class LoadingOverlayTests(unittest.TestCase):
    def test_bottom_random_loading_status_overrides_underlying_login(self):
        ocr = [
            ocr_item("点击屏幕进入游戏", 640, 560),
            ocr_item("正在计算波函数", 640, 684),
        ]
        self.assertEqual(loading.detect(None, ocr, {item["text"] for item in ocr}), Scene.LOADING)

    def test_regular_bottom_text_does_not_count_as_loading_overlay(self):
        ocr = [ocr_item("点击屏幕进入游戏", 640, 560)]
        self.assertIsNone(loading.detect(None, ocr, {item["text"] for item in ocr}))

    def test_random_loading_text_outside_bottom_strip_does_not_match(self):
        ocr = [ocr_item("正在计算波函数", 640, 400)]
        self.assertIsNone(loading.detect(None, ocr, {item["text"] for item in ocr}))


if __name__ == "__main__":
    unittest.main()
