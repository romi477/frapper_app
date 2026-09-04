import re
from datetime import datetime

from frapper_core.constants import DATETIME_FORMAT


FIXTURE_FILENAME_RE = re.compile(
    r'^photo_(\d+)@(\d{2})-(\d{2})-(\d{4})_(\d{2})-(\d{2})-(\d{2})\.(?:jpe?g)$',
    re.IGNORECASE,
)


def parse_fixture_filename(filename: str) -> tuple[int, str] | None:
    match = FIXTURE_FILENAME_RE.match(filename)
    if not match:
        return None

    message_id = int(match.group(1))
    day, month, year = match.group(2), match.group(3), match.group(4)
    hour, minute, second = match.group(5), match.group(6), match.group(7)
    datetime_created = f'{year}-{month}-{day}T{hour}:{minute}:{second}'

    datetime.strptime(datetime_created, DATETIME_FORMAT)
    return message_id, datetime_created
