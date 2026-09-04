#!/usr/bin/env python3
"""Load Reverso screenshot fixtures into the Frapper database.

Pass any directory that contains fixture images. The path is bind-mounted into
the listener container; it does not need to be named "fixtures" or live inside
the repo. Only filenames must match:

    photo_{message_id}@{DD-MM-YYYY}_{HH-MM-SS}.jpg

Example:
    python scripts/load_fixtures.py --lang pl ~/Downloads/reverso-shots
    python scripts/load_fixtures.py --lang en "/path/with spaces/photos" --down
"""

import argparse
import http.client
import logging
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / 'logs'
HOST_DB_PATH = REPO_ROOT / '_frapper.db'
HEALTH_TIMEOUT_SEC = 90
FIXTURE_IDLE_TIMEOUT_SEC = 300
FIXTURE_SEC_PER_IMAGE = 3
FIXTURE_FILENAME_RE = re.compile(
    r'^photo_\d+@\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}\.(?:jpe?g)$',
    re.IGNORECASE,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger('load_fixtures')


def read_dotenv(path: Path) -> dict[str, str]:
    values = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def api_settings() -> tuple[str, str]:
    env = read_dotenv(REPO_ROOT / '.env')
    host = env.get('FRAPPER_API_HOST') or 'api'
    port = env.get('FRAPPER_API_PORT') or '4040'

    return host, port


def api_health_url() -> str:
    _, port = api_settings()

    return f'http://127.0.0.1:{port}/health'


def compose_api_base_url() -> str:
    host, port = api_settings()
    if '://' in host:
        return host

    return f'http://{host}:{port}'


def fixture_log_name(lang: str) -> str:
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    return f'fixture-import-{lang}-{stamp}.log'


def init_fixture_log(lang: str, directory: Path) -> tuple[str, Path]:
    name = fixture_log_name(lang)
    path = LOGS_DIR / name
    LOGS_DIR.mkdir(exist_ok=True)
    path.write_text(
        '\n'.join([
            '=== fixture import started ===',
            f'lang={lang}',
            f'directory={directory}',
            '',
        ]) + '\n',
        encoding='utf-8',
    )
    return name, path


def count_fixture_images(directory: Path) -> tuple[int, int]:
    matching = 0
    total = 0
    for file_path in directory.iterdir():
        if not file_path.is_file():
            continue
        total += 1
        if FIXTURE_FILENAME_RE.match(file_path.name):
            matching += 1
    return matching, total


def fixture_idle_timeout(matching: int, override: int | None = None) -> int:
    if override is not None:
        return override
    return max(FIXTURE_IDLE_TIMEOUT_SEC, matching * FIXTURE_SEC_PER_IMAGE)


def ensure_database() -> None:
    result = subprocess.run(
        [sys.executable, 'api/migrate_db.py', '--init', str(HOST_DB_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error(result.stderr or result.stdout)
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

    for line in result.stdout.splitlines():
        if line.strip():
            log.info(line)


def start_compose_services(compose: list[str]) -> None:
    log.info('Starting api and redis containers')
    result = subprocess.run(
        [*compose, 'up', '-d', '--wait', '--wait-timeout', str(HEALTH_TIMEOUT_SEC), 'api', 'redis'],
        cwd=REPO_ROOT,
    )
    if result.returncode == 0:
        log.info('Compose reports api and redis are healthy')
        return

    log.warning('Compose --wait failed (exit %s); falling back to HTTP health probe', result.returncode)
    subprocess.run([*compose, 'up', '-d', 'api', 'redis'], cwd=REPO_ROOT, check=True)


def wait_for_api(url: str, timeout_sec: int) -> None:
    log.info('Waiting for API health at %s', url)
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    log.info('API is healthy')
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.RemoteDisconnected, OSError):
            pass
        time.sleep(2)
    raise TimeoutError(f'API not healthy after {timeout_sec}s: {url}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--lang', required=True, choices=['pl', 'en'])
    parser.add_argument(
        'directory',
        nargs='+',
        metavar='IMAGE_DIR',
        help='directory with fixture images (quote the path if it contains spaces)',
    )
    parser.add_argument(
        '--timeout',
        type=int,
        metavar='SEC',
        help='OCR phase timeout in seconds (default: max(300, 3 * matching file count))',
    )
    parser.add_argument(
        '--down',
        action='store_true',
        help='Stop api and redis containers after the import finishes',
    )
    args = parser.parse_args()

    directory = Path(' '.join(args.directory)).resolve()
    if not directory.is_dir():
        log.error('Not a directory: %s', directory)
        return 1

    matching, total = count_fixture_images(directory)
    log_name, log_path = init_fixture_log(args.lang, directory)
    log.info('Language: %s', args.lang)
    log.info('Image directory: %s', directory)
    log.info('Iteration log: %s', log_path)
    log.info('Files: %d total, %d matching fixture filename pattern', total, matching)
    if matching == 0:
        log.warning('No matching fixture images found; listener will exit quickly')

    idle_timeout = fixture_idle_timeout(matching, args.timeout)
    log.info('OCR timeout budget: %ds (%d sec/image)', idle_timeout, FIXTURE_SEC_PER_IMAGE)

    compose = ['docker', 'compose']
    exit_code = 1

    try:
        ensure_database()
        start_compose_services(compose)
        wait_for_api(api_health_url(), HEALTH_TIMEOUT_SEC)

        log.info('Running listener in fixture mode (API: %s)', compose_api_base_url())
        api_host, api_port = api_settings()
        result = subprocess.run(
            [
                *compose,
                'run',
                '--rm',
                '--no-deps',
                '-e',
                'FRAPPER_FIXTURE_MODE=1',
                '-e',
                f'FRAPPER_API_HOST={api_host}',
                '-e',
                f'FRAPPER_API_PORT={api_port}',
                '-e',
                'FRAPPER_FIXTURE_DIR=/fixtures',
                '-e',
                f'FRAPPER_FIXTURE_LANG={args.lang}',
                '-e',
                f'FRAPPER_FIXTURE_IDLE_TIMEOUT={idle_timeout}',
                '-e',
                f'FRAPPER_FIXTURE_LOG=/tmp/{log_name}',
                '-v',
                f'{log_path}:/tmp/{log_name}',
                '-v',
                f'{directory}:/fixtures:ro',
                'listener',
            ],
            cwd=REPO_ROOT,
        )
        exit_code = result.returncode
        if exit_code == 0:
            log.info('Fixture import finished successfully')
        else:
            log.error('Fixture import failed with exit code %s', exit_code)
        log.info('Iteration log saved to: %s', log_path)
    except TimeoutError as exc:
        log.error('%s', exc)
    except subprocess.CalledProcessError as exc:
        log.error('Docker command failed with exit code %s', exc.returncode)
    finally:
        if args.down:
            log.info('Stopping api and redis containers')
            subprocess.run([*compose, 'down'], cwd=REPO_ROOT)

    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
