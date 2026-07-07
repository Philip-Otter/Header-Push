from datetime import date, datetime
from typing import Dict

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