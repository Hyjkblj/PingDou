"""Storage abstraction with a local development implementation."""

import hashlib
import shutil
from pathlib import Path

from app.core.config import get_settings


class LocalStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Invalid storage key")
        return target

    def write(self, key: str, content: bytes) -> Path:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self.path(key).is_file()

    def copy(self, source_key: str, target_key: str) -> Path:
        source = self.path(source_key)
        target = self.path(target_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    def size(self, key: str) -> int:
        return self.path(key).stat().st_size

    def sha256(self, key: str) -> str:
        digest = hashlib.sha256()
        with self.path(key).open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


storage = LocalStorage()
