import json
from pathlib import Path

def clone_json(data: dict) -> dict: return json.loads(json.dumps(data))

def save_json(path: Path, data: dict) -> None:
    # Ensure profile/config directories exist before writing. This is what lets
    # the default user config live under AppData/HeaderForge instead of beside
    # the script.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding='utf-8', newline='\n')

def deep_merge(base: dict, overlay: dict) -> dict:
    out = clone_json(base)
    for k, v in (overlay or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(
            v, dict) and isinstance(out.get(k), dict) else v
    return out

def load_json_if_exists(path: Path, default: dict) -> dict: return deep_merge(default,
                                                                              json.loads(path.read_text(encoding='utf-8'))) if path.exists() else clone_json(default)
