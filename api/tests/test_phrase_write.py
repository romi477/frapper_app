def _row(target, tag):
    return {
        'meta_id': None,
        'state': 'done',
        'active': True,
        'target': target,
        'target_tag': tag,
        'translate': 'translation',
        'translate_tag': 'translation',
        'target_mask': '1' * len(target.split()),
        'translate_mask': '1',
        'message_id': 1,
        'message_date': '2026-10-01T10:00:00',
        'metadata': '{}',
    }


def _stored_targets(client, lang='pl'):
    response = client.get('/api/phrase/fetch-count', params={'lang': lang, 'count': 100})
    assert response.status_code == 200, response.text
    return sorted(row['target'] for row in response.json())


def test_post_phrases_skips_rows_that_already_exist(client):
    seed = client.post('/api/phrase', params={'lang': 'pl'}, json=[_row('Stare zdanie', 'stare')])
    assert seed.status_code == 200, seed.text

    response = client.post(
        '/api/phrase',
        params={'lang': 'pl'},
        json=[_row('Nowe jeden', 'nowe'), _row('Stare zdanie', 'stare'), _row('Nowe dwa', 'dwa')],
    )

    assert response.status_code == 200, response.text
    assert [row['target'] for row in response.json()] == ['Nowe jeden', 'Nowe dwa']
    assert _stored_targets(client) == ['Nowe dwa', 'Nowe jeden', 'Stare zdanie']


def test_post_phrases_skips_duplicates_within_one_batch(client):
    response = client.post(
        '/api/phrase',
        params={'lang': 'pl'},
        json=[_row('To samo', 'samo'), _row('To samo', 'samo')],
    )

    assert response.status_code == 200, response.text
    assert [row['target'] for row in response.json()] == ['To samo']
    assert _stored_targets(client) == ['To samo']


def test_delete_missing_phrase_returns_404(client):
    response = client.delete('/api/phrase/999', params={'lang': 'en'})

    assert response.status_code == 404


def test_post_phrase_meta_twice_returns_existing_record(client):
    meta = {'message_id': 42, 'datetime_created': '2026-10-01T10:00:00'}

    first = client.post('/api/phrase-meta', params={'lang': 'pl'}, json=meta)
    second = client.post('/api/phrase-meta', params={'lang': 'pl'}, json=meta)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()['id'] == first.json()['id']


def test_post_phrase_meta_with_malformed_datetime_returns_422(client):
    response = client.post(
        '/api/phrase-meta',
        params={'lang': 'pl'},
        json={'message_id': 42, 'datetime_created': 'yesterday'},
    )

    assert response.status_code == 422


def test_get_phrase_meta_with_malformed_datetime_returns_422(client):
    response = client.get(
        '/api/phrase-meta',
        params={'lang': 'pl', 'message_id': 42, 'datetime_created': '2026-10-01 10:00'},
    )

    assert response.status_code == 422
