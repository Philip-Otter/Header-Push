import difflib
from datetime import date, datetime
from typing import Dict, Tuple
from dataschemes import staged_change

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

def get_configured_languages(cfg: dict, pcfg: dict) -> Dict[str, dict]:
    langs = dict(cfg.get('languages', {}))
    inc = {x.lower() for x in pcfg.get('include_extensions', []) if x}
    exc = {x.lower() for x in pcfg.get('exclude_extensions', []) if x}
    if inc:
        langs = {e: m for e, m in langs.items() if e.lower() in inc}
    if exc:
        langs = {e: m for e, m in langs.items() if e.lower() not in exc}
    return langs

def unified_diff(change: staged_change.StagedChange) -> str: return ''.join(difflib.unified_diff(change.original.splitlines(True),
                                                                                   change.updated.splitlines(True), fromfile=f'before/{change.path.name}', tofile=f'after/{change.path.name}'))
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