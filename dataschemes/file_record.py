from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileRecord:
    path: Path
    rel: str
    language: str
    status: str
    selected: bool = False