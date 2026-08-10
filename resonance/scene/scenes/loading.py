from typing import Optional, Set

from resonance.scene.scene import Scene


def detect(img, ocr_results: list, text_set: Set[str]) -> Optional[Scene]:
    loading_markers = (
        "加载中",
        "正在加载",
        "资源加载",
        "Loading",
        "LOADING",
    )
    if any(marker in text for text in text_set for marker in loading_markers):
        return Scene.LOADING

    # Network jitter uses the same loading overlay on top of whatever page was
    # underneath (login, exchange, etc.).  Its status sentence is deliberately
    # random, but its layout is stable: a short "正在…" line sits beside the
    # train icon in the bottom status strip.  Detect the layout rather than
    # enumerating the changing flavour text, so LOADING takes precedence over
    # the underlying page and no input is sent while the overlay is present.
    for item in ocr_results:
        text = str(item.get("text", "")).strip()
        if not text.startswith("正在") or len(text) < 3:
            continue
        position = item.get("position")
        if not position:
            continue
        center_x = (position[0][0] + position[2][0]) / 2
        center_y = (position[0][1] + position[2][1]) / 2
        if 420 <= center_x <= 920 and center_y >= 580:
            return Scene.LOADING
    return None
