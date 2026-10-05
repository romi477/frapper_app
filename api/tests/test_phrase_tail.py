def _tail(client, tail, count=10):
    response = client.get('/api/phrase/fetch-tail', params={'lang': 'en', 'tail': tail, 'count': count})
    assert response.status_code == 200, response.text
    return response.json()


def test_fetch_tail_excludes_inactive_phrases(client, insert_phrase):
    insert_phrase(target='active one', target_tag='one')
    insert_phrase(target='inactive two', target_tag='two', active=False)

    assert [row['target'] for row in _tail(client, tail=10)] == ['active one']


def test_fetch_tail_pool_is_last_rows_despite_id_gaps(client, insert_phrase):
    ids = [insert_phrase(target=f'phrase {i}', target_tag=f'tag {i}') for i in range(6)]
    for item_id in ids[:3]:
        assert client.delete(f'/api/phrase/{item_id}', params={'lang': 'en'}).status_code == 200

    assert [row['id'] for row in _tail(client, tail=1)] == [ids[-1]]
