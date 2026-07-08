import shutil
from configs import config_handler
from pathlib import Path
from headerforge import plugin, forge
from helpers import file_helper

def cli_scan(path: Path) -> int:
    """This is a CLI command to scan for supported files in the given directory."""
    cfg = config_handler.load_config()
    pcfg = config_handler.load_project_config(path if path.is_dir() else path.parent)
    plugins = plugin.load_plugins(cfg, path if path.is_dir() else path.parent, pcfg)
    files = file_helper.iter_supported_files(path, cfg, pcfg, plugins)
    for f in files:
        print(f)
    print(f'Scanned {len(files)} file(s).')
    return 0


def cli_apply(path: Path, dry=False) -> int:
    """This is a CLI command to apply headers to files."""
    cfg = config_handler.load_config()
    pcfg = config_handler.load_project_config(path if path.is_dir() else path.parent)
    plugins = plugin.load_plugins(cfg, path if path.is_dir() else path.parent, pcfg)
    files = file_helper.iter_supported_files(path, cfg, pcfg, plugins)
    changed = 0
    for f in files:
        ch = forge.stage_change(f, cfg, pcfg, plugins, None)
        if ch.changed:
            changed += 1
            print(('WOULD CHANGE' if dry else 'CHANGED')+f': {f}')
            if not dry:
                if cfg.get('options', {}).get('backup_before_write', True):
                    shutil.copy2(f, f.with_name(
                        f.name+cfg.get('options', {}).get('backup_extension', '.bak')))
                file_helper.atomic_write_text(f, ch.updated)
        else:
            print(f'SKIPPED: {f}')
    print(f'Processed {len(files)} file(s). Changed {changed}.')
    return 0