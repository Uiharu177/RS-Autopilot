from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    texts = [item["text"] for item in ocr_results]
    if not any("进入" in text for text in texts):
        return None
    triggers = ("交易所", "市集", "工会", "俱乐部", "商会", "铁安局")
    if any(trigger in text for text in texts for trigger in triggers):
        return Scene.STATION_DETAIL
    return None
