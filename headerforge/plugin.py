import sys
import importlib
import traceback
from dataschemes import plugin_module
from configs import config_handler
from typing import Optional, List, Iterable, Any
from dataschemes import plugin_module
from pathlib import Path

def load_plugins(global_cfg: dict, project_root: Optional[Path], project_cfg: dict) -> List[plugin_module.PluginModule]:
    paths = []
    if global_cfg.get('options', {}).get('global_plugins_enabled', True):
        gd = config_handler.get_user_config_dir()/config_handler.ConfigHandler.Plugin_Directory
        paths += sorted(gd.glob('*.py')) if gd.exists() else []
    if project_root and project_cfg.get('enabled', True) and project_cfg.get('plugins_enabled', True) and global_cfg.get('options', {}).get('project_plugins_enabled', True):
        root = project_root if project_root.is_dir() else project_root.parent
        pd = root/project_cfg.get('project_plugins_directory', config_handler.ConfigHandler.Plugin_Directory)
        paths += sorted(pd.glob('*.py')) if pd.exists() else []
    out = []
    for path in paths:
        try:
            name = f'hf_plugin_{path.stem}_{abs(hash(path))}'
            spec = importlib.util.spec_from_file_location(name, path)
            if not spec or not spec.loader:
                raise RuntimeError('Could not create import spec')
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            out.append(plugin_module.PluginModule(path.stem, path, mod))
        except Exception:
            out.append(plugin_module.PluginModule(path.stem, path,
                       None, traceback.format_exc()))
    return out

def plugin_call(plugins: Iterable[plugin_module.PluginModule], func_name: str, *args: Any) -> List[Any]:
    out = []
    for p in plugins:
        if p.error or p.module is None:
            continue
        f = getattr(p.module, func_name, None)
        if callable(f):
            try:
                out.append(f(*args))
            except Exception:
                p.error = traceback.format_exc()
    return out