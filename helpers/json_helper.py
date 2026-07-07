import json
from pathlib import Path

def clone_json(data: dict) -> dict: return json.loads(json.dumps(data))

def save_json(path: Path, data: dict) -> None:
    # Ensure profile/config directories exist before writing. This is what lets
    # the default user config live under AppData/HeaderForge instead of beside
    # the script.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding='utf-8', newline='\n')