from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from resonance.model.runtime import APP_PATH, Config, app
from resonance.utils.utils import read_json


class FileHandler(FileSystemEventHandler):
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path

    @property
    def data(self):
        return read_json(self.file_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(self.file_path):
            _app = Config.model_validate(self.data)
            for attr_name in app.__dict__.keys():
                setattr(app, attr_name, getattr(_app, attr_name))


event_handler = FileHandler(APP_PATH)
observer = Observer()
observer.schedule(event_handler, path=APP_PATH.parent, recursive=False)
observer.start()
