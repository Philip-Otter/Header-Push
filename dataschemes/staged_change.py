from dataclasses import dataclass
from pathlib import Path

@dataclass
class StagedChange:
    path: Path
    original: str
    updated: str
    operation: str
    
    @property
    def changed(self) -> bool: return self.original != self.updated