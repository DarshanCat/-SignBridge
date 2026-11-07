import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversation_routes import router as conversation_router
from app.api.nlp_routes import router as nlp_router
from app.api.record_routes import router as record_router
from app.api.review_routes import router as review_router
from app.api.routes import router
from app.core.config import get_settings
from app.recognition.model_status import get_model_status

logging.basicConfig(level=logging.INFO)

settings = get_settings()
logger = logging.getLogger("signbridge")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load the recognition model once at startup (cached for requests); report honestly if there is none."""
    status = get_model_status(settings.model_dir)
    logger.info("Recognition model state at startup: %s (%s)", status.state, status.message)
    if settings.preload_nlp:  # the first text to gloss request otherwise pays for loading spaCy (about 4.5 s measured)
        try:
            from app.api.nlp_routes import _load_nlp

            _load_nlp(settings.spacy_model)("warm up")
            logger.info("spaCy model %s preloaded", settings.spacy_model)
        except Exception as exc:  # the NLP endpoints report 503 themselves; the API must still start
            logger.warning("spaCy preload skipped: %s", exc)
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(nlp_router)
app.include_router(record_router)
app.include_router(conversation_router)
app.include_router(review_router)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Reject oversized bodies early using Content-Length (chunked uploads are not expected by this API)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > get_settings().max_body_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request body is too large."})
    return await call_next(request)


@app.middleware("http")
async def add_process_time(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
    return response
