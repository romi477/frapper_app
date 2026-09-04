import requests


class FrapperApiClient:

    def __init__(self, base_url, username, password, user_agent='FrapperClient/0.1.0'):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': user_agent,
        }

    @property
    def phrase_meta_url(self):
        return f'{self.base_url}/api/phrase-meta'

    @property
    def phrase_url(self):
        return f'{self.base_url}/api/phrase'

    def post_phrase_meta(self, data, lang):
        return requests.post(
            self.phrase_meta_url,
            json=data,
            params={'lang': lang},
            headers=self.headers,
            auth=self.auth,
        )

    def get_phrase_meta(self, lang, message_id, datetime_created):
        return requests.get(
            self.phrase_meta_url,
            params={
                'lang': lang,
                'message_id': message_id,
                'datetime_created': datetime_created,
            },
            headers=self.headers,
            auth=self.auth,
        )

    def post_phrase(self, data, lang):
        return requests.post(
            self.phrase_url,
            json=data,
            params={'lang': lang},
            headers=self.headers,
            auth=self.auth,
        )

    def get_phrase(self, path, lang, params=None):
        query = dict(params or {})
        query['lang'] = lang
        return requests.get(
            f'{self.phrase_url}/{path}',
            params=query,
            headers=self.headers,
            auth=self.auth,
        )

    def delete_phrase(self, item_id, lang):
        return requests.delete(
            f'{self.phrase_url}/{item_id}',
            params={'lang': lang},
            headers=self.headers,
            auth=self.auth,
        )
