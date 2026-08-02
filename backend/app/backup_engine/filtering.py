from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FilterSpec:
    extensions: list[str] | None = None
    min_size: int | None = None
    max_size: int | None = None

    def __post_init__(self) -> None:
        if self.extensions is not None:
            normalized = []
            for ext in self.extensions:
                ext = ext.strip().lower()
                if ext and not ext.startswith("."):
                    ext = "." + ext
                if ext:
                    normalized.append(ext)
            self.extensions = normalized or None

    def matches(self, path: Path, size: int) -> bool:
        if self.extensions is not None:
            if path.suffix.lower() not in set(self.extensions):
                return False
        if self.min_size is not None and size < self.min_size:
            return False
        if self.max_size is not None and size > self.max_size:
            return False
        return True
