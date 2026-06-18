"""OCR 模块：ONNX PaddleOCR 封装，线程安全。

  使用 onnxocr.onnx_paddleocr.ONNXPaddleOcr 模型。
  提供 predict(image, cropped_pos1, cropped_pos2) 接口。
  内部维护 threading.Lock 保证单线程调用模型。
  支持 merge_ocr_text() — 合并相邻 OCR 文本块。
"""

from pathlib import Path
from threading import Lock
from typing import Tuple, Union

import cv2 as cv
from onnxocr.onnx_paddleocr import ONNXPaddleOcr

from resonance.vision.utils import crop_image

model = ONNXPaddleOcr(
    use_angle_cls=False, use_gpu=True, use_dml=False, use_openvino=False
)
_ocr_lock = Lock()


def ocrout2result(out, cropped_pos1):
    if not out or not out[0]:
        return []

    out = out[0]
    return [
        {
            "text": str(predict_data[1][0]),
            "score": float(predict_data[1][1]),
            "position": [
                [float(predict_data[0][0][0] + cropped_pos1[0]), float(predict_data[0][0][1] + cropped_pos1[1])],
                [float(predict_data[0][1][0] + cropped_pos1[0]), float(predict_data[0][1][1] + cropped_pos1[1])],
                [float(predict_data[0][2][0] + cropped_pos1[0]), float(predict_data[0][2][1] + cropped_pos1[1])],
                [float(predict_data[0][3][0] + cropped_pos1[0]), float(predict_data[0][3][1] + cropped_pos1[1])],
            ],
        }
        for predict_data in out
    ]


def merge_ocr_text(ocr_results: list[dict]) -> tuple[str, str]:
    texts = [str(item.get("text", "")) for item in ocr_results]
    joined = "\n".join(texts)
    compact = "".join("".join(text.split()) for text in texts)
    return joined, compact


def _prepare_image(
    image: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False,
):
    if isinstance(image, Path):
        image = str(image)
    if isinstance(image, str):
        image = cv.imread(image)
    if image is None:
        return None
    if (cropped_pos1 != (0, 0) or cropped_pos2 != (0, 0)) and not no_crop:
        image = crop_image(image, cropped_pos1, cropped_pos2)
    return image


def _predict_impl(
    image: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False,
):
    image = _prepare_image(image, cropped_pos1, cropped_pos2, no_crop)
    if image is None:
        return []
    with _ocr_lock:
        out = model.ocr(image)
    return ocrout2result(out, cropped_pos1)


def predict(
    image: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False
):
    return _predict_impl(image, cropped_pos1, cropped_pos2, no_crop)


def number_predict(
    image: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False
):
    return _predict_impl(image, cropped_pos1, cropped_pos2, no_crop)
