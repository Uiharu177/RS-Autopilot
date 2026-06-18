from typing import Callable, Optional
from zipfile import ZipFile
from loguru import logger
import requests


def download_file(
    url: str,
    path: str,
    progress_changed: Optional[Callable[[int], None]] = None,
    update_finished: Optional[Callable[[bool], None]] = None,
):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get("content-length", 0))
        cur_size = 0
        with open(path, "wb") as f:
            for data in response.iter_content(1024):
                f.write(data)
                if progress_changed:
                    cur_size += len(data)
                    progress_changed(int(cur_size / total_size * 100))
        if update_finished:
            update_finished(True)
    else:
        logger.info(f"下载文件失败 - {path} - {response.status_code}")


def unzip(
    zip_path,
    extract_path,
    progress_changed: Optional[Callable[[int], None]] = None,
    update_finished: Optional[Callable[[bool], None]] = None,
):
    with ZipFile(zip_path, "r") as zip_ref:
        total_size = sum((file.file_size for file in zip_ref.infolist()))
        cur_size = 0
        for file in zip_ref.infolist():
            zip_ref.extract(member=file, path=extract_path)
            if progress_changed:
                cur_size += file.file_size
                progress_changed(int(cur_size / total_size * 100))
    if update_finished:
        update_finished(True)
