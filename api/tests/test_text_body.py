from app.services.text_body import html_to_plain_text, prepare_text_body

STORY = (
    '<div class="window"><div class="titlebar"><span class="dot red"></span>'
    '<span class="filename">talk.txt</span></div>'
    '<div class="content"><div class="line"><span class="name name-1">Owen:</span> '
    'I <span class="key">ran into</span> <em>her</em> &amp; left.</div><hr>'
    '<div class="legend-item"><span class="swatch" style="background:#27c93f"></span> key</div>'
    '</div></div>'
)


def test_window_fragment_keeps_closing_tag():
    assert prepare_text_body('<div class="window">Hi</div>') == '<div class="window">Hi</div>'


def test_story_markup_survives_normalization():
    assert prepare_text_body(STORY) == STORY


def test_plain_text_with_lone_angle_bracket_is_kept_verbatim():
    text = 'Remember: a<b means less. Second sentence here.'

    assert prepare_text_body(text) == text


def test_html_to_plain_text_keeps_trailing_text_after_ampersand():
    assert html_to_plain_text('<p>Hi</p>Tom&Jerry') == 'Hi\nTom&Jerry'


def test_entity_encoded_javascript_link_is_neutralized():
    body = prepare_text_body('<div class="window"><a href="&#106;avascript:alert(1)">click</a></div>')

    assert body == '<div class="window">click</div>'


def test_unsafe_style_and_disallowed_elements_are_dropped():
    body = prepare_text_body(
        '<div class="window"><span style="background:url(https://x.test/a)">a</span>'
        '<img src="x.png"><meta http-equiv="refresh" content="0;url=https://x.test"></div>'
    )

    assert body == '<div class="window"><span>a</span></div>'
