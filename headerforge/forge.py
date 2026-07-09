import html
import re
from typing import Optional, Tuple, List
from pathlib import Path
from configs import config_handler
from helpers import misc_helper, file_helper
from dataschemes import plugin_module, staged_change
from dataschemes import file_record

class Forge:


    def __init__(self):
        pass

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
    b = content.find(config_handler.ConfigHandler.Header_Begin)
    e = content.find(config_handler.ConfigHandler.Header_End)
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
    patch_line_regex = re.compile(
    r'^(?P<patch_type>.+?)\s+Patch\s*:\s*(?P<version>.+)$', re.I)
    lines = [clean_header_line(x) for x in header_text.splitlines()]
    lines = [x for x in lines if x and x not in (config_handler.ConfigHandler.Header_Begin, config_handler.ConfigHandler.Header_End)]
    values = {}
    for idx, line in enumerate(lines):
        pm = patch_line_regex.match(line)
        if pm:
            values['patch_type'] = pm.group('patch_type').strip()
            values['version'] = pm.group('version').strip()
            continue
        if ':' not in line:
            continue
        label, raw = [x.strip() for x in line.split(':', 1)]
        lower = label.lower()
        for key, labels in config_handler.ConfigHandler.FIELD_LABELS.items():
            if lower in [x.lower() for x in labels]:
                if key == 'created':
                    values['created_date'] = misc_helper.parse_created_date(
                        raw).isoformat()
                elif key == 'build_stage':
                    values['build_stage'] = config_handler.normalize_stage(raw)
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
                values[target] = config_handler.normalize_stage(
                    ' '.join(c)) if target == 'build_stage' else ' '.join(c)
    return values

def format_copyright(values: dict) -> str:
    owner = (values.get('copyright_owner') or '').strip()
    if not owner:
        return ''
    end = (values.get('copyright_end_year') or '').strip() or str(
        misc_helper.parse_created_date(values.get('created_date', '')).year)
    start = (values.get('copyright_start_year') or '').strip()
    years = f'{start}-{end}' if start and start != end else end
    return f'Copyright : © {years} {owner}'

def strip_template(
    line: str) -> str: return line[2:] if line.startswith('; ') else '' if line == ';' else line

def build_header(path: Path, cfg: dict, pcfg: dict, overrides: Optional[dict] = None) -> str:
    lang = misc_helper.get_configured_languages(cfg, pcfg)[path.suffix.lower()]
    lp = lang.get('line_prefix', '')
    bo = lang.get('block_open', '')
    bc = lang.get('block_close', '')
    style = lang.get('style', 'block')
    vals = file_helper.get_file_details(path, cfg, pcfg, overrides)
    lines = []
    if style == 'block' and bo:
        lines.append(bo)
    lines.append(f'{lp}{config_handler.ConfigHandler.Header_Begin}')
    for line in template_core(path, cfg, pcfg, vals):
        c = strip_template(line)
        lines.append(f'{lp}{c}' if c else lp.rstrip())
    lines.append(f'{lp}{config_handler.ConfigHandler.Header_End}')
    if style == 'block' and bc:
        lines.append(bc)
    return '\n'.join(lines).rstrip()+'\n\n'

def template_core(path: Path, cfg: dict, pcfg: dict, values: dict) -> List[str]:
    lines = list(pcfg.get('template_lines') or cfg.get('template_lines', []))
    out = []
    for line in lines:
        if not values.get('copyright_section') and '{copyright_section}' in line:
            continue
        if not values.get('license_section') and '{license_section}' in line:
            continue
        out.append(safe_format(line, values).rstrip())
    return out

def safe_format(line: str, values: dict) -> str:
    try:
        return line.format(**values)
    except KeyError as e:
        return line.replace('{'+str(e.args[0])+'}', f'<missing:{e.args[0]}>')
    
def stage_change(path: Path, cfg: dict, pcfg: dict, overrides: Optional[dict]) -> staged_change.StagedChange:
    original = file_helper.read_text_lossy(path)
    existed = extract_managed_header(original) is not None
    updated = apply_header_to_text(original, path.suffix.lower(
    ), build_header(path, cfg, pcfg, overrides), cfg)
    op = 'Update Header' if existed and original != updated else 'Insert Header' if not existed and original != updated else 'No Change'
    return staged_change.StagedChange(path, original, updated, op)

def apply_header_to_text(content: str, suffix: str, header: str, cfg: dict) -> str:
    pre, body = misc_helper.split_preamble(content, suffix, cfg)
    b = find_managed_header_bounds(body)
    body = (body[:b[0]]+header+body[b[1]:].lstrip('\n')
            ) if b else header+body.lstrip('\n')
    return pre+body