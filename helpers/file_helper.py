import sys
import os
import tempfile
from pathlib import Path


def read_text_lossy(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding=sys.getdefaultencoding(), errors='replace')

def atomic_write_text(path: Path, text: str) -> None:
    # Atomic-ish write: temp file in the same directory, flush/fsync, then os.replace.
    path = path.resolve()
    fd, tmp = tempfile.mkstemp(
        prefix=f'.{path.name}.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise