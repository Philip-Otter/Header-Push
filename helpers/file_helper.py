import sys
import os
import tempfile
from pathlib import Path
from typing import Optional, List
from configs import config_handler
from helpers import misc_helper
from dataschemes import plugin_module
from headerforge import forge, plugin

# way too tightly coupled right now


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

def get_file_details(path: Optional[Path], cfg: dict, pcfg: dict, overrides: Optional[dict] = None) -> dict:
    v = dict(cfg.get('defaults', {}))
    v.update(pcfg.get('header_defaults', {})
             if pcfg.get('enabled', True) else {})
    if overrides:
        v.update({k: x for k, x in overrides.items() if x is not None})
    v.update({'filename': path.name, 'filename_stem': path.stem, 'extension': path.suffix.lower(), 'relative_path': str(path)} if path else {
             'filename': 'ExampleFile.cs', 'filename_stem': 'ExampleFile', 'extension': '.cs', 'relative_path': 'ExampleFile.cs'})
    v['build_stage'] = config_handler.normalize_stage(v.get('build_stage'))
    v['created'] = misc_helper.created_label(v.get('created_date', ''))
    v['copyright_section'] = forge.format_copyright(v)
    v['license_section'] = f"License   : {v.get('license', '').strip()}" if v.get(
        'license', '').strip() else ''
    
    for _ in range(3):
        for k, x in list(v.items()):
            if isinstance(x, str):
                try:
                    v[k] = x.format(**v)
                except Exception:
                    pass
    return v

def iter_supported_files(root: Path, cfg: dict, pcfg: dict) -> List[Path]:
    langs = misc_helper.get_configured_languages(cfg, pcfg)
    if root.is_file():
        return [] if config_handler.should_ignore_path(root, root.parent, cfg, pcfg) or root.suffix.lower() not in langs else [root]
    return sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in langs and not config_handler.should_ignore_path(p, root, cfg, pcfg))
