from fastapi import APIRouter

from .phrase import router as phrase_router
from .phrase_meta import router as meta_router
from .text_en import router as text_en_router


router = APIRouter(prefix='/api')

router.include_router(phrase_router)
router.include_router(meta_router)
router.include_router(text_en_router)
