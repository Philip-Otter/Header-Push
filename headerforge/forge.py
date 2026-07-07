import html
import re
from typing import Optional, Tuple
from configs import config_handler
from helpers import misc_helper

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