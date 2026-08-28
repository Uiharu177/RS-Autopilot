"""OCR 模块：ONNX PaddleOCR 封装，线程安全。

  使用 onnxocr.onnx_paddleocr.ONNXPaddleOcr 模型。
  提供 predict(image, cropped_pos1, cropped_pos2) 接口。
  内部维护 threading.Lock 保证单线程调用模型。
  支持 merge_ocr_text() — 合并相邻 OCR 文本块。
"""

from pathlib import Path
from threading import Lock
from typing import Iterable, Tuple, Union

import cv2 as cv
import numpy as np
from onnxocr.onnx_paddleocr import ONNXPaddleOcr

from resonance.vision.utils import crop_image

model = ONNXPaddleOcr(
    use_angle_cls=False, use_gpu=True, use_dml=False, use_openvino=False
)
_ocr_lock = Lock()

_NUMERIC_CHARACTERS = frozenset("0123456789/ ")


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


def _decode_ctc_output(
    predictions: np.ndarray,
    character: list[str],
    allowed_characters: frozenset[str] | None,
) -> list[tuple[str, float]]:
    """Decode raw CTC recognizer output without postprocess filtering.

    ``allowed_characters`` implements constrained decoding for fixed business
    fields: probabilities for labels outside the set are ignored before the
    usual per-frame CTC argmax.  No source text is substituted or repaired.
    """
    if predictions.ndim == 2:
        predictions = predictions[np.newaxis, ...]
    if predictions.ndim != 3:
        raise ValueError(f"Unsupported recognizer output shape: {predictions.shape}")

    blank_index = 0
    decoded: list[tuple[str, float]] = []
    for batch_predictions in predictions:
        pieces: list[str] = []
        confidences: list[float] = []
        previous_index = blank_index
        for frame_probabilities in batch_predictions:
            candidate_count = len(frame_probabilities)
            if allowed_characters is None:
                allowed_indices = range(1, candidate_count)
            else:
                allowed_indices = (
                    index
                    for index in range(1, candidate_count)
                    if index < len(character)
                    and character[index] in allowed_characters
                )
            best_index = max(allowed_indices, key=lambda index: frame_probabilities[index])
            if best_index != previous_index:
                pieces.append(character[best_index])
                confidences.append(float(frame_probabilities[best_index]))
            previous_index = best_index

        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        decoded.append(("".join(pieces), confidence))
    return decoded


def _run_recognizer_with_allowed_characters(
    image: cv.typing.MatLike, allowed_characters: frozenset[str]
) -> list:
    recognizer = model.text_recognizer
    normalized_image = recognizer.resize_norm_img(image, image.shape[1] / image.shape[0])
    normalized_batch = normalized_image[np.newaxis, ...].copy()
    input_feed = recognizer.get_input_feed(
        recognizer.rec_input_name, normalized_batch
    )
    outputs = recognizer.run(recognizer.rec_output_name, input_feed=input_feed)
    decoded = _decode_ctc_output(
        outputs[0], recognizer.postprocess_op.character, allowed_characters
    )
    # Reuse the standard result shape: box + [text, score].  A constrained
    # field has exactly one detector-independent crop, so its box is a unit
    # placeholder and is not used for clicking.
    return [
        [[[0, 0], [0, 0], [0, 0], [0, 0]], [text, score]]
        for text, score in decoded
    ]


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
    allowed_characters: frozenset[str] | None = None,
):
    image = _prepare_image(image, cropped_pos1, cropped_pos2, no_crop)
    if image is None:
        return []
    with _ocr_lock:
        if allowed_characters is None:
            out = model.ocr(image)
        else:
            out = [_run_recognizer_with_allowed_characters(image, allowed_characters)]
    return ocrout2result(out, cropped_pos1)


def predict(
    image: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False,
    allowed_characters: Iterable[str] | None = None,
):
    allowed_set = None if allowed_characters is None else frozenset(allowed_characters)
    return _predict_impl(
        image,
        cropped_pos1,
        cropped_pos2,
        no_crop,
        allowed_characters=allowed_set,
    )


def number_predict(
    image: Union[str, Path, cv.typing.MatLike],
    cropped_pos1: Tuple[int, int] = (0, 0),
    cropped_pos2: Tuple[int, int] = (0, 0),
    no_crop: bool = False,
):
    """Recognize a fixed numeric business field with constrained CTC decoding.

    The slash stays in the allowed set because ``current/capacity`` is part of
    the source label; replacing it with ``1`` would recreate the OCR bug.
    """
    return _predict_impl(
        image,
        cropped_pos1,
        cropped_pos2,
        no_crop,
        allowed_characters=_NUMERIC_CHARACTERS,
    )
