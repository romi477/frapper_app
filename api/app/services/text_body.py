import re
from html import escape
from html.parser import HTMLParser


_TAG_START = re.compile(r'<\s*[a-z]', re.I)
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

# Allowlist for stored story HTML (rendered with innerHTML). The checks above only
# give friendly errors; sanitize_html() is what actually keeps markup safe.
_ALLOWED_TAGS = frozenset({
    'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'hr', 'i', 'li', 'mark', 'ol', 'p', 'pre', 'small', 'span', 'strong', 'sub', 'sup',
    'table', 'tbody', 'td', 'th', 'thead', 'tr', 'u', 'ul',
})
_VOID_TAGS = frozenset({'br', 'hr'})
# Elements with an end tag whose content must not leak out as text. Void elements
# (img, embed, meta, input, …) are simply not in the allowlist.
_DROPPED_WITH_CONTENT = frozenset({
    'applet', 'frameset', 'head', 'iframe', 'math', 'noembed', 'noframes', 'noscript',
    'object', 'script', 'select', 'style', 'svg', 'template', 'textarea', 'title', 'xmp',
})
_UNSAFE_STYLE = re.compile(r'url\s*\(|expression|javascript\s*:|@import|\\|[<>]', re.I)


class _PlainTextExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class _HtmlSanitizer(HTMLParser):
    """Re-serializes HTML keeping only allowlisted tags and the class/style attributes."""

    def __init__(self):
        super().__init__()
        self.out = []
        self.open_tags = []
        self.skip_tag = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth += 1
            return
        if tag in _DROPPED_WITH_CONTENT:
            self.skip_tag, self.skip_depth = tag, 1
            return
        if tag not in _ALLOWED_TAGS:
            return  # unwrap: drop the tag, keep its text

        kept = ''.join(
            f' {name}="{escape(value)}"'
            for name, value in attrs
            if value is not None and (
                name == 'class' or (name == 'style' and not _UNSAFE_STYLE.search(value))
            )
        )
        self.out.append(f'<{tag}{kept}>')
        if tag not in _VOID_TAGS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if not self.skip_depth:
                    self.skip_tag = None
            return
        if tag not in self.open_tags:
            return
        while self.open_tags:
            open_tag = self.open_tags.pop()
            self.out.append(f'</{open_tag}>')
            if open_tag == tag:
                break

    def handle_data(self, data):
        if not self.skip_tag:
            self.out.append(escape(data, quote=False))

    def result(self) -> str:
        closing = ''.join(f'</{tag}>' for tag in reversed(self.open_tags))
        return ''.join(self.out) + closing


def looks_like_html(text: str) -> bool:
    # Same rule as the web UI (`<letter … >`): a lone "<" in plain text is not markup.
    text = str(text or '').strip()
    match = _TAG_START.search(text)
    return bool(match) and text.find('>', match.end()) >= 0


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
        tag_end = html.find('>', tag_match.end())
        if tag_end < 0:
            return ''
        index = tag_end + 1

    return html[start:index].strip()


def html_to_plain_text(html: str) -> str:
    normalized = re.sub(r'(?i)<br\s*/?>', '\n', html)
    normalized = re.sub(r'(?i)</(?:p|div|li|tr|h[1-6])\s*>', '\n', normalized)
    parser = _PlainTextExtractor()
    parser.feed(normalized)
    parser.close()
    text = ''.join(parser.parts).replace('\r\n', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def sanitize_html(html: str) -> str:
    sanitizer = _HtmlSanitizer()
    sanitizer.feed(html)
    sanitizer.close()
    return sanitizer.result()


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
    if looks_like_html(body):
        body = sanitize_html(body)
    return body
