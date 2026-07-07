import sys
from pathlib import Path


def read_text_lossy(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding=sys.getdefaultencoding(), errors='replace')