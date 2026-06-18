import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from loguru import logger
from pydantic import BaseModel

from resonance.utils.download_utils import download_file, unzip
from resonance.utils.utils import TEMP_PATH


class UpdateStatus(Enum):
    LATEST = 1
    UPDATE = 2
    FAILED = 0
    NOSUPPORT = 3
    FAILDCDK = 4


class Data(BaseModel):
    arch: str
    channel: str
    os: str
    release_note: str
    version_name: str
    version_number: int
    cdk_expired_time: Optional[float] = None
    custom_data: Optional[str] = None
    filesize: Optional[int] = None
    sha256: Optional[str] = None
    update_type: Optional[str] = None
    url: Optional[str] = None


class LatestInfoResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Data] = None


class BaseUpdateUtils(ABC):
    zip_name = "RS-Autopilot.zip"
    zip_path = TEMP_PATH / zip_name
    data: LatestInfoResponse = None

    @abstractmethod
    def get_latest_info(self, cdk: str) -> LatestInfoResponse:
        pass

    def get_update_status(self, cdk: str, reload: bool = False) -> UpdateStatus:
        if not getattr(sys, "frozen", False):
            return UpdateStatus.NOSUPPORT
        if not self.data or reload:
            self.data = self.get_latest_info(cdk=cdk)
        if not self.data:
            return UpdateStatus.FAILED
        elif self.data.code == 7002:
            return UpdateStatus.FAILDCDK
        elif self.data.code != 0:
            return UpdateStatus.FAILED
        elif self.data.msg == "current version is latest":
            return UpdateStatus.LATEST
        elif self.data.data.url:
            return UpdateStatus.UPDATE
        else:
            return UpdateStatus.FAILED
