#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
from configs import config_handler
from helpers import json_helper, file_helper
from headerforge import forge, plugin
from gui import header_forge_gui
from pathlib import Path

try:
    import tkinter as tk
except Exception as exc:
    tk = filedialog = messagebox = ttk = None
    TK_IMPORT_ERROR = exc
else:
    TK_IMPORT_ERROR = None

def run_gui():
    """Run the GUI application."""
    if tk is None:
        raise RuntimeError(f'tkinter is not available: {TK_IMPORT_ERROR}')
    root = tk.Tk()
    
    header_forge_gui.HeaderForgeApp(root)
    root.mainloop()


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


def main() -> int:
    """This runs the main app"""
    ap = argparse.ArgumentParser(
        description='HeaderForge - unified managed developer header tool')
    ap.add_argument(
        '--config', help='Override HeaderForge user config file path for this session.')
    ap.add_argument('--scan')
    ap.add_argument('--apply')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--init-project')
    ap.add_argument('--init-plugin-dir')
    a = ap.parse_args()
    if a.init_project:
        root = Path(a.init_project)
        root.mkdir(parents=True, exist_ok=True)
        p = config_handler.get_project_config_path(root)
        if not p.exists():
            json_helper.save_json(p, config_handler.ConfigHandler.Default_Project_Config)
            print(f'CREATED: {p}')
        else:
            print(f'EXISTS: {p}')
        return 0
    if a.init_plugin_dir:
        root = Path(a.init_plugin_dir)
        root.mkdir(parents=True, exist_ok=True)
        pd = root/config_handler.ConfigHandler.Plugin_Directory
        pd.mkdir(parents=True, exist_ok=True)
        print(f'READY: {pd}')
        return 0
    if a.scan:
        return cli_scan(Path(a.scan))
    if a.apply:
        return cli_apply(Path(a.apply), a.dry_run)
    run_gui()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
