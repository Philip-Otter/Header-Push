from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PluginModule:
    name: str
    path: Path
    module: Any
    error: str = ''
