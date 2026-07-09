import os
import fnmatch
from pathlib import Path
from typing import Optional
from datetime import date
from helpers import json_helper
from headerforge import plugin
from typing import List
from dataschemes import plugin_module

class ConfigHandler:
    """This class manages all of the applications configs"""
    # Application Details
    App_Name: str = 'HeaderPush'
    App_Version: str = '1.0.0'

    # Config Files
    Config_File: str = 'headerforge.json'
    Config_Override_Path: Optional[Path] = None
    Project_Config_File: str = 'headerforge.project.json'

    # Plugins
    Plugin_Directory: str = 'headerforge_plugins'

    # Header Indicators
    Header_Begin: str = 'HEADERFORGE-BEGIN'
    Header_End: str = 'HEADERFORGE-END'
    
    # Defaults
    Default_Project_Types = ['script', 'application',
                          'library', 'service', 'module', 'tool']
    Default_Risk_Levels = ['Low', 'Medium', 'High', 'Critical']
    Default_Build_Stages = ['Pre-Alpha', 'Alpha', 'Beta',
                        'Release Candidate', 'Release', 'Maintenance', 'Deprecated']
    Default_Patch_Types = ['Major', 'Minor', 'Patch',
                       'Bug-Fix', 'Security', 'Documentation', 'Maintenance']
    

    Default_Config = {
    'template_name': 'Standard Developer Header',
    'defaults': {
        'organization': 'Organization', 'artifact_type': 'script', 'name': '{filename_stem}', 'codename': '',
        'owner': 'Developer Name', 'title': 'Developer Position', 'created_date': date.today().isoformat(),
        'purpose': 'Describe what this script/service/module does.',
        'impact': 'Describe affected systems, users, workflows, or processes.',
        'risk': 'Low', 'build_stage': 'Alpha', 'patch_type': 'Minor', 'version': 'v1.0.0-alpha',
        'copyright_owner': 'Developer', 'copyright_start_year': '', 'copyright_end_year': str(date.today().year), 'license': ''},
    'settings': {'artifact_types': Default_Project_Types, 'risk_levels': Default_Risk_Levels, 'build_stages': Default_Build_Stages, 'patch_types': Default_Patch_Types},
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

    Default_Project_Config = {'enabled': True, 'include_extensions': [], 'exclude_extensions': [], 'ignore_directories': ['bin', 'obj', '.git', '.vs', '.vscode'], 'ignore_files': [
    ], 'ignore_globs': ['*.bak', '*.tmp'], 'plugins_enabled': True, 'project_plugins_directory': Plugin_Directory, 'header_defaults': {}, 'template_lines': []}

    FIELD_LABELS = {'organization': ['Organization'], 'artifact_type': ['Type', 'Artifact Type'], 'name': ['Name', 'Script', 'Application', 'Library'], 'codename': ['Codename', 'Code Name', 'Internal Codename'], 'owner': ['Owner'], 'title': ['Title'], 'created': [
    'Created'], 'purpose': ['Purpose'], 'impact': ['Impact'], 'risk': ['Risk Level', 'Risk'], 'build_stage': ['Build Stage', 'Release Stage', 'Stage', 'Pre-Release Stage'], 'patch_line': ['Patch'], 'copyright': ['Copyright'], 'license': ['License', 'Licensing']}



def get_user_config_dir() -> Path:
    # Windows desktop-app behavior: use roaming AppData. Non-Windows fallback
    # keeps the tool portable for Linux/macOS/dev containers.
    appdata = os.getenv('APPDATA')
    return Path(appdata)/'HeaderForge' if appdata else Path.home()/'.headerforge'

def get_user_config_path() -> Path: return get_user_config_dir()/ConfigHandler.Config_File

def get_project_config_path(
    root: Path) -> Path: return (root if root.is_dir() else root.parent)/ConfigHandler.Project_Config_File

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
    s.setdefault('artifact_types', ConfigHandler.Default_Project_Types)
    s.setdefault('risk_levels', ConfigHandler.Default_Risk_Levels)
    s.setdefault('build_stages', ConfigHandler.Default_Build_Stages)
    s.setdefault('patch_types', ConfigHandler.Default_Patch_Types)

def normalize_stage(value: str) -> str:
    raw = (value or '').strip()
    m = {'prealpha': 'Pre-Alpha', 'pre-alpha': 'Pre-Alpha', 'alpha': 'Alpha', 'beta': 'Beta', 'rc': 'Release Candidate',
         'release candidate': 'Release Candidate', 'release candidate (rc)': 'Release Candidate', 'stable': 'Release', 'production': 'Release', 'prod': 'Release'}
    return m.get(raw.lower(), raw or 'Alpha')

def load_config() -> dict:
    cfg = json_helper.load_json_if_exists(get_user_config_path(), ConfigHandler.Default_Config)
    migrate_config(cfg)
    return cfg

def load_project_config(root: Path) -> dict: return json_helper.load_json_if_exists(
    get_project_config_path(root), ConfigHandler.Default_Project_Config)

def get_app_directory() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()

def should_ignore_path(path: Path, root: Path, cfg: dict, pcfg: dict, plugins: List[plugin_module.PluginModule]) -> bool:
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
    return any(x is True for x in plugin.plugin_call(plugins, 'should_ignore', path, root, {'global': cfg, 'project': pcfg}))

def config_path() -> Path:
    # Override order: CLI --config, then HEADERFORGE_CONFIG, then AppData.
    if ConfigHandler.Config_Override_Path is not None:
        return ConfigHandler.Config_Override_Path.expanduser()
    env = os.getenv('HEADERFORGE_CONFIG')
    return Path(env).expanduser() if env else get_user_config_path()