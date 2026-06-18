from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    texts = [item["text"] for item in ocr_results]
    text = "\n".join(texts)
    if "取消追踪" in text:
        return Scene.TASK_DETAIL
    if "MISSION" not in text:
        return None
    markers = ("主线任务", "支线任务", "商会任务", "物资补给", "奖励物品")
    hits = sum(1 for marker in markers if marker in text)
    if hits >= 2:
        return Scene.TASK_DETAIL
    return None
