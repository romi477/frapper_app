import logging
from pathlib import Path

import requests

from frapper_core import FrapperApiClient, parse_fixture_filename, prepare_redis_key

from app.fixture_log import FixtureRunLog


log = logging.getLogger('frapper-listener')


def list_fixture_files_sorted(directory: str | Path) -> tuple[list[Path], list[Path]]:
    root = Path(directory)
    parsed_files: list[tuple[int, str, Path]] = []
    unparseable: list[Path] = []

    for file_path in root.iterdir():
        if not file_path.is_file():
            continue

        parsed = parse_fixture_filename(file_path.name)
        if not parsed:
            unparseable.append(file_path)
            continue

        message_id, message_date = parsed
        parsed_files.append((message_id, message_date, file_path))

    parsed_files.sort(key=lambda item: (item[0], item[1], item[2].name))
    return [file_path for _, _, file_path in parsed_files], unparseable


def ingest_fixture_directory(
    api_client: FrapperApiClient,
    redis_client,
    directory: str,
    lang: str,
    run_log: FixtureRunLog | None = None,
) -> dict[str, int]:
    stats = {'loaded': 0, 'skipped': 0, 'failed': 0, 'unparseable': 0}
    fixture_files, unparseable_files = list_fixture_files_sorted(directory)

    for file_path in unparseable_files:
        log.warning('Unparseable fixture filename: %s', file_path.name)
        if run_log:
            run_log.iteration(f'ingest {file_path.name} unparseable')
            run_log.record_failed(file_path.name, 'unparseable filename')
        stats['unparseable'] += 1

    if run_log and fixture_files:
        first = parse_fixture_filename(fixture_files[0].name)
        last = parse_fixture_filename(fixture_files[-1].name)
        if first and last:
            run_log.note(
                f'processing {len(fixture_files)} file(s) sorted by id '
                f'({first[0]}..{last[0]})'
            )

    log.info('Processing %d fixture file(s) sorted by message id', len(fixture_files))

    for file_path in fixture_files:
        parsed = parse_fixture_filename(file_path.name)
        if not parsed:
            continue

        message_id, message_date = parsed

        try:
            meta_response = api_client.get_phrase_meta(lang, message_id, message_date)
        except requests.RequestException as exc:
            log.error('Meta lookup failed for %s: %s', file_path.name, exc)
            if run_log:
                run_log.iteration(f'ingest {file_path.name} failed: meta lookup {exc}')
                run_log.record_failed(file_path.name, f'meta lookup {exc}')
            stats['failed'] += 1
            continue

        if meta_response.ok:
            log.info('Skipping existing fixture: %s', file_path.name)
            if run_log:
                run_log.iteration(f'ingest {file_path.name} skipped (exists)')
                run_log.record_skipped(file_path.name)
            stats['skipped'] += 1
            continue

        try:
            response = api_client.post_phrase_meta(
                {'message_id': message_id, 'datetime_created': message_date},
                lang=lang,
            )
        except requests.RequestException as exc:
            log.error('POST META failed for %s: %s', file_path.name, exc)
            if run_log:
                run_log.iteration(f'ingest {file_path.name} failed: POST META {exc}')
                run_log.record_failed(file_path.name, f'POST META {exc}')
            stats['failed'] += 1
            continue

        if not response.ok:
            log.error(
                'POST META failed for %s: HTTP %s %s',
                file_path.name,
                response.status_code,
                response.text,
            )
            if run_log:
                run_log.iteration(
                    f'ingest {file_path.name} failed: POST META HTTP {response.status_code}'
                )
                run_log.record_failed(
                    file_path.name,
                    f'POST META HTTP {response.status_code}',
                )
            stats['failed'] += 1
            continue

        redis_key = prepare_redis_key(lang, message_id, message_date)
        redis_client.set(redis_key, file_path.read_bytes())
        log.info('Loaded fixture: %s -> %s', file_path.name, redis_key)
        if run_log:
            run_log.iteration(f'ingest {file_path.name} loaded -> {redis_key}')
        stats['loaded'] += 1

    return stats
