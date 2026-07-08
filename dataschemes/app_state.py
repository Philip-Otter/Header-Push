from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
from dataschemes import plugin_module, file_record, staged_change

@dataclass
class AppState:
    files: List[file_record.FileRecord] = field(default_factory=list)
    staged: Dict[Path, staged_change.StagedChange] = field(default_factory=dict)
    plugins: List[plugin_module.PluginModule] = field(default_factory=list)
    last_push_backups: Dict[Path, Path] = field(default_factory=dict)