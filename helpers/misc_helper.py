from datetime import date, datetime

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