import logging
import sys
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, RedirectResponse
from pony.orm import db_session

from app.api import router
from app.config import config
from app.db.database import db
from app.utils import validate_basic


STATIC_DIR = Path(__file__).parent / 'static'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
_logger = logging.getLogger('frapper-api')

app = FastAPI(
    title='Frapper API',
    description='Frapper API',
    version='1.0.0',
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(router)


if config.frapper_enable_docs:
    @app.get('/openapi.json', dependencies=[Depends(validate_basic)], include_in_schema=False)
    def openapi_json():

        return app.openapi()

    @app.get('/docs', dependencies=[Depends(validate_basic)], include_in_schema=False)
    def swagger_ui():

        return get_swagger_ui_html(
            openapi_url='/openapi.json',
            title=f'{app.title} - Swagger UI',
        )

    @app.get('/redoc', dependencies=[Depends(validate_basic)], include_in_schema=False)
    def redoc_ui():

        return get_redoc_html(
            openapi_url='/openapi.json',
            title=f'{app.title} - ReDoc',
        )


@app.middleware('http')
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    _logger.info(
        '%s %s %s %.1fms',
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


@app.get('/health', include_in_schema=False)
@db_session
def health():
    db.execute('SELECT 1')

    return {'status': 'ok'}


@app.get('/favicon.ico', include_in_schema=False)
@app.get('/favicon.svg', include_in_schema=False)
def serve_favicon():

    return FileResponse(STATIC_DIR / 'favicon.svg', media_type='image/svg+xml')


@app.get('/', include_in_schema=False)
def root_redirect():

    return RedirectResponse(url='/web', status_code=302)


@app.get('/web', dependencies=[Depends(validate_basic)], include_in_schema=False)
def serve_index():

    return FileResponse(STATIC_DIR / 'index.html')
