import os


def _tags(client, tag, path='target-tag', lang='en', field='target_tag'):
    response = client.get(f'/api/phrase/{path}', params={'lang': lang, 'tag': tag})
    assert response.status_code == 200, response.text
    return sorted(row[field] for row in response.json())


def test_target_tag_search_handles_apostrophe(client, insert_phrase):
    insert_phrase(target="I don't know", target_tag="don't")

    assert _tags(client, "don't") == ["don't"]


def test_translate_tag_search_handles_apostrophe(client, insert_phrase):
    insert_phrase(
        table='phrase_pl',
        target='Nie wiem',
        target_tag='nie wiem',
        translate="I don't know",
        translate_tag="don't",
    )

    assert _tags(client, "don't", path='translate-tag', lang='pl', field='translate_tag') == ["don't"]


def test_tag_search_does_not_evaluate_dollar_expressions(client, monkeypatch):
    monkeypatch.delenv('frapper_injected', raising=False)
    tag = "$(__import__('os').environ.__setitem__('frapper_injected', '1'))"

    assert _tags(client, tag) == []
    assert 'frapper_injected' not in os.environ


def test_tag_search_treats_like_wildcards_literally(client, insert_phrase):
    insert_phrase(target='make it', target_tag='make')

    assert _tags(client, 'ma_e') == []
    assert _tags(client, 'm%ke') == []


def test_tag_search_matching_rules(client, insert_phrase):
    insert_phrase(target='a b c', target_tag='make sure')
    insert_phrase(target='d e f', target_tag='make')
    insert_phrase(target='g h i', target_tag='be')

    assert _tags(client, 'make') == ['make', 'make sure']  # >= 4 chars: substring
    assert _tags(client, 'make==') == ['make']  # trailing == forces exact match
    assert _tags(client, 'be') == ['be']  # < 4 chars: exact match
    assert _tags(client, 'MAKE SURE') == ['make sure']  # case-insensitive
