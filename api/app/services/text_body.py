import re
from html.parser import HTMLParser


_LOOKS_LIKE_HTML = re.compile(r'<\s*[a-z]', re.I)
_WINDOW_OPEN = re.compile(
    r'<div\b[^>]*\bclass=(["\'])(?:(?!\1).)*\bwindow\b(?:(?!\1).)*\1[^>]*>',
    re.I,
)
_DIV_TAG = re.compile(r'</?div\b', re.I)

_FORBIDDEN_CHECKS = (
    (re.compile(r'<\s*script\b', re.I), 'Script tags are not allowed.'),
    (re.compile(r'<\s*style\b', re.I), 'Style tags are not allowed.'),
    (re.compile(r'<\s*iframe\b', re.I), 'Embedded frames are not allowed.'),
    (re.compile(r'<\s*object\b', re.I), 'Embedded objects are not allowed.'),
    (re.compile(r'<\s*embed\b', re.I), 'Embedded objects are not allowed.'),
    (re.compile(r'<\s*link\b', re.I), 'Link tags are not allowed.'),
    (re.compile(r'javascript\s*:', re.I), 'JavaScript URLs are not allowed.'),
    (re.compile(r'\bon[a-z]+\s*=', re.I), 'Inline event handlers are not allowed.'),
)


class _PlainTextExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def looks_like_html(text: str) -> bool:
    return bool(_LOOKS_LIKE_HTML.search(str(text or '').strip()))


def find_window_outer_html(html: str) -> str:
    match = _WINDOW_OPEN.search(html)
    if not match:
        return ''

    start = match.start()
    depth = 1
    index = match.end()

    while index < len(html) and depth > 0:
        tag_match = _DIV_TAG.search(html, index)
        if not tag_match:
            return ''
        if html[tag_match.start() + 1] == '/':
            depth -= 1
        else:
            depth += 1
        index = tag_match.end()

    return html[start:index].strip()


def html_to_plain_text(html: str) -> str:
    normalized = re.sub(r'(?i)<br\s*/?>', '\n', html)
    normalized = re.sub(r'(?i)</(?:p|div|li|tr|h[1-6])\s*>', '\n', normalized)
    parser = _PlainTextExtractor()
    parser.feed(normalized)
    text = ''.join(parser.parts).replace('\r\n', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalize_text_body(raw: str) -> str:
    trimmed = str(raw or '').strip()
    if not trimmed:
        return ''

    if not looks_like_html(trimmed):
        return trimmed

    window_html = find_window_outer_html(trimmed)
    if window_html:
        return window_html

    return html_to_plain_text(trimmed)


def validate_text_body(body: str) -> None:
    if not looks_like_html(body):
        return

    if not _WINDOW_OPEN.match(body.strip()):
        raise ValueError('HTML body must be a single <div class="window"> fragment.')

    for pattern, message in _FORBIDDEN_CHECKS:
        if pattern.search(body):
            raise ValueError(message)


def prepare_text_body(raw: str) -> str:
    body = normalize_text_body(raw)
    if not body:
        raise ValueError('Body is required.')
    validate_text_body(body)
    return body
