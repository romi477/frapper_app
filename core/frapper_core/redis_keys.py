def prepare_redis_key(lang, message_id, message_date):
    return f'{lang}_{message_id}_{message_date}'


def parse_redis_key(key):
    lang, message_id, message_date = key.split('_', maxsplit=2)
    return lang, message_id, message_date
