"""场景级联识别器：按优先级运行 detector 列表，返回第一个匹配的场景。

  流程：
    Recognizer() → 截图 → 依次运行各 detector（优先级从高到低）
    → 第一个返回非 None 的场景即为当前场景
    → 缓存 2 秒内的结果避免重复截图
  每个 detector 是 scene/scenes/ 下的一个模块，实现 detect(image) → Scene | None。
"""

from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple, Union

import cv2 as cv

from resonance.device.device import screenshot_image
from resonance.scene.scene import Scene
from resonance.vision.color import BGR
from resonance.vision.ocr import predict
from resonance.vision.utils import MATCH_TEMPLATE_RESULT, match_template


# Type for a scene detector module
DetectorFunc = Callable[[cv.typing.MatLike, list, Set[str]], Optional[Scene]]


class Recognizer:
    """Central vision recognizer with screenshot caching and scene detection.

    Usage:
        recog = Recognizer()
        recog.update()              # force re-capture on next access
        scene = recog.scene         # lazy: capture -> detect -> cache
        result = recog.find("...")  # template match on cached image
    """

    def __init__(self):
        self._scene = Scene.UNDEFINED
        self._image: Optional[cv.typing.MatLike] = None
        self._ocr_cache: Optional[List[dict]] = None
        self._text_set: Optional[Set[str]] = None

        # Priority-ordered detection pipeline
        self._detectors: List[Tuple[str, DetectorFunc]] = []
        self._load_detectors()

    def _load_detectors(self):
        from resonance.scene.scenes import crash, transit, login, loading, battle, travel, navigation, exchange, station, shop, main, city, task
        self._detectors = [
            ("crash", crash.detect),
            ("loading", loading.detect),
            ("main", main.detect),
            ("task", task.detect),
            ("login", login.detect),
            ("battle", battle.detect),
            ("navigation", navigation.detect),
            ("transit", transit.detect),
            ("exchange", exchange.detect),
            ("station", station.detect),
            ("shop", shop.detect),
            ("city", city.detect),
            ("travel", travel.detect),
        ]

    # ---- Screenshot management ----

    def update(self):
        self._scene = Scene.UNDEFINED
        self._image = None
        self._ocr_cache = None
        self._text_set = None

    @property
    def image(self) -> cv.typing.MatLike:
        if self._image is None:
            self._image = screenshot_image()
        return self._image

    @image.setter
    def image(self, value: cv.typing.MatLike):
        self._image = value
        self._scene = Scene.UNDEFINED
        self._ocr_cache = None
        self._text_set = None

    # ---- Scene detection ----

    @property
    def scene(self) -> Scene:
        if self._scene == Scene.UNDEFINED:
            self._scene = self.get_scene()
        return self._scene

    def get_scene(self) -> Scene:
        img = self.image
        texts = self._ocr()
        text_set = self._text_set

        for name, detector in self._detectors:
            result = detector(img, texts, text_set)
            if result is not None:
                return result

        return Scene.UNKNOWN

    # ---- Convenience methods ----

    def find(
        self,
        template: Union[str, Path],
        threshold: float = 0.9,
        cropped_pos1: Tuple[int, int] = (0, 0),
        cropped_pos2: Tuple[int, int] = (0, 0),
    ) -> MATCH_TEMPLATE_RESULT:
        return match_template(
            self.image, template, cropped_pos1, cropped_pos2, threshold,
        )

    def get_bgr(self, pos: Tuple[int, int] = (0, 0), offset: int = 0) -> BGR:
        from resonance.vision.utils import get_bgr as _get_bgr
        return _get_bgr(self.image, pos, offset)

    def get_hsv(self, pos: Tuple[int, int] = (0, 0)):
        from resonance.vision.utils import get_hsv as _get_hsv
        return _get_hsv(self.image, pos)

    def ocr(self, **kwargs) -> List[dict]:
        if not kwargs:
            return self._ocr()
        return predict(self.image, **kwargs)

    def _ocr(self) -> List[dict]:
        if self._ocr_cache is None:
            self._ocr_cache = predict(self.image)
            self._text_set = {r["text"] for r in self._ocr_cache}
        return self._ocr_cache
