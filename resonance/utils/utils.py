import json
from pathlib import Path
import sys
from typing import Any, List, Tuple, Union

from loguru import logger

ROOT_PATH = Path()
if getattr(sys, 'frozen', False):
    ROOT_PATH = Path(sys.executable).parent
RESOURCES_PATH = ROOT_PATH / "resources"
TEMP_PATH = ROOT_PATH / "temp"


def save_json(path: Path, data: Union[dict, list]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def read_json(path: Union[str, Path], default: Union[dict, list] = {}) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default


def compare_ranges(
    low: Union[Tuple[int, int, int], List[int]],
    x: Union[Tuple[int, int, int], List[int]],
    high: Union[Tuple[int, int, int], List[int]],
):
    low_0, low_1, low_2 = low
    x_0, x_1, x_2 = x
    high_0, high_1, high_2 = high
    return (
        (low_0 <= x_0 <= high_0)
        and (low_1 <= x_1 <= high_1)
        and (low_2 <= x_2 <= high_2)
    )
