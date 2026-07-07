#!/usr/bin/env python3

from __future__ import annotations

import argparse
import calendar
import difflib
import fnmatch
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception as exc:
    tk = filedialog = messagebox = ttk = None
    TK_IMPORT_ERROR = exc
else:
    TK_IMPORT_ERROR = None

APP_NAME = 'HeaderPush'
APP_VERSION = '1.0.0'
CONFIG_FILE = 'headerforge.json'
PROJECT_CONFIG_FILE = 'headerforge.project.json'
PLUGIN_DIR = 'headerforge_plugins'
CONFIG_OVERRIDE_PATH: Optional[Path] = None
HEADER_BEGIN = 'HEADERFORGE-BEGIN'
HEADER_END = 'HEADERFORGE-END'

DEFAULT_PROJECT_TYPE = ['script', 'application',
                          'library', 'service', 'module', 'tool']
DEFAULT_RISK_LEVELS = ['Low', 'Medium', 'High', 'Critical']
DEFAULT_BUILD_STAGES = ['Pre-Alpha', 'Alpha', 'Beta',
                        'Release Candidate', 'Release', 'Maintenance', 'Deprecated']
DEFAULT_PATCH_TYPES = ['Major', 'Minor', 'Patch',
                       'Bug-Fix', 'Security', 'Documentation', 'Maintenance']

DEFAULT_CONFIG = {
    'template_name': 'Standard Developer Header',
    'defaults': {
        'organization': 'Organization', 'artifact_type': 'script', 'name': '{filename_stem}', 'codename': '',
        'owner': 'Developer Name', 'title': 'Developer Position', 'created_date': date.today().isoformat(),
        'purpose': 'Describe what this script/service/module does.',
        'impact': 'Describe affected systems, users, workflows, or processes.',
        'risk': 'Low', 'build_stage': 'Alpha', 'patch_type': 'Minor', 'version': 'v1.0.0-alpha',
        'copyright_owner': 'Developer', 'copyright_start_year': '', 'copyright_end_year': str(date.today().year), 'license': ''},
    'settings': {'artifact_types': DEFAULT_PROJECT_TYPE, 'risk_levels': DEFAULT_RISK_LEVELS, 'build_stages': DEFAULT_BUILD_STAGES, 'patch_types': DEFAULT_PATCH_TYPES},
    'template_lines': ['; =============================================================================', '; {organization}', ';', '; Type        : {artifact_type}', '; Name        : {name}', '; Codename    : {codename}', '; Owner       : {owner}', '; Title       : {title}', '; Created     : {created}', ';', '; Purpose :', ';   {purpose}', ';', '; Impact :', ';   {impact}', ';', '; Risk Level :', ';   {risk}', ';', '; Build Stage :', ';   {build_stage}', ';', '; {patch_type} Patch: {version}', ';', '; {copyright_section}', '; {license_section}', '; ============================================================================='],
    'languages': {
        '.au3': {'name': 'AutoIt', 'style': 'line', 'line_prefix': '; ', 'block_open': '', 'block_close': ''},
        '.cs': {'name': 'C#', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/*', 'block_close': ' */'},
        '.py': {'name': 'Python', 'style': 'block', 'line_prefix': '', 'block_open': '\"\"\"', 'block_close': '\"\"\"'},
        '.ps1': {'name': 'PowerShell', 'style': 'block', 'line_prefix': '', 'block_open': '<#', 'block_close': '#>'},
        '.js': {'name': 'JavaScript', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/**', 'block_close': ' */'},
        '.ts': {'name': 'TypeScript', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/**', 'block_close': ' */'},
        '.java': {'name': 'Java', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/**', 'block_close': ' */'},
        '.go': {'name': 'Go', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/*', 'block_close': ' */'},
        '.c': {'name': 'C', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/*', 'block_close': ' */'},
        '.h': {'name': 'C/C++ Header', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/*', 'block_close': ' */'},
        '.cpp': {'name': 'C++', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/*', 'block_close': ' */'},
        '.hpp': {'name': 'C++ Header', 'style': 'block', 'line_prefix': ' * ', 'block_open': '/*', 'block_close': ' */'},
        '.html': {'name': 'HTML', 'style': 'block', 'line_prefix': '', 'block_open': '<!--', 'block_close': '-->'},
        '.xml': {'name': 'XML', 'style': 'block', 'line_prefix': '', 'block_open': '<!--', 'block_close': '-->'}},
    'options': {'backup_before_write': True, 'backup_extension': '.bak', 'global_plugins_enabled': True, 'project_plugins_enabled': True, 'skip_directories': ['.git', '.svn', '.hg', '.vs', '.vscode', 'bin', 'obj', 'node_modules', 'dist', 'build', '__pycache__'], 'ignore_globs': ['*.bak', '*.tmp', '*.generated.*'], 'preserve_shebang': True, 'preserve_xml_declaration': True, 'preserve_encoding_comment': True}}

DEFAULT_PROJECT_CONFIG = {'enabled': True, 'include_extensions': [], 'exclude_extensions': [], 'ignore_directories': ['bin', 'obj', '.git', '.vs', '.vscode'], 'ignore_files': [
], 'ignore_globs': ['*.bak', '*.tmp'], 'plugins_enabled': True, 'project_plugins_directory': PLUGIN_DIR, 'header_defaults': {}, 'template_lines': []}
FIELD_LABELS = {'organization': ['Organization'], 'artifact_type': ['Type', 'Artifact Type'], 'name': ['Name', 'Script', 'Application', 'Library'], 'codename': ['Codename', 'Code Name', 'Internal Codename'], 'owner': ['Owner'], 'title': ['Title'], 'created': [
    'Created'], 'purpose': ['Purpose'], 'impact': ['Impact'], 'risk': ['Risk Level', 'Risk'], 'build_stage': ['Build Stage', 'Release Stage', 'Stage', 'Pre-Release Stage'], 'patch_line': ['Patch'], 'copyright': ['Copyright'], 'license': ['License', 'Licensing']}
PATCH_LINE_RE = re.compile(
    r'^(?P<patch_type>.+?)\s+Patch\s*:\s*(?P<version>.+)$', re.I)

HELP_DOCS = '''HEADERFORGE HELP / ABOUT
=============================
HeaderForge creates, previews, stages, and atomically applies managed developer headers.
Managed headers are wrapped with HEADERFORGE-BEGIN and HEADERFORGE-END.

WORKFLOW
--------
1. Open Project
2. Scan
3. Select files in the Treeview
4. Edit Header Builder fields
5. Review Header / Diff / Full File
6. Stage
7. Push

PROJECT CONFIG
--------------
Each project can contain headerforge.project.json. Create or edit it from the Project Config tab.

Example:
{
  "enabled": true,
  "include_extensions": [".cs", ".au3", ".ps1"],
  "exclude_extensions": [],
  "ignore_directories": ["bin", "obj", ".git", "node_modules"],
  "ignore_files": ["AssemblyInfo.cs"],
  "ignore_globs": ["*.generated.cs", "*.designer.cs", "*.bak"],
  "plugins_enabled": true,
  "project_plugins_directory": "headerforge_plugins",
  "header_defaults": {"owner": "Philip Otter", "build_stage": "Beta"},
  "template_lines": []
}

CONFIG KEYS
-----------
include_extensions: if empty, all known extensions are eligible. If populated, only those extensions are scanned.
exclude_extensions: extensions to block.
ignore_directories: directory names skipped anywhere in the tree.
ignore_files: exact file names skipped.
ignore_globs: glob patterns skipped.
plugins_enabled: enables project plugins.
project_plugins_directory: project plugin folder.
header_defaults: project-specific header values.
template_lines: project-specific template. Empty means use global template.

PLUGIN SYSTEM
-------------
Plugins are plain Python files. Global plugins live beside this script in headerforge_plugins/*.py.
Project plugins live in <project>/headerforge_plugins/*.py.

Supported plugin functions:

register(app)
    Add UI, toolbar buttons, tabs, or text.

get_header_fields()
    Return extra fields as dictionaries:
    {"key":"change_ticket", "label":"Change Ticket", "kind":"entry", "default":""}
    {"key":"environment", "label":"Environment", "kind":"combo", "values":["Dev","Test","Prod"], "default":"Dev"}

get_template_lines(config)
    Return extra template lines, for example:
    ["; Change Ticket : {change_ticket}"]

should_ignore(path, project_root, config)
    Return True to ignore a file or folder.

alter_header_values(values, path, config)
    Change values before rendering. Return the modified dict.

render_template(values, path, config)
    Fully override the template core. Return a list of lines or a string.

PLUGIN APP API
--------------
app.add_toolbar_button(text, command)
app.add_tab(title)
app.add_text(parent, text)
app.info(title, message)
app.reload_plugins()
app.refresh_all()
app.cfg
app.project_cfg
app.project_root

SECURITY NOTE
-------------
Plugins are executable Python code. Only load trusted plugins. HeaderForge does not sandbox plugins.
'''


@dataclass
class PluginModule:
    name: str
    path: Path
    module: Any
    error: str = ''


@dataclass
class FileRecord:
    path: Path
    rel: str
    language: str
    status: str
    selected: bool = False


@dataclass
class StagedChange:
    path: Path
    original: str
    updated: str
    operation: str
    @property
    def changed(self) -> bool: return self.original != self.updated


@dataclass
class AppState:
    files: List[FileRecord] = field(default_factory=list)
    staged: Dict[Path, StagedChange] = field(default_factory=dict)
    plugins: List[PluginModule] = field(default_factory=list)
    last_push_backups: Dict[Path, Path] = field(default_factory=dict)


def app_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def clone_json(data: dict) -> dict: return json.loads(json.dumps(data))


def deep_merge(base: dict, overlay: dict) -> dict:
    out = clone_json(base)
    for k, v in (overlay or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(
            v, dict) and isinstance(out.get(k), dict) else v
    return out


def save_json(path: Path, data: dict) -> None:
    # Ensure profile/config directories exist before writing. This is what lets
    # the default user config live under AppData/HeaderForge instead of beside
    # the script.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding='utf-8', newline='\n')


def load_json_if_exists(path: Path, default: dict) -> dict: return deep_merge(default,
                                                                              json.loads(path.read_text(encoding='utf-8'))) if path.exists() else clone_json(default)


def user_config_dir() -> Path:
    # Windows desktop-app behavior: use roaming AppData. Non-Windows fallback
    # keeps the tool portable for Linux/macOS/dev containers.
    appdata = os.getenv('APPDATA')
    return Path(appdata)/'HeaderForge' if appdata else Path.home()/'.headerforge'


def user_config_path() -> Path: return user_config_dir()/CONFIG_FILE


def config_path() -> Path:
    # Override order: CLI --config, then HEADERFORGE_CONFIG, then AppData.
    if CONFIG_OVERRIDE_PATH is not None:
        return CONFIG_OVERRIDE_PATH.expanduser()
    env = os.getenv('HEADERFORGE_CONFIG')
    return Path(env).expanduser() if env else user_config_path()


def project_config_path(
    root: Path) -> Path: return (root if root.is_dir() else root.parent)/PROJECT_CONFIG_FILE


def migrate_config(cfg: dict) -> None:
    d = cfg.setdefault('defaults', {})
    if 'script' in d and 'name' not in d:
        d['name'] = d.pop('script')
    if 'stage' in d and 'build_stage' not in d:
        d['build_stage'] = normalize_stage(d.pop('stage'))
    d.setdefault('created_date', date.today().isoformat())
    d.setdefault('copyright_owner', d.get('organization', ''))
    d.setdefault('copyright_start_year', '')
    d.setdefault('copyright_end_year', str(date.today().year))
    d.setdefault('license', '')
    s = cfg.setdefault('settings', {})
    s.setdefault('artifact_types', DEFAULT_PROJECT_TYPE)
    s.setdefault('risk_levels', DEFAULT_RISK_LEVELS)
    s.setdefault('build_stages', DEFAULT_BUILD_STAGES)
    s.setdefault('patch_types', DEFAULT_PATCH_TYPES)


def load_config() -> dict:
    cfg = load_json_if_exists(config_path(), DEFAULT_CONFIG)
    migrate_config(cfg)
    return cfg


def load_project_config(root: Path) -> dict: return load_json_if_exists(
    project_config_path(root), DEFAULT_PROJECT_CONFIG)


def parse_created_date(value: str) -> date:
    if not value:
        return date.today()
    for fmt in ('%Y-%m-%d', '%B %d, %Y', '%B, %Y', '%b %d, %Y', '%b, %Y'):
        try:
            x = datetime.strptime(str(value).strip(), fmt)
            return x.date().replace(day=x.day if '%d' in fmt else 1)
        except ValueError:
            pass
    return date.today()


def created_label(
    value: str) -> str: return parse_created_date(value).strftime('%B, %Y')


def normalize_stage(value: str) -> str:
    raw = (value or '').strip()
    m = {'prealpha': 'Pre-Alpha', 'pre-alpha': 'Pre-Alpha', 'alpha': 'Alpha', 'beta': 'Beta', 'rc': 'Release Candidate',
         'release candidate': 'Release Candidate', 'release candidate (rc)': 'Release Candidate', 'stable': 'Release', 'production': 'Release', 'prod': 'Release'}
    return m.get(raw.lower(), raw or 'Alpha')


def read_text_lossy(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding=sys.getdefaultencoding(), errors='replace')


def write_text_atomic(path: Path, text: str) -> None:
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


def clean_header_line(line: str) -> str:
    s = html.unescape(line).rstrip('\r\n').strip()
    if s in ('/*', '/**', '*/', '<#', '#>', '<!--', '-->', '"""'):
        return ''
    for p in ('*', ';', '#', '//'):
        if s.startswith(p):
            return s[len(p):].strip()
    return s


def find_managed_header_bounds(content: str) -> Optional[Tuple[int, int]]:
    # Locate the HeaderForge markers, then expand to include the surrounding comment wrapper.
    b = content.find(HEADER_BEGIN)
    e = content.find(HEADER_END)
    if b < 0 or e < 0 or e < b:
        return None
    start = content.rfind('\n', 0, b)
    start = 0 if start < 0 else start+1
    end = content.find('\n', e)
    end = len(content) if end < 0 else end+1
    tail = content[end:end+140]
    for closer in (' */', '*/', '"""', '#>', '-->'):
        idx = tail.find(closer)
        if idx >= 0:
            ce = end+idx+len(closer)
            nl = content.find('\n', ce)
            end = len(content) if nl < 0 else nl+1
            break
    return start, end


def extract_managed_header(content: str) -> Optional[str]:
    b = find_managed_header_bounds(content)
    return None if not b else content[b[0]:b[1]]


def parse_managed_header_values(header_text: str) -> dict:
    lines = [clean_header_line(x) for x in header_text.splitlines()]
    lines = [x for x in lines if x and x not in (HEADER_BEGIN, HEADER_END)]
    values = {}
    for idx, line in enumerate(lines):
        pm = PATCH_LINE_RE.match(line)
        if pm:
            values['patch_type'] = pm.group('patch_type').strip()
            values['version'] = pm.group('version').strip()
            continue
        if ':' not in line:
            continue
        label, raw = [x.strip() for x in line.split(':', 1)]
        lower = label.lower()
        for key, labels in FIELD_LABELS.items():
            if lower in [x.lower() for x in labels]:
                if key == 'created':
                    values['created_date'] = parse_created_date(
                        raw).isoformat()
                elif key == 'build_stage':
                    values['build_stage'] = normalize_stage(raw)
                elif key == 'copyright':
                    values['copyright_owner'] = re.sub(
                        r'^©\s*[0-9\-]*\s*', '', raw).strip()
                elif key == 'license':
                    values['license'] = raw
                elif key != 'patch_line':
                    values[key] = raw
                break
        if lower in ('purpose', 'impact', 'risk level', 'risk', 'build stage') and not raw:
            c = []
            for nxt in lines[idx+1:]:
                if ':' in nxt:
                    break
                if nxt.strip('= -'):
                    c.append(nxt.strip())
            if c:
                target = 'risk' if lower in (
                    'risk level', 'risk') else 'build_stage' if lower == 'build stage' else lower
                values[target] = normalize_stage(
                    ' '.join(c)) if target == 'build_stage' else ' '.join(c)
    return values


def load_plugins(global_cfg: dict, project_root: Optional[Path], project_cfg: dict) -> List[PluginModule]:
    paths = []
    if global_cfg.get('options', {}).get('global_plugins_enabled', True):
        gd = user_config_dir()/PLUGIN_DIR
        paths += sorted(gd.glob('*.py')) if gd.exists() else []
    if project_root and project_cfg.get('enabled', True) and project_cfg.get('plugins_enabled', True) and global_cfg.get('options', {}).get('project_plugins_enabled', True):
        root = project_root if project_root.is_dir() else project_root.parent
        pd = root/project_cfg.get('project_plugins_directory', PLUGIN_DIR)
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
            out.append(PluginModule(path.stem, path, mod))
        except Exception:
            out.append(PluginModule(path.stem, path,
                       None, traceback.format_exc()))
    return out


def plugin_call(plugins: Iterable[PluginModule], func_name: str, *args: Any) -> List[Any]:
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


def configured_languages(cfg: dict, pcfg: dict) -> Dict[str, dict]:
    langs = dict(cfg.get('languages', {}))
    inc = {x.lower() for x in pcfg.get('include_extensions', []) if x}
    exc = {x.lower() for x in pcfg.get('exclude_extensions', []) if x}
    if inc:
        langs = {e: m for e, m in langs.items() if e.lower() in inc}
    if exc:
        langs = {e: m for e, m in langs.items() if e.lower() not in exc}
    return langs


def should_ignore_path(path: Path, root: Path, cfg: dict, pcfg: dict, plugins: List[PluginModule]) -> bool:
    base = root if root.is_dir() else root.parent
    try:
        rel = path.relative_to(base)
    except ValueError:
        rel = path
    if set(rel.parts) & (set(cfg.get('options', {}).get('skip_directories', [])) | set(pcfg.get('ignore_directories', []))):
        return True
    if path.name in set(pcfg.get('ignore_files', [])):
        return True
    pats = list(cfg.get('options', {}).get('ignore_globs', [])) + \
        list(pcfg.get('ignore_globs', []))
    rels = rel.as_posix()
    if any(fnmatch.fnmatch(path.name, p) or fnmatch.fnmatch(rels, p) for p in pats):
        return True
    return any(x is True for x in plugin_call(plugins, 'should_ignore', path, root, {'global': cfg, 'project': pcfg}))


def iter_supported_files(root: Path, cfg: dict, pcfg: dict, plugins: List[PluginModule]) -> List[Path]:
    langs = configured_languages(cfg, pcfg)
    if root.is_file():
        return [] if should_ignore_path(root, root.parent, cfg, pcfg, plugins) or root.suffix.lower() not in langs else [root]
    return sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in langs and not should_ignore_path(p, root, cfg, pcfg, plugins))


def split_preamble(content: str, suffix: str, cfg: dict) -> Tuple[str, str]:
    opts = cfg.get('options', {})
    lines = content.splitlines(True)
    pre = []
    if lines and opts.get('preserve_shebang', True) and lines[0].startswith('#!'):
        pre.append(lines.pop(0))
    if suffix.lower() == '.py' and opts.get('preserve_encoding_comment', True) and lines and ('coding' in lines[0] or 'encoding' in lines[0]) and lines[0].lstrip().startswith('#'):
        pre.append(lines.pop(0))
    if suffix.lower() == '.xml' and opts.get('preserve_xml_declaration', True) and lines and lines[0].lstrip().startswith('<?xml'):
        pre.append(lines.pop(0))
    return ''.join(pre), ''.join(lines)


def safe_format(line: str, values: dict) -> str:
    try:
        return line.format(**values)
    except KeyError as e:
        return line.replace('{'+str(e.args[0])+'}', f'<missing:{e.args[0]}>')


def strip_template(
    line: str) -> str: return line[2:] if line.startswith('; ') else '' if line == ';' else line


def format_copyright(values: dict) -> str:
    owner = (values.get('copyright_owner') or '').strip()
    if not owner:
        return ''
    end = (values.get('copyright_end_year') or '').strip() or str(
        parse_created_date(values.get('created_date', '')).year)
    start = (values.get('copyright_start_year') or '').strip()
    years = f'{start}-{end}' if start and start != end else end
    return f'Copyright : © {years} {owner}'


def file_values(path: Optional[Path], cfg: dict, pcfg: dict, plugins: List[PluginModule], overrides: Optional[dict] = None) -> dict:
    v = dict(cfg.get('defaults', {}))
    v.update(pcfg.get('header_defaults', {})
             if pcfg.get('enabled', True) else {})
    if overrides:
        v.update({k: x for k, x in overrides.items() if x is not None})
    v.update({'filename': path.name, 'filename_stem': path.stem, 'extension': path.suffix.lower(), 'relative_path': str(path)} if path else {
             'filename': 'ExampleFile.cs', 'filename_stem': 'ExampleFile', 'extension': '.cs', 'relative_path': 'ExampleFile.cs'})
    v['build_stage'] = normalize_stage(v.get('build_stage'))
    v['created'] = created_label(v.get('created_date', ''))
    v['copyright_section'] = format_copyright(v)
    v['license_section'] = f"License   : {v.get('license', '').strip()}" if v.get(
        'license', '').strip() else ''
    for res in plugin_call(plugins, 'alter_header_values', v, path, {'global': cfg, 'project': pcfg}):
        if isinstance(res, dict):
            v.update(res)
    for _ in range(3):
        for k, x in list(v.items()):
            if isinstance(x, str):
                try:
                    v[k] = x.format(**v)
                except Exception:
                    pass
    return v


def template_core(path: Path, cfg: dict, pcfg: dict, plugins: List[PluginModule], values: dict) -> List[str]:
    custom = plugin_call(plugins, 'render_template', values, path, {
                         'global': cfg, 'project': pcfg})
    if custom:
        r = custom[-1]
        return r.splitlines() if isinstance(r, str) else list(r)
    lines = list(pcfg.get('template_lines') or cfg.get('template_lines', []))
    for extra in plugin_call(plugins, 'get_template_lines', {'global': cfg, 'project': pcfg}):
        if isinstance(extra, list):
            lines += extra
    out = []
    for line in lines:
        if not values.get('copyright_section') and '{copyright_section}' in line:
            continue
        if not values.get('license_section') and '{license_section}' in line:
            continue
        out.append(safe_format(line, values).rstrip())
    return out


def build_header(path: Path, cfg: dict, pcfg: dict, plugins: List[PluginModule], overrides: Optional[dict] = None) -> str:
    lang = configured_languages(cfg, pcfg)[path.suffix.lower()]
    lp = lang.get('line_prefix', '')
    bo = lang.get('block_open', '')
    bc = lang.get('block_close', '')
    style = lang.get('style', 'block')
    vals = file_values(path, cfg, pcfg, plugins, overrides)
    lines = []
    if style == 'block' and bo:
        lines.append(bo)
    lines.append(f'{lp}{HEADER_BEGIN}')
    for line in template_core(path, cfg, pcfg, plugins, vals):
        c = strip_template(line)
        lines.append(f'{lp}{c}' if c else lp.rstrip())
    lines.append(f'{lp}{HEADER_END}')
    if style == 'block' and bc:
        lines.append(bc)
    return '\n'.join(lines).rstrip()+'\n\n'


def apply_header_to_text(content: str, suffix: str, header: str, cfg: dict) -> str:
    pre, body = split_preamble(content, suffix, cfg)
    b = find_managed_header_bounds(body)
    body = (body[:b[0]]+header+body[b[1]:].lstrip('\n')
            ) if b else header+body.lstrip('\n')
    return pre+body


def stage_change(path: Path, cfg: dict, pcfg: dict, plugins: List[PluginModule], overrides: Optional[dict]) -> StagedChange:
    original = read_text_lossy(path)
    existed = extract_managed_header(original) is not None
    updated = apply_header_to_text(original, path.suffix.lower(
    ), build_header(path, cfg, pcfg, plugins, overrides), cfg)
    op = 'Update Header' if existed and original != updated else 'Insert Header' if not existed and original != updated else 'No Change'
    return StagedChange(path, original, updated, op)


def unified_diff(change: StagedChange) -> str: return ''.join(difflib.unified_diff(change.original.splitlines(True),
                                                                                   change.updated.splitlines(True), fromfile=f'before/{change.path.name}', tofile=f'after/{change.path.name}'))


class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.window = None
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<Leave>', self.hide, add='+')

    def show(self, _=None):
        if self.window or not self.text:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(
            f'+{self.widget.winfo_rootx()+20}+{self.widget.winfo_rooty()+self.widget.winfo_height()+8}')
        ttk.Label(self.window, text=self.text, justify='left', padding=(
            8, 5), relief='solid', borderwidth=1, wraplength=420).pack()

    def hide(self, _=None):
        if self.window:
            self.window.destroy()
            self.window = None


class HeaderForgeApp:
    def __init__(self, root: 'tk.Tk'):
        self.root = root
        root.title(f'{APP_NAME} {APP_VERSION}')
        root.geometry('1720x1000')
        self.cfg = load_config()
        self.project_root = Path.cwd()
        self.project_cfg = load_project_config(self.project_root)
        self.state = AppState()
        self.field_vars = {}
        self.setting_widgets = {}
        self.status = tk.StringVar(
            value='Ready. Nothing gets created unless you explicitly ask.')
        self.filter_var = tk.StringVar(value='')
        self._style()
        self._shell()
        self.reload_plugins(initial=True)
        self._add_plugin_fields()
        self._load_fields()
        self.refresh_all(load_config_editor=False)
        self.log('Startup complete', 'READY')

    def _style(self):
        s = ttk.Style(self.root)
        try:
            if 'clam' in s.theme_names():
                s.theme_use('clam')
        except Exception:
            pass
        s.configure('Toolbar.TFrame', background='#20242c')
        s.configure('Toolbar.TButton', padding=(10, 6))
        s.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        s.configure('Metric.TLabel', font=(
            'Segoe UI', 18, 'bold'), foreground='#1f6feb')
        s.configure('Muted.TLabel', foreground='#666')

    def _group(self, title): g = ttk.LabelFrame(
        self.toolbar, text=title, padding=4); g.pack(side='left', padx=5); return g

    def _button(self, parent, text, cmd, tip=''):
        b = ttk.Button(parent, text=text, command=cmd, style='Toolbar.TButton')
        b.pack(side='left', padx=3, pady=2)
        if tip:
            ToolTip(b, tip)
        return b

    def _shell(self):
        self.toolbar = ttk.Frame(self.root, style='Toolbar.TFrame', padding=6)
        self.toolbar.pack(fill='x')
        self._toolbar()
        main = ttk.PanedWindow(self.root, orient='horizontal')
        main.pack(fill='both', expand=True, padx=8, pady=8)
        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=2)
        main.add(right, weight=6)
        self._file_browser(left)
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill='both', expand=True)
        self.dashboard_tab = ttk.Frame(self.tabs, padding=10)
        self.builder_tab = ttk.Frame(self.tabs, padding=10)
        self.preview_tab = ttk.Frame(self.tabs, padding=10)
        self.staged_tab = ttk.Frame(self.tabs, padding=10)
        self.settings_tab = ttk.Frame(self.tabs, padding=10)
        self.config_tab = ttk.Frame(self.tabs, padding=10)
        self.plugins_tab = ttk.Frame(self.tabs, padding=10)
        self.help_tab = ttk.Frame(self.tabs, padding=10)
        for tab, name in [(self.dashboard_tab, 'Dashboard'), (self.builder_tab, 'Header Builder'), (self.preview_tab, 'Preview'), (self.staged_tab, 'Staged Changes'), (self.settings_tab, 'Settings'), (self.config_tab, 'Project Config'), (self.plugins_tab, 'Plugins'), (self.help_tab, 'Help / About')]:
            self.tabs.add(tab, text=name)
        self._dashboard()
        self._builder()
        self._preview()
        self._staged()
        self._settings()
        self._config()
        self._plugins()
        self._help()
        bar = ttk.Frame(self.root, padding=(8, 2))
        bar.pack(fill='x')
        ttk.Label(bar, textvariable=self.status).pack(side='left')

    def _toolbar(self):
        p = self._group('Project')
        self._button(p, 'Open Project', self.open_project,
                     'Pick target folder. Does not create files.')
        self._button(p, 'Scan', self.scan,
                     'Scan supported files and preserve selections.')
        h = self._group('Header')
        self._button(h, 'Import Header', self.import_selected_header,
                     'Import fields from selected managed header.')
        self._button(h, 'Reset Fields', self.reset_fields, 'Reload defaults.')
        s = self._group('Stage')
        self._button(s, 'Stage Selected', self.stage_selected,
                     'Build in-memory changes only.')
        self._button(s, 'Review Staged', self.show_staged_diff,
                     'Diff all staged changes.')
        self._button(s, 'Clear Staged', self.clear_staged,
                     'Clear staged list.')
        pub = self._group('Publish')
        self._button(pub, 'Push Staged', self.push_staged,
                     'Write staged changes atomically.')
        self._button(pub, 'Undo Last Push', self.undo_last_push,
                     'Restore backups from last push.')
        t = self._group('Tools')
        self._button(t, 'Create Project Config', self.create_project_config,
                     'Explicitly create project config.')
        self._button(t, 'Create Plugin Dir', self.create_plugin_dir,
                     'Explicitly create plugin directory.')
        self._button(t, 'Sample Plugin', self.create_sample_plugin,
                     'Explicitly create starter plugin.')
        self._button(t, 'Reload Plugins', self.reload_plugins,
                     'Reload trusted plugins.')
        self._button(t, 'Help', lambda: self.tabs.select(
            self.help_tab), 'Open docs.')

    def add_toolbar_button(self, text, command): return self._button(
        self._group('Plugin'), text, command, 'Plugin-provided action.')

    def add_tab(self, title): f = ttk.Frame(
        self.tabs, padding=10); self.tabs.add(f, text=title); return f

    def add_text(self, parent, text): w = tk.Text(parent, wrap='word'); w.pack(
        fill='both', expand=True); w.insert('1.0', text); return w

    def info(self, title, msg): messagebox.showinfo(title, msg)

    def log(self, msg, level='INFO'):
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {level}: {msg}\n"
        if hasattr(self, 'operation_log'):
            self.operation_log.insert('end', line)
            self.operation_log.see('end')
        self.status.set(f'{level}: {msg}')

    def _file_browser(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill='x', pady=(0, 6))
        ttk.Label(top, text='File Browser',
                  style='Title.TLabel').pack(side='left')
        ttk.Button(top, text='All', command=lambda: self.set_selection(
            True)).pack(side='right')
        ttk.Button(top, text='None', command=lambda: self.set_selection(
            False)).pack(side='right')
        fr = ttk.Frame(parent)
        fr.pack(fill='x', pady=(0, 6))
        ttk.Label(fr, text='Filter:').pack(side='left')
        e = ttk.Entry(fr, textvariable=self.filter_var)
        e.pack(side='left', fill='x', expand=True, padx=4)
        ToolTip(e, 'Filter without losing selection.')
        self.filter_var.trace_add('write', lambda *_: self.populate_tree())
        cols = ('selected', 'status', 'language', 'path')
        self.tree = ttk.Treeview(parent, columns=cols,
                                 show='tree headings', selectmode='browse')
        for c, t, w in [('#0', 'File', 250), ('selected', 'Use', 50), ('status', 'Header', 105), ('language', 'Language', 95), ('path', 'Relative Path', 460)]:
            self.tree.heading(c, text=t)
            self.tree.column(
                c, width=w, anchor='center' if c == 'selected' else 'w')
        y = ttk.Scrollbar(parent, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)
        self.tree.pack(side='left', fill='both', expand=True)
        y.pack(side='right', fill='y')
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.refresh_previews())

    def _dashboard(self):
        ttk.Label(self.dashboard_tab, text='Project Dashboard',
                  style='Title.TLabel').pack(anchor='w')
        self.metrics_frame = ttk.Frame(self.dashboard_tab)
        self.metrics_frame.pack(fill='x', pady=10)
        self.dashboard_text = tk.Text(
            self.dashboard_tab, wrap='word', height=14)
        self.dashboard_text.pack(fill='both', expand=True)
        ttk.Label(self.dashboard_tab, text='Operation Log',
                  style='Title.TLabel').pack(anchor='w', pady=(10, 0))
        self.operation_log = tk.Text(
            self.dashboard_tab, wrap='word', height=10)
        self.operation_log.pack(fill='both', expand=True)

    def _builder(self):
        # Builder-owned actions live here, not on the global toolbar. These
        # controls act on the current header profile/template the user is editing.
        actions = ttk.LabelFrame(
            self.builder_tab, text='Builder Defaults / Templates', padding=8)
        actions.pack(fill='x', pady=(0, 8))
        profile = ttk.Frame(actions)
        profile.pack(fill='x', pady=(0, 4))
        ttk.Label(profile, text='Profile Actions:',
                  style='Muted.TLabel').pack(side='left', padx=(0, 8))
        self._builder_button(profile, 'Save User Defaults', self.save_user_defaults,
                             'Save current builder fields to the user config file.')
        self._builder_button(profile, 'Load User Defaults',
                             self.load_user_defaults, 'Reload values from the user config file.')
        self._builder_button(profile, 'Reset Built-In Defaults', self.reset_builtin_defaults,
                             'Reset this session to built-in defaults without deleting your saved user config.')
        self._builder_button(profile, 'Override Config File', self.override_config_file,
                             'Use a different config JSON file for this session.')
        templates = ttk.Frame(actions)
        templates.pack(fill='x')
        ttk.Label(templates, text='Template Actions:',
                  style='Muted.TLabel').pack(side='left', padx=(0, 8))
        self._builder_button(templates, 'Export Template', self.export_template,
                             'Export current defaults/settings/template to a JSON template file.')
        self._builder_button(templates, 'Import Template', self.import_template,
                             'Import a JSON template and load it into the builder.')
        self.config_location_var = tk.StringVar(
            value=f'User config: {config_path()}')
        ttk.Label(actions, textvariable=self.config_location_var,
                  style='Muted.TLabel').pack(anchor='w', pady=(6, 0))
        canvas = tk.Canvas(self.builder_tab, highlightthickness=0)
        scroll = ttk.Scrollbar(
            self.builder_tab, orient='vertical', command=canvas.yview)
        self.builder_frame = ttk.Frame(canvas)
        self.builder_frame.bind('<Configure>', lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.builder_frame, anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self._builder_row = 0
        self._add_standard_fields()

    def _builder_button(self, parent, text, command, tip=''):
        b = ttk.Button(parent, text=text, command=command)
        b.pack(side='left', padx=3, pady=2)
        if tip:
            ToolTip(b, tip)
        return b

    def settings_list(self, key, fallback): return list(
        self.cfg.get('settings', {}).get(key, fallback))

    def _tip(self, key):
        return {'artifact_type': 'Edit available values in Settings.', 'risk': 'Low/Medium/High/Critical style impact tag. Edit in Settings.', 'build_stage': 'Pre-Alpha, Alpha, Beta, Release Candidate, Release, Maintenance, Deprecated.', 'patch_type': 'Change intent/version category. Edit in Settings.', 'purpose': 'What this code exists to do.', 'impact': 'Systems/users/workflows affected.', 'created_date': 'Stored as full date, displayed as Month, Year.'}.get(key, 'Header value used during render.')

    def _add_field(self, key, label, kind='entry', values=None, default=''):
        r = self._builder_row
        self._builder_row += 1
        lab = ttk.Label(self.builder_frame, text=label+':')
        lab.grid(row=r, column=0, sticky='nw', padx=(0, 8), pady=4)
        ToolTip(lab, self._tip(key))
        var = tk.StringVar(value=default)
        self.field_vars[key] = var
        if kind == 'text':
            w = tk.Text(self.builder_frame, height=4, width=90, wrap='word')
            w.grid(row=r, column=1, sticky='ew', pady=4)
            w.bind('<KeyRelease>', lambda e, k=key, x=w: self._sync_text(k, x))
            setattr(self, f'field_widget_{key}', w)
        elif kind == 'combo':
            w = ttk.Combobox(self.builder_frame,
                             textvariable=var, values=values or [])
            w.grid(row=r, column=1, sticky='ew', pady=4)
            var.trace_add('write', lambda *_: self.refresh_previews())
        elif kind == 'date':
            box = ttk.Frame(self.builder_frame)
            box.grid(row=r, column=1, sticky='ew', pady=4)
            self.year_var = tk.StringVar()
            self.month_var = tk.StringVar()
            self.day_var = tk.StringVar()
            ttk.Combobox(box, width=8, textvariable=self.year_var, values=[str(
                y) for y in range(1995, date.today().year+11)], state='readonly').pack(side='left')
            ttk.Combobox(box, width=12, textvariable=self.month_var, values=list(
                calendar.month_name)[1:], state='readonly').pack(side='left', padx=4)
            ttk.Combobox(box, width=4, textvariable=self.day_var, values=[
                         str(d) for d in range(1, 32)], state='readonly').pack(side='left')
            ttk.Label(box, text='Header displays Month, Year',
                      style='Muted.TLabel').pack(side='left', padx=8)
            for v in (self.year_var, self.month_var, self.day_var):
                v.trace_add('write', lambda *_: self._date_changed())
        else:
            w = ttk.Entry(self.builder_frame, textvariable=var)
            w.grid(row=r, column=1, sticky='ew', pady=4)
            var.trace_add('write', lambda *_: self.refresh_previews())
        if 'w' in locals():
            ToolTip(w, self._tip(key))
        self.builder_frame.columnconfigure(1, weight=1)

    def _add_standard_fields(self):
        for args in [('organization', 'Organization'), ('artifact_type', 'Artifact Type', 'combo', self.settings_list('artifact_types', DEFAULT_PROJECT_TYPE)), ('name', 'Name'), ('codename', 'Codename'), ('owner', 'Owner'), ('title', 'Title'), ('created_date', 'Created Date', 'date'), ('purpose', 'Purpose', 'text'), ('impact', 'Impact', 'text'), ('risk', 'Risk', 'combo', self.settings_list('risk_levels', DEFAULT_RISK_LEVELS)), ('build_stage', 'Build Stage', 'combo', self.settings_list('build_stages', DEFAULT_BUILD_STAGES)), ('patch_type', 'Patch Type', 'combo', self.settings_list('patch_types', DEFAULT_PATCH_TYPES)), ('version', 'Version'), ('copyright_owner', 'Copyright Owner'), ('copyright_start_year', 'Copyright Start Year'), ('copyright_end_year', 'Copyright End Year'), ('license', 'License')]:
            self._add_field(*args)

    def _add_plugin_fields(self):
        for fields in plugin_call(self.state.plugins, 'get_header_fields'):
            if isinstance(fields, list):
                for f in fields:
                    if isinstance(f, dict) and f.get('key') not in self.field_vars:
                        self._add_field(f.get('key'), f.get('label', f.get('key')), f.get(
                            'kind', 'entry'), f.get('values'), f.get('default', ''))

    def _text_area(self, parent):
        f = ttk.Frame(parent)
        f.pack(fill='both', expand=True)
        t = tk.Text(f, wrap='none')
        y = ttk.Scrollbar(f, orient='vertical', command=t.yview)
        x = ttk.Scrollbar(f, orient='horizontal', command=t.xview)
        t.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        t.grid(row=0, column=0, sticky='nsew')
        y.grid(row=0, column=1, sticky='ns')
        x.grid(row=1, column=0, sticky='ew')
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        return t

    def _preview(self):
        paned = ttk.PanedWindow(self.preview_tab, orient='vertical')
        paned.pack(fill='both', expand=True)
        top = ttk.PanedWindow(paned, orient='horizontal')
        bot = ttk.Frame(paned)
        paned.add(top, weight=2)
        paned.add(bot, weight=3)
        hf = ttk.LabelFrame(top, text='Header Preview', padding=4)
        df = ttk.LabelFrame(top, text='Diff Preview', padding=4)
        top.add(hf, weight=1)
        top.add(df, weight=1)
        ff = ttk.LabelFrame(bot, text='Full File Preview', padding=4)
        ff.pack(fill='both', expand=True)
        self.header_preview = self._text_area(hf)
        self.diff_preview = self._text_area(df)
        self.full_preview = self._text_area(ff)

    def _staged(self):
        top = ttk.Frame(self.staged_tab)
        top.pack(fill='x', pady=(0, 6))
        ttk.Label(top, text='Staged Changes',
                  style='Title.TLabel').pack(side='left')
        ttk.Button(top, text='Remove Selected',
                   command=self.remove_selected_staged).pack(side='right')
        ttk.Button(top, text='Review Selected Diff',
                   command=self.review_selected_staged).pack(side='right', padx=4)
        self.staged_tree = ttk.Treeview(self.staged_tab, columns=(
            'operation', 'changed', 'path'), show='headings', selectmode='extended')
        for c, t, w in [('operation', 'Operation', 160), ('changed', 'Changed', 90), ('path', 'Path', 900)]:
            self.staged_tree.heading(c, text=t)
            self.staged_tree.column(
                c, width=w, anchor='center' if c != 'path' else 'w')
        y = ttk.Scrollbar(self.staged_tab, orient='vertical',
                          command=self.staged_tree.yview)
        self.staged_tree.configure(yscrollcommand=y.set)
        self.staged_tree.pack(side='left', fill='both', expand=True)
        y.pack(side='right', fill='y')

    def _settings(self):
        ttk.Label(self.settings_tab, text='Editable Settings',
                  style='Title.TLabel').pack(anchor='w')
        ttk.Label(self.settings_tab, text='One value per line. Save User Config writes to your HeaderForge user config path only when clicked.',
                  style='Muted.TLabel').pack(anchor='w')
        grid = ttk.Frame(self.settings_tab)
        grid.pack(fill='both', expand=True)
        for idx, (key, title, fallback) in enumerate([('artifact_types', 'Artifact Types', DEFAULT_PROJECT_TYPE), ('risk_levels', 'Risk Levels', DEFAULT_RISK_LEVELS), ('build_stages', 'Build Stages', DEFAULT_BUILD_STAGES), ('patch_types', 'Patch Types', DEFAULT_PATCH_TYPES)]):
            lf = ttk.LabelFrame(grid, text=title, padding=6)
            lf.grid(row=idx//2, column=idx % 2, sticky='nsew', padx=5, pady=5)
            tx = tk.Text(lf, height=12, width=42)
            tx.pack(fill='both', expand=True)
            tx.insert('1.0', '\n'.join(self.settings_list(key, fallback)))
            self.setting_widgets[key] = tx
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        btn = ttk.Frame(self.settings_tab)
        btn.pack(fill='x', pady=6)
        ttk.Button(btn, text='Apply In Memory',
                   command=self.apply_settings_in_memory).pack(side='left')
        ttk.Button(btn, text='Save User Config',
                   command=self.save_global_config).pack(side='left', padx=4)

    def _config(self):
        top = ttk.Frame(self.config_tab)
        top.pack(fill='x', pady=(0, 6))
        ttk.Label(top, text='Project Config',
                  style='Title.TLabel').pack(side='left')
        ttk.Button(top, text='Load Existing',
                   command=self.load_project_config_into_editor).pack(side='right')
        ttk.Button(top, text='Create', command=self.create_project_config).pack(
            side='right', padx=4)
        ttk.Button(top, text='Save', command=self.save_project_config).pack(
            side='right')
        self.config_state = ttk.Label(
            self.config_tab, text='', style='Muted.TLabel')
        self.config_state.pack(anchor='w')
        self.config_text = tk.Text(self.config_tab, wrap='none')
        self.config_text.pack(fill='both', expand=True)

    def _plugins(self):
        top = ttk.Frame(self.plugins_tab)
        top.pack(fill='x', pady=(0, 6))
        ttk.Label(top, text='Plugin Manager',
                  style='Title.TLabel').pack(side='left')
        ttk.Button(top, text='Create Plugin Dir',
                   command=self.create_plugin_dir).pack(side='right')
        ttk.Button(top, text='Sample Plugin', command=self.create_sample_plugin).pack(
            side='right', padx=4)
        ttk.Button(top, text='Reload',
                   command=self.reload_plugins).pack(side='right')
        self.plugins_tree = ttk.Treeview(self.plugins_tab, columns=(
            'status', 'name', 'path', 'error'), show='headings')
        for c, t, w in [('status', 'Status', 90), ('name', 'Name', 180), ('path', 'Path', 620), ('error', 'Error', 500)]:
            self.plugins_tree.heading(c, text=t)
            self.plugins_tree.column(c, width=w, anchor='w')
        self.plugins_tree.pack(fill='both', expand=True)

    def _help(self): self.help_text = tk.Text(self.help_tab, wrap='word'); self.help_text.pack(
        fill='both', expand=True); self.help_text.insert('1.0', HELP_DOCS); self.help_text.configure(state='disabled')

    def _sync_text(self, key, w): self.field_vars[key].set(
        w.get('1.0', 'end-1c')); self.refresh_previews()

    def _date_changed(self):
        try:
            y = int(self.year_var.get())
            m = list(calendar.month_name).index(self.month_var.get())
            d = min(int(self.day_var.get()), calendar.monthrange(y, m)[1])
            self.field_vars['created_date'].set(date(y, m, d).isoformat())
        except Exception:
            return
        self.refresh_previews()

    def _set_created(self, value): dt = parse_created_date(value); self.year_var.set(str(dt.year)); self.month_var.set(
        calendar.month_name[dt.month]); self.day_var.set(str(dt.day)); self.field_vars['created_date'].set(dt.isoformat())

    def _load_fields(self):
        vals = file_values(None, self.cfg, self.project_cfg,
                           self.state.plugins, None)
        for k, v in self.field_vars.items():
            val = str(vals.get(k, v.get()))
            if k in ('purpose', 'impact'):
                w = getattr(self, f'field_widget_{k}')
                w.delete('1.0', 'end')
                w.insert('1.0', val)
                v.set(val)
            elif k == 'created_date':
                self._set_created(val)
            else:
                v.set(val)

    def get_overrides(self): d = {k: v.get() for k, v in self.field_vars.items(
    )}; d['build_stage'] = normalize_stage(d.get('build_stage')); return d

    def current_user_config(self) -> dict:
        # Persist the user's current builder profile plus editable dropdown
        # settings. Project-specific file selections/staged changes are not user defaults.
        cfg = deep_merge(DEFAULT_CONFIG, self.cfg)
        cfg['defaults'].update(self.get_overrides())
        if hasattr(self, 'setting_widgets'):
            cfg.setdefault('settings', {})
            for k, w in self.setting_widgets.items():
                vals = [x.strip() for x in w.get(
                    '1.0', 'end-1c').splitlines() if x.strip()]
                if vals:
                    cfg['settings'][k] = vals
        migrate_config(cfg)
        return cfg

    def set_config_location_label(self):
        if hasattr(self, 'config_location_var'):
            self.config_location_var.set(f'User config: {config_path()}')

    def save_user_defaults(self):
        try:
            self.cfg = self.current_user_config()
            save_json(config_path(), self.cfg)
            self.set_config_location_label()
            self.update_dashboard()
            self.refresh_previews()
            self.log(f'Saved user defaults: {config_path()}', 'SUCCESS')
            messagebox.showinfo(
                APP_NAME, f'Saved user defaults to:\n\n{config_path()}')
        except Exception as e:
            messagebox.showerror(
                APP_NAME, f'Could not save user defaults:\n\n{e}')
            self.log(f'Failed to save user defaults: {e}', 'ERROR')

    def load_user_defaults(self):
        try:
            self.cfg = load_config()
            self._load_fields()
            self.set_config_location_label()
            self.update_dashboard()
            self.refresh_previews()
            self.log(f'Loaded user defaults: {config_path()}', 'SUCCESS')
        except Exception as e:
            messagebox.showerror(
                APP_NAME, f'Could not load user defaults:\n\n{e}')
            self.log(f'Failed to load user defaults: {e}', 'ERROR')

    def reset_builtin_defaults(self):
        # Session-only reset. This intentionally does not delete the AppData file.
        self.cfg = clone_json(DEFAULT_CONFIG)
        migrate_config(self.cfg)
        self._load_fields()
        self.set_config_location_label()
        self.update_dashboard()
        self.refresh_previews()
        self.log(
            'Reset current builder fields to built-in defaults. Saved user config was not deleted.', 'SUCCESS')

    def override_config_file(self):
        global CONFIG_OVERRIDE_PATH
        chosen = filedialog.asksaveasfilename(title='Use HeaderForge Config File', defaultextension='.json', filetypes=[
                                              ('JSON files', '*.json'), ('All files', '*.*')], initialfile=CONFIG_FILE)
        if not chosen:
            self.log('Config override canceled.')
            return
        CONFIG_OVERRIDE_PATH = Path(chosen)
        if CONFIG_OVERRIDE_PATH.exists():
            self.cfg = load_config()
        else:
            self.cfg = self.current_user_config()
            save_json(CONFIG_OVERRIDE_PATH, self.cfg)
        self._load_fields()
        self.set_config_location_label()
        self.update_dashboard()
        self.refresh_previews()
        self.log(
            f'Using config override for this session: {CONFIG_OVERRIDE_PATH}', 'SUCCESS')

    def export_template(self):
        path = filedialog.asksaveasfilename(title='Export HeaderForge Template', defaultextension='.json', filetypes=[
                                            ('JSON files', '*.json'), ('All files', '*.*')], initialfile='headerforge-template.json')
        if not path:
            self.log('Export template canceled.')
            return
        data = {'template_name': self.cfg.get('template_name', 'Custom HeaderForge Template'), 'defaults': self.get_overrides(
        ), 'settings': self.cfg.get('settings', {}), 'template_lines': self.cfg.get('template_lines', [])}
        try:
            save_json(Path(path), data)
            self.log(f'Exported template: {path}', 'SUCCESS')
        except Exception as e:
            messagebox.showerror(
                APP_NAME, f'Could not export template:\n\n{e}')
            self.log(f'Failed to export template: {e}', 'ERROR')

    def import_template(self):
        path = filedialog.askopenfilename(title='Import HeaderForge Template', filetypes=[
                                          ('JSON files', '*.json'), ('All files', '*.*')])
        if not path:
            self.log('Import template canceled.')
            return
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            if isinstance(data.get('defaults'), dict):
                self.cfg.setdefault('defaults', {}).update(data['defaults'])
            if isinstance(data.get('settings'), dict):
                self.cfg.setdefault('settings', {}).update(data['settings'])
            if isinstance(data.get('template_lines'), list):
                self.cfg['template_lines'] = data['template_lines']
            if data.get('template_name'):
                self.cfg['template_name'] = str(data['template_name'])
            migrate_config(self.cfg)
            self._load_fields()
            self.refresh_previews()
            self.update_dashboard()
            self.log(f'Imported template: {path}', 'SUCCESS')
        except Exception as e:
            messagebox.showerror(
                APP_NAME, f'Could not import template:\n\n{e}')
            self.log(f'Failed to import template: {e}', 'ERROR')

    def capture_selected_paths(self): return {
        r.path for r in self.state.files if r.selected}

    def update_config_state(self):
        p = project_config_path(self.project_root)
        self.config_state.configure(
            text=f"Project config: {'Found' if p.exists() else 'Not found'} - {p}")
        if not p.exists():
            self.config_text.delete('1.0', 'end')
            self.config_text.insert('1.0', json.dumps(
                DEFAULT_PROJECT_CONFIG, indent=4))

    def open_project(self):
        s = filedialog.askdirectory(initialdir=str(self.project_root))
        if not s:
            self.log('Open Project canceled')
            return
        self.project_root = Path(s)
        self.project_cfg = load_project_config(self.project_root)
        self.config_text.delete('1.0', 'end')
        self.update_config_state()
        self.reload_plugins(initial=True)
        self._load_fields()
        self.scan()
        self.log(f'Opened project: {self.project_root}', 'SUCCESS')

    def load_project_config_into_editor(self):
        p = project_config_path(self.project_root)
        if not p.exists():
            self.update_config_state()
            self.log(f'Project config not found. Nothing was created: {p}')
            return
        self.project_cfg = load_project_config(self.project_root)
        self.config_text.delete('1.0', 'end')
        self.config_text.insert('1.0', json.dumps(self.project_cfg, indent=4))
        self.update_config_state()
        self.log(f'Loaded project config: {p}', 'SUCCESS')

    def create_project_config(self):
        p = project_config_path(self.project_root)
        if p.exists():
            self.log(f'Project config already exists: {p}')
            self.load_project_config_into_editor()
            return
        save_json(p, DEFAULT_PROJECT_CONFIG)
        self.project_cfg = load_project_config(self.project_root)
        self.load_project_config_into_editor()
        self.log(f'Created project config: {p}', 'SUCCESS')

    def save_project_config(self):
        try:
            self.project_cfg = deep_merge(DEFAULT_PROJECT_CONFIG, json.loads(
                self.config_text.get('1.0', 'end-1c').strip() or json.dumps(self.project_cfg)))
            save_json(project_config_path(self.project_root), self.project_cfg)
            selected = self.capture_selected_paths()
            self.reload_plugins(initial=True)
            self.scan(preserved_selection=selected)
            self.update_config_state()
            self.log(
                f'Saved project config: {project_config_path(self.project_root)}', 'SUCCESS')
        except Exception as e:
            messagebox.showerror(
                APP_NAME, f'Invalid project config JSON:\n\n{e}')
            self.log(f'Failed to save project config: {e}', 'ERROR')

    def apply_settings_in_memory(self):
        self.cfg.setdefault('settings', {})
        for k, w in self.setting_widgets.items():
            vals = [x.strip()
                    for x in w.get('1.0', 'end-1c').splitlines() if x.strip()]
            if vals:
                self.cfg['settings'][k] = vals
        self.log(
            'Applied settings in memory. Restart app to refresh existing combo dropdown lists fully.', 'SUCCESS')
        self.refresh_previews()

    def save_global_config(self): self.apply_settings_in_memory(); save_json(config_path(
    ), self.cfg); self.set_config_location_label(); self.log(f'Saved user config: {config_path()}', 'SUCCESS')

    def create_plugin_dir(self):
        root = self.project_root if self.project_root.is_dir() else self.project_root.parent
        pd = root/self.project_cfg.get('project_plugins_directory', PLUGIN_DIR)
        pd.mkdir(parents=True, exist_ok=True)
        self.log(f'Created/verified plugin directory: {pd}', 'SUCCESS')
        self.reload_plugins(initial=True)

    def create_sample_plugin(self):
        root = self.project_root if self.project_root.is_dir() else self.project_root.parent
        pd = root/self.project_cfg.get('project_plugins_directory', PLUGIN_DIR)
        pd.mkdir(parents=True, exist_ok=True)
        sample = pd/'sample_headerforge_plugin.py'
        if sample.exists():
            self.log(f'Sample plugin already exists: {sample}')
            return
        sample.write_text(
            '"Sample HeaderForge plugin."\n\ndef get_header_fields():\n    return [{"key":"change_ticket","label":"Change Ticket","kind":"entry","default":""}]\n\ndef get_template_lines(config):\n    return ["; Change Ticket : {change_ticket}"]\n', encoding='utf-8')
        self.log(f'Created sample plugin: {sample}', 'SUCCESS')
        self.reload_plugins(initial=True)

    def reload_plugins(self, initial=False):
        self.state.plugins = load_plugins(
            self.cfg, self.project_root, self.project_cfg)
        for p in self.state.plugins:
            if not p.error and callable(getattr(p.module, 'register', None)):
                try:
                    p.module.register(self)
                except Exception:
                    p.error = traceback.format_exc()
        self.update_plugin_tree()
        if not initial:
            self.log(
                f"Reloaded plugins. OK: {sum(1 for p in self.state.plugins if not p.error)}. Errors: {sum(1 for p in self.state.plugins if p.error)}.", 'SUCCESS')

    def update_plugin_tree(self):
        if not hasattr(self, 'plugins_tree'):
            return
        self.plugins_tree.delete(*self.plugins_tree.get_children())
        for p in self.state.plugins:
            self.plugins_tree.insert('', 'end', values=('ERROR' if p.error else 'OK', p.name, str(
                p.path), p.error.splitlines()[-1] if p.error else ''))

    def scan(self, preserved_selection=None):
        preserved = preserved_selection if preserved_selection is not None else self.capture_selected_paths()
        try:
            files = iter_supported_files(
                self.project_root, self.cfg, self.project_cfg, self.state.plugins)
            langmap = configured_languages(self.cfg, self.project_cfg)
            base = self.project_root if self.project_root.is_dir() else self.project_root.parent
            rec = []
            first = not self.state.files and not preserved
            for p in files:
                rel = str(p.relative_to(base)) if p.is_relative_to(
                    base) else str(p)
                status = 'Existing' if extract_managed_header(
                    read_text_lossy(p)) else 'Missing'
                lang = langmap.get(p.suffix.lower(), {}).get(
                    'name', p.suffix.lower())
                rec.append(FileRecord(p, rel, lang, status,
                           True if first else p in preserved))
            self.state.files = rec
            self.populate_tree()
            self.update_dashboard()
            self.refresh_previews()
            self.log(
                f'Scan completed. Supported files: {len(rec)}.', 'SUCCESS')
        except Exception as e:
            self.log(f'Scan failed: {e}', 'ERROR')
            self.show_text_window('Scan Error', traceback.format_exc())

    def populate_tree(self):
        if not hasattr(self, 'tree'):
            return
        focus = self.tree.focus()
        self.tree.delete(*self.tree.get_children())
        dirs = {}
        needle = self.filter_var.get().lower().strip()
        for r in self.state.files:
            if needle and needle not in f'{r.rel} {r.language} {r.status}'.lower():
                continue
            parts = Path(r.rel).parts
            parent = ''
            cur = ''
            for part in parts[:-1]:
                cur = f'{cur}/{part}' if cur else part
                if cur not in dirs:
                    dirs[cur] = self.tree.insert(
                        parent, 'end', text=part, open=True, values=('', 'Folder', '', cur))
                parent = dirs[cur]
            self.tree.insert(parent, 'end', iid=str(
                r.path), text=parts[-1], values=('☑' if r.selected else '☐', r.status, r.language, r.rel))
        if focus and self.tree.exists(focus):
            self.tree.selection_set(focus)
            self.tree.focus(focus)

    def on_tree_click(self, event):
        if self.tree.identify_region(event.x, event.y) != 'cell' or self.tree.identify_column(event.x) != '#1':
            return
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        path = Path(iid)
        for r in self.state.files:
            if r.path == path:
                r.selected = not r.selected
                self.tree.set(iid, 'selected', '☑' if r.selected else '☐')
                self.update_dashboard()
                return

    def set_selection(self, val):
        for r in self.state.files:
            r.selected = val
        self.populate_tree()
        self.update_dashboard()
        self.log('Selection updated: ' +
                 ('all selected' if val else 'none selected'))

    def selected_records(self): return [
        r for r in self.state.files if r.selected]

    def selected_file(self):
        sel = self.tree.selection() if hasattr(self, 'tree') else []
        if sel and Path(sel[0]).exists():
            return Path(sel[0])
        rs = self.selected_records()
        return rs[0].path if rs else None

    def import_selected_header(self):
        p = self.selected_file()
        if not p:
            messagebox.showinfo(APP_NAME, 'Select a file first.')
            self.log('Import failed: no file selected.', 'ERROR')
            return
        h = extract_managed_header(read_text_lossy(p))
        if not h:
            messagebox.showinfo(
                APP_NAME, 'Selected file does not contain a managed HeaderForge header.')
            self.log(f'Import failed: no managed header in {p.name}.', 'ERROR')
            return
        for k, val in parse_managed_header_values(h).items():
            if k not in self.field_vars:
                continue
            if k in ('purpose', 'impact'):
                w = getattr(self, f'field_widget_{k}')
                w.delete('1.0', 'end')
                w.insert('1.0', val)
                self.field_vars[k].set(val)
            elif k == 'created_date':
                self._set_created(val)
            else:
                self.field_vars[k].set(val)
        self.refresh_previews()
        self.log(f'Imported header fields from {p.name}.', 'SUCCESS')

    def reset_fields(self): self._load_fields(); self.refresh_previews(
    ); self.log('Header fields reset.', 'SUCCESS')

    def refresh_all(self, load_config_editor=True):
        if load_config_editor:
            self.load_project_config_into_editor()
        else:
            self.update_config_state()
        self.update_dashboard()
        self.update_staged_tree()
        self.update_plugin_tree()
        self.refresh_previews()

    def update_dashboard(self):
        for c in self.metrics_frame.winfo_children():
            c.destroy()
        metrics = [('Files', len(self.state.files)), ('Selected', len(self.selected_records())), ('Existing', sum(1 for r in self.state.files if r.status ==
                                                                                                                  'Existing')), ('Missing', sum(1 for r in self.state.files if r.status == 'Missing')), ('Staged', len(self.state.staged))]
        for lab, val in metrics:
            box = ttk.LabelFrame(self.metrics_frame, text=lab, padding=10)
            box.pack(side='left', fill='x', expand=True, padx=4)
            ttk.Label(box, text=str(val), style='Metric.TLabel').pack()
        by = {}
        for r in self.state.files:
            by[r.language] = by.get(r.language, 0)+1
        pc = project_config_path(self.project_root)
        pd = (self.project_root if self.project_root.is_dir() else self.project_root.parent) / \
            self.project_cfg.get('project_plugins_directory', PLUGIN_DIR)
        lines = [f'Project: {self.project_root}', f"Project config: {'Found' if pc.exists() else 'Missing'} - {pc}", f"Plugin directory: {'Found' if pd.exists() else 'Missing'} - {pd}",
                 f"Global config: {'Found' if config_path().exists() else 'Missing'} - {config_path()}", '', 'Languages:']+([f'- {k}: {v}' for k, v in sorted(by.items())] if by else ['- No files scanned yet.'])
        lines += ['', 'Plugins:']+([f"- {p.name}: {'ERROR' if p.error else 'OK'} ({p.path})" for p in self.state.plugins] or ['- No plugins loaded.'])+[
            '', 'Staged Changes:']+([f'- {c.operation}: {c.path}' for c in self.state.staged.values()] or ['- Nothing staged.'])
        self.dashboard_text.delete('1.0', 'end')
        self.dashboard_text.insert('1.0', '\n'.join(lines))

    def refresh_previews(self):
        p = self.selected_file()
        temp = None
        try:
            if p is None:
                fd, name = tempfile.mkstemp(
                    prefix='HeaderForgeExample', suffix='.cs')
                os.close(fd)
                temp = Path(name)
                temp.write_text(
                    'using System;\n\npublic class ExampleFile { }\n', encoding='utf-8')
                p = temp
            ch = stage_change(p, self.cfg, self.project_cfg,
                              self.state.plugins, self.get_overrides())
            header = build_header(
                p, self.cfg, self.project_cfg, self.state.plugins, self.get_overrides())
            self._set_text(self.header_preview, header)
            self._set_text(self.diff_preview, unified_diff(ch))
            self._set_text(self.full_preview, ch.updated)
        except Exception as e:
            self._set_text(self.header_preview, str(e))
            self._set_text(self.diff_preview, traceback.format_exc())
            self._set_text(self.full_preview, '')
        finally:
            if temp:
                temp.unlink(missing_ok=True)

    def _set_text(self, w, text): w.configure(state='normal'); w.delete(
        '1.0', 'end'); w.insert('1.0', text); w.configure(state='normal')

    def stage_selected(self):
        self.state.staged.clear()
        errors = []
        for r in self.selected_records():
            try:
                ch = stage_change(r.path, self.cfg, self.project_cfg,
                                  self.state.plugins, self.get_overrides())
                if ch.changed:
                    self.state.staged[r.path] = ch
            except Exception as e:
                errors.append(f'{r.path}: {e}')
        self.update_staged_tree()
        self.update_dashboard()
        self.refresh_previews()
        self.tabs.select(self.staged_tab)
        if errors:
            self.show_text_window('Stage Errors', '\n'.join(errors))
            self.log(
                f'Stage completed with errors. Staged: {len(self.state.staged)}. Errors: {len(errors)}.', 'WARNING')
        else:
            self.log(
                f'Stage completed. Staged changed files: {len(self.state.staged)}.', 'SUCCESS')

    def update_staged_tree(self):
        if not hasattr(self, 'staged_tree'):
            return
        self.staged_tree.delete(*self.staged_tree.get_children())
        for p, ch in self.state.staged.items():
            self.staged_tree.insert('', 'end', iid=str(p), values=(
                ch.operation, 'Yes' if ch.changed else 'No', str(p)))

    def remove_selected_staged(self):
        n = 0
        for iid in self.staged_tree.selection():
            p = Path(iid)
            if p in self.state.staged:
                del self.state.staged[p]
                n += 1
        self.update_staged_tree()
        self.update_dashboard()
        self.log(f'Removed {n} staged change(s).', 'SUCCESS')

    def review_selected_staged(self):
        selected = [self.state.staged[Path(i)] for i in self.staged_tree.selection(
        ) if Path(i) in self.state.staged]
        if not selected:
            messagebox.showinfo(
                APP_NAME, 'Select one or more staged changes first.')
            return
        self.show_text_window('Selected Staged Diff', '\n'.join(
            unified_diff(c) for c in selected))

    def clear_staged(self): n = len(self.state.staged); self.state.staged.clear(); self.update_staged_tree(
    ); self.update_dashboard(); self.log(f'Cleared {n} staged change(s).', 'SUCCESS')

    def show_staged_diff(self):
        """This shows a diff of all staged changes without actually pushing those changes."""
        if not self.state.staged:
            messagebox.showinfo(APP_NAME, 'No staged changes yet.')
            self.log('Review staged requested but nothing is staged.')
            return
        self.show_text_window('Staged Diff', '\n'.join(
            unified_diff(c) for c in self.state.staged.values()))

    def push_staged(self):
        """This pushes the staged header changes out to the target files"""
        if not self.state.staged:
            messagebox.showinfo(APP_NAME, 'No staged changes to push.')
            self.log('Push skipped: no staged changes.')
            return
        errors = []
        pushed = 0
        self.state.last_push_backups.clear()
        for ch in list(self.state.staged.values()):
            try:
                if self.cfg.get('options', {}).get('backup_before_write', True):
                    backup = ch.path.with_name(
                        ch.path.name+self.cfg.get('options', {}).get('backup_extension', '.bak'))
                    shutil.copy2(ch.path, backup)
                    self.state.last_push_backups[ch.path] = backup
                write_text_atomic(ch.path, ch.updated)
                pushed += 1
            except Exception as e:
                errors.append(f'{ch.path}: {e}')
        self.state.staged.clear()
        selected = self.capture_selected_paths()
        self.scan(preserved_selection=selected)
        self.update_staged_tree()
        if errors:
            self.show_text_window('Push Errors', '\n'.join(errors))
            self.log(
                f'Push completed with errors. Pushed: {pushed}. Errors: {len(errors)}.', 'WARNING')
        else:
            self.log(
                f'Push completed successfully. Files written atomically: {pushed}.', 'SUCCESS')

    def undo_last_push(self):
        """This undoes the last push made to the staged files."""
        if not self.state.last_push_backups:
            messagebox.showinfo(
                APP_NAME, 'No backup map from the last push is available.')
            self.log('Undo skipped: no last-push backups tracked.')
            return
        errors = []
        restored = 0
        for target, backup in self.state.last_push_backups.items():
            try:
                if not backup.exists():
                    raise FileNotFoundError(str(backup))
                shutil.copy2(backup, target)
                restored += 1
            except Exception as e:
                errors.append(f'{target}: {e}')
        selected = self.capture_selected_paths()
        self.scan(preserved_selection=selected)
        if errors:
            self.show_text_window('Undo Errors', '\n'.join(errors))
            self.log(
                f'Undo completed with errors. Restored: {restored}. Errors: {len(errors)}.', 'WARNING')
        else:
            self.log(
                f'Undo completed successfully. Restored files: {restored}.', 'SUCCESS')

    def show_text_window(self, title, text): win = tk.Toplevel(self.root); win.title(
        f'{APP_NAME} - {title}'); win.geometry('1250x850'); area = self._text_area(win); area.insert('1.0', text)


def run_gui():
    """Run the GUI application."""
    if tk is None:
        raise RuntimeError(f'tkinter is not available: {TK_IMPORT_ERROR}')
    root = tk.Tk()
    HeaderForgeApp(root)
    root.mainloop()


def cli_scan(path: Path) -> int:
    """This is a CLI command to scan for supported files in the given directory."""
    cfg = load_config()
    pcfg = load_project_config(path if path.is_dir() else path.parent)
    plugins = load_plugins(cfg, path if path.is_dir() else path.parent, pcfg)
    files = iter_supported_files(path, cfg, pcfg, plugins)
    for f in files:
        print(f)
    print(f'Scanned {len(files)} file(s).')
    return 0


def cli_apply(path: Path, dry=False) -> int:
    """This is a CLI command to apply headers to files."""
    cfg = load_config()
    pcfg = load_project_config(path if path.is_dir() else path.parent)
    plugins = load_plugins(cfg, path if path.is_dir() else path.parent, pcfg)
    files = iter_supported_files(path, cfg, pcfg, plugins)
    changed = 0
    for f in files:
        ch = stage_change(f, cfg, pcfg, plugins, None)
        if ch.changed:
            changed += 1
            print(('WOULD CHANGE' if dry else 'CHANGED')+f': {f}')
            if not dry:
                if cfg.get('options', {}).get('backup_before_write', True):
                    shutil.copy2(f, f.with_name(
                        f.name+cfg.get('options', {}).get('backup_extension', '.bak')))
                write_text_atomic(f, ch.updated)
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
        p = project_config_path(root)
        if not p.exists():
            save_json(p, DEFAULT_PROJECT_CONFIG)
            print(f'CREATED: {p}')
        else:
            print(f'EXISTS: {p}')
        return 0
    if a.init_plugin_dir:
        root = Path(a.init_plugin_dir)
        root.mkdir(parents=True, exist_ok=True)
        pd = root/PLUGIN_DIR
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
