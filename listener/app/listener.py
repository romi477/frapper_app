# python3

import os
import logging
import sys
from time import sleep, monotonic

from redis import Redis

from frapper_core import FrapperApiClient, api_base_url, parse_redis_key
from app.frapper import ImageFrapper
from app.fixture import ingest_fixture_directory
from app.fixture_log import FixtureRunLog


logging.basicConfig(level=logging.INFO, handlers=[])
log = logging.getLogger('frapper-listener')
log.propagate = False
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
log.addHandler(console_handler)

api_client = FrapperApiClient(
    api_base_url(os.getenv('FRAPPER_API_HOST'), os.getenv('FRAPPER_API_PORT')),
    os.getenv('FRAPPER_USERNAME'),
    os.getenv('FRAPPER_PASSWORD'),
    user_agent='FrapperListener/0.1.0',
)


def sorted_redis_keys(client) -> list[str]:
    keys = [key.decode() for key in client.scan_iter()]

    def sort_key(complex_key: str) -> tuple[int, str, str]:
        _, message_id, message_date = parse_redis_key(complex_key)
        return int(message_id), message_date, complex_key

    return sorted(keys, key=sort_key)


def process_redis_key(client, complex_key: str, run_log: FixtureRunLog | None = None) -> None:
    log.info(complex_key)
    lang, message_id, message_date = parse_redis_key(complex_key)

    meta_response = api_client.get_phrase_meta(lang, int(message_id), message_date)
    if not meta_response.ok:
        log.error(
            'Meta lookup failed for %s: HTTP %s %s',
            complex_key,
            meta_response.status_code,
            meta_response.text,
        )
        if run_log:
            run_log.iteration(
                f'process {complex_key} failed: meta lookup HTTP {meta_response.status_code}'
            )
            run_log.record_failed(complex_key, f'meta lookup HTTP {meta_response.status_code}')
        client.move(complex_key, 1)
        return

    meta_id = meta_response.json()['id']

    kw = dict(
        meta_id=meta_id,
        message_date=message_date,
        message_id=int(message_id),
    )
    record_list = ImageFrapper.split_image_from_bin_data(client.get(complex_key), **kw)
    for rec in record_list:
        rec.parse()

    record_list_valid = [x for x in record_list if x.is_done]

    if not record_list_valid:
        log.info(f'Missed records: {complex_key}. Bin data moved to DB=1')
        if run_log:
            run_log.iteration(f'process {complex_key} missed (moved to DB 1)')
            run_log.record_failed(complex_key, 'ocr parse missed')
        client.move(complex_key, 1)
        return

    data = [x.to_dict() for x in record_list_valid]
    log.info(f'Post data for {complex_key}: {data}')

    response = api_client.post_phrase(data, lang=lang)

    if not response.ok:
        log.error(f'Response status: {response.status_code} ({complex_key}). Bin data moved to DB=1')
        log.error(response.text)
        if run_log:
            run_log.iteration(
                f'process {complex_key} failed: POST phrase HTTP {response.status_code}'
            )
            run_log.record_failed(complex_key, f'POST phrase HTTP {response.status_code}')
        client.move(complex_key, 1)
        return

    log.info(response.json())
    if run_log:
        run_log.iteration(f'process {complex_key} ok ({len(record_list_valid)} phrase(s))')
    client.delete(complex_key)


def read_redis_db(client, run_log: FixtureRunLog | None = None):

    for complex_key in client.scan_iter():
        process_redis_key(client, complex_key.decode(), run_log=run_log)


def run_fixture_mode(
    client,
    fixture_dir: str,
    lang: str,
    idle_timeout_sec: int,
    run_log: FixtureRunLog | None = None,
) -> int:
    if run_log:
        run_log.note(f'lang={lang} directory={fixture_dir}')

    stats = ingest_fixture_directory(api_client, client, fixture_dir, lang, run_log=run_log)
    log.info('Fixture ingest complete: %s', stats)
    if run_log:
        run_log.note(f'ingest complete: {stats}')

    pending_keys = sorted_redis_keys(client)
    log.info('Processing %d redis key(s) sorted by message id', len(pending_keys))
    if run_log and pending_keys:
        _, first_id, _ = parse_redis_key(pending_keys[0])
        _, last_id, _ = parse_redis_key(pending_keys[-1])
        run_log.note(f'ocr queue sorted by id ({first_id}..{last_id})')

    idle_deadline = monotonic() + idle_timeout_sec
    log.info('OCR timeout budget: %ds for %d key(s)', idle_timeout_sec, len(pending_keys))
    if run_log:
        run_log.note(f'ocr timeout budget: {idle_timeout_sec}s')

    for index, complex_key in enumerate(pending_keys):
        if monotonic() > idle_deadline:
            remaining = pending_keys[index:]
            log.error('Fixture mode timed out with %d pending Redis key(s)', len(remaining))
            if run_log:
                run_log.record_pending(remaining)
                run_log.close('timed out with pending Redis keys')
            return 1
        process_redis_key(client, complex_key, run_log=run_log)

    log.info('Fixture mode complete: %s', stats)
    if run_log:
        if run_log.skipped_files:
            log.info('Skipped %d file(s): %s', len(run_log.skipped_files), ', '.join(run_log.skipped_files))
        if run_log.failed_files:
            log.info(
                'Failed %d file(s): %s',
                len(run_log.failed_files),
                ', '.join(name for name, _ in run_log.failed_files),
            )
        run_log.close(f'ingest stats: {stats}')
    return 0


if __name__ == '__main__':
    redis_client = Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'))

    if os.getenv('FRAPPER_FIXTURE_MODE') == '1':
        fixture_dir = os.getenv('FRAPPER_FIXTURE_DIR')
        fixture_lang = os.getenv('FRAPPER_FIXTURE_LANG')
        idle_timeout = int(os.getenv('FRAPPER_FIXTURE_IDLE_TIMEOUT', '300'))

        if not fixture_dir or not fixture_lang:
            raise SystemExit('FRAPPER_FIXTURE_DIR and FRAPPER_FIXTURE_LANG are required in fixture mode')

        log.info(
            'Fixture mode API: %s',
            api_base_url(os.getenv('FRAPPER_API_HOST'), os.getenv('FRAPPER_API_PORT')),
        )

        run_log = None
        fixture_log_path = os.getenv('FRAPPER_FIXTURE_LOG')
        if fixture_log_path:
            run_log = FixtureRunLog(fixture_log_path)

        try:
            raise SystemExit(
                run_fixture_mode(
                    redis_client,
                    fixture_dir,
                    fixture_lang,
                    idle_timeout,
                    run_log=run_log,
                )
            )
        except KeyboardInterrupt:
            redis_client.close()
            raise
    else:
        while True:
            try:
                read_redis_db(redis_client)
            except KeyboardInterrupt:
                redis_client.close()
                raise
            else:
                sleep(5)
