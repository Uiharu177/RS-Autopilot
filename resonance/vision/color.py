"""颜色模型：BGR 和 HSV 值封装，支持比较运算。

  BGR / HSV 对象支持：==、<=、< 比较（带 offset 容差）、迭代。
  用于：交易所按钮颜色检测、体力界面判断等场景。
"""

from __future__ import annotations
from typing import Iterator, Tuple


class BGR:
    def __init__(self, b: int, g: int, r: int, offset: int = 0) -> None:
        self.b = b
        self.g = g
        self.r = r
        self.offset = offset

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BGR):
            return (
                abs(self.b - other.b) <= self.offset
                and abs(self.g - other.g) <= self.offset
                and abs(self.r - other.r) <= self.offset
            )
        if isinstance(other, (list, tuple)):
            if len(other) == 3:
                other = BGR(*other)
                return (
                    abs(self.b - other.b) <= self.offset
                    and abs(self.g - other.g) <= self.offset
                    and abs(self.r - other.r) <= self.offset
                )
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __le__(self, other: BGR) -> bool:
        return (
            self.b <= other.b
            and self.g <= other.g
            and self.r <= other.r
        )

    def __lt__(self, other: BGR) -> bool:
        return (
            self.b < other.b
            and self.g < other.g
            and self.r < other.r
        )

    def __getitem__(self, index: int) -> int:
        return (self.b, self.g, self.r)[index]

    def __iter__(self) -> Iterator[int]:
        return iter((self.b, self.g, self.r))

    def __repr__(self) -> str:
        return f"BGR({self.b}, {self.g}, {self.r}, offset={self.offset})"


class HSV:
    def __init__(self, h: int, s: int, v: int, offset: int = 0) -> None:
        self.h = h
        self.s = s
        self.v = v
        self.offset = offset

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HSV):
            return (
                abs(self.h - other.h) <= self.offset
                and abs(self.s - other.s) <= self.offset
                and abs(self.v - other.v) <= self.offset
            )
        if isinstance(other, (list, tuple)):
            if len(other) == 3:
                other = HSV(*other)
                return (
                    abs(self.h - other.h) <= self.offset
                    and abs(self.s - other.s) <= self.offset
                    and abs(self.v - other.v) <= self.offset
                )
        return False

    def __le__(self, other: HSV) -> bool:
        return (
            self.h <= other.h
            and self.s <= other.s
            and self.v <= other.v
        )

    def __lt__(self, other: HSV) -> bool:
        return (
            self.h < other.h
            and self.s < other.s
            and self.v < other.v
        )

    def __getitem__(self, index: int) -> int:
        return (self.h, self.s, self.v)[index]

    def __iter__(self) -> Iterator[int]:
        return iter((self.h, self.s, self.v))

    def __repr__(self) -> str:
        return f"HSV({self.h}, {self.s}, {self.v}, offset={self.offset})"
