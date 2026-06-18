import json
from dataclasses import asdict, dataclass
from typing import ClassVar


@dataclass
class WsMsg:
    data_types: ClassVar[list[type]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        WsMsg.data_types.append(cls)

    def serialize(self) -> str | bytes:
        d = asdict(self)
        d["type"] = self.type
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def construct_initial(cls) -> str | bytes | None:
        return None


@dataclass
class Log(WsMsg):
    type: ClassVar[str] = "log"
    data: str = ""

    @classmethod
    def construct_initial(cls):
        from resonance.utils.logger import log_lines
        if log_lines:
            return cls("\n".join(log_lines[-20:])).serialize()
        from pathlib import Path
        log_path = Path("logs/runtime.log")
        if log_path.exists():
            try:
                lines = log_path.read_text(encoding="utf-8").strip().split("\n")
                return cls("\n".join(lines[-20:])).serialize()
            except OSError:
                pass
        return cls("").serialize()


@dataclass
class Sc(WsMsg):
    type: ClassVar[str] = "sc"
    data: object = None

    def serialize(self) -> bytes:
        import cv2

        img = cv2.resize(self.data, (480, 270), interpolation=cv2.INTER_AREA)
        _, jpeg = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        result = jpeg.tobytes()

        import resonance.utils.screenshot_logger as _sl

        _sl.ws_screenshot = result
        return result

    @classmethod
    def construct_initial(cls):
        from resonance.utils.screenshot_logger import ws_screenshot

        return ws_screenshot
