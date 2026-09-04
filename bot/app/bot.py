# python3

import logging
import sys
from datetime import datetime

from redis import Redis

from telethon.sync import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto

from frapper_core import (
    DATETIME_FORMAT,
    FrapperApiClient,
    PhraseList,
    api_base_url,
    prepare_redis_key,
    rebuild_string,
)

from app.utils import Emoji
from app.config import config


FETCH_COUNT_RE = r'/c(\s+\d+)?$'
FETCH_SLICE_RE = r'/s\s+(\d+)\s+(\d+)'
FETCH_TAIL_RE = r'/l(\s+(\d+)\s+(\d+))?'
FETCH_TARGET_TAG_RE = r'/f(\s.*)?$'
FETCH_TRANSLATE_TAG_RE = r'/t(\s.*)?$'
DELETE_BY_ID = r'/d\s+(\d+)$'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
_logger = logging.getLogger('frapper-bot')

api_client = FrapperApiClient(
    api_base_url(config.frapper_api_host, config.frapper_api_port),
    config.frapper_username,
    config.frapper_password,
    user_agent='FrapperBot/0.1.0',
)
redis_client = Redis(host=config.redis_host, port=config.redis_port)
bot = TelegramClient('/opt/bot/data/frapper-bot', config.tg_api_id, config.tg_api_hash)


def phrase_channels():
    channels = {config.tg_phrase_pl_id: 'pl'}
    if config.tg_phrase_en_id:
        channels[config.tg_phrase_en_id] = 'en'
    return channels


def add_log(func):
    def _add_log(event):
        _logger.info(
            'Request for target "%s" from user %s (admin=%s)',
            event.message.message,
            event.peer_id.user_id,
            str(event.peer_id.user_id) == str(config.tg_su_id),
        )
        return func(event)
    return _add_log


@bot.on(events.NewMessage(incoming=True, chats=list(phrase_channels().keys())))
async def handler_new_message_phrase(event):
    chat_id = int(str(event.chat_id)[4:])  # Skip the "-100" prefix
    lang = phrase_channels()[chat_id]
    _logger.info('New item %s in the "%s" phrase channel', event.message.id, lang)

    message = event.message
    if not isinstance(message.media, MessageMediaPhoto):
        _logger.info('Item is not a picture.')
        await event.respond('Item is not a picture.')
        return False

    data = {
        'message_id': (message_id := message.id),
        'datetime_created': (message_date := message.date.strftime(DATETIME_FORMAT)),
    }

    response = api_client.post_phrase_meta(data, lang=lang)

    if not response.ok:
        _logger.error(response.text)
        await event.respond(f'POST META: HTTP {response.status_code}')
        return False

    redis_key = prepare_redis_key(lang, message_id, message_date)

    _logger.info('Redis key added: %s', redis_key)

    binary_data = await event.download_media(file=bytes)
    redis_client.set(redis_key, binary_data)

    return True


@bot.on(events.NewMessage(pattern=FETCH_COUNT_RE))
@add_log
async def handler_fetch_count_pl(event):
    count = event.message.message.replace('/c', '').strip()

    return await _perform_request(
        event,
        'pl',
        'fetch-count',
        params={'count': int(count)} if count else None,
    )


@bot.on(events.NewMessage(pattern=FETCH_SLICE_RE))
@add_log
async def handler_fetch_slice_pl(event):
    since_id, count = event.message.message.replace('/s', '').strip().split()

    return await _perform_request(
        event,
        'pl',
        'fetch-slice',
        params={'since_id': int(since_id), 'count': int(count)},
    )


@bot.on(events.NewMessage(pattern=FETCH_TAIL_RE))
@add_log
async def handler_fetch_tail_pl(event):
    args = event.message.message.replace('/l', '').strip().split()

    return await _perform_request(
        event,
        'pl',
        'fetch-tail',
        params={'tail': int(args[0]), 'count': int(args[1])} if args else None,
    )


@bot.on(events.NewMessage(pattern=FETCH_TARGET_TAG_RE))
@add_log
async def handler_fetch_target_tag_pl(event):
    args = event.message.message.replace('/f', '').strip().split()

    return await _perform_request(
        event,
        'pl',
        'target-tag',
        params={'tag': ' '.join(args)} if args else None,
    )


@bot.on(events.NewMessage(pattern=FETCH_TRANSLATE_TAG_RE))
@add_log
async def handler_fetch_translate_tag_pl(event):
    args = event.message.message.replace('/t', '').strip().split()

    return await _perform_request(
        event,
        'pl',
        'translate-tag',
        params={'tag': ' '.join(args)} if args else None,
    )


@bot.on(events.NewMessage(pattern=DELETE_BY_ID))
@add_log
async def handler_delete_record_by_id(event):
    if not str(event.peer_id.user_id) == str(config.tg_su_id):
        return await event.reply(f'Sorry, protected resource {Emoji.CONFUSED_FACE}')

    args = event.message.message.replace('/d', '').strip().split()

    response = api_client.delete_phrase(args[0], lang='pl')

    if not response.ok:
        return await event.reply(f'Server Error {Emoji.JACK_O_LANTERM}')

    return await event.reply(f'OK {Emoji.SPARKLES}')


@bot.on(events.NewMessage(pattern='/start'))
async def handler_client_start_pl(event):
    _logger.info('New user logged in: %s', event.peer_id.user_id)
    return await event.reply(f'Cześć, człowieku! Postanowiłeś ćwiczyć Polskiego? To lecimy {Emoji.SPARKLES}')


async def _perform_request(event, lang, path, params=None):
    response = api_client.get_phrase(path, params=params, lang=lang)

    if not response.ok:
        return await event.reply(f'Server Error {Emoji.JACK_O_LANTERM}')

    item_list = PhraseList.validate_json(response.text)
    if not item_list:
        return await event.reply(f'Not Found {Emoji.CONFUSED_FACE}')

    for index, item in enumerate(item_list, 1):
        html_string = _prepare_html(item, index, len(item_list))
        await event.respond(html_string, parse_mode='html')

    return True


def _prepare_html(item, index, count):
    target = rebuild_string(item.target, item.target_mask)
    translate = rebuild_string(item.translate, item.translate_mask)

    head = f'{item.id} ({index}/{count})'
    target_format = f'{Emoji.INFORMATION}\t\t{target}'
    translate_format = f'{Emoji.LEFT_ARROW_CURVING_RIGHT}\t\t<i>{translate}</i>'

    return f'{head}\n\n{target_format}\n\n{translate_format}'


if __name__ == '__main__':
    bot.start(bot_token=config.frapper_bot_token)
    _logger.info('FrapperBot %s started at: %s', str(bot), str(datetime.now()))

    try:
        bot.run_until_disconnected()
    except KeyboardInterrupt:
        redis_client.close()
        raise
