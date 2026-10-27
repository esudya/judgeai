import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import chats, knowledge
from src.config import settings
from src.services.analysis_runner import fail_interrupted_analyses

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    interrupted = await fail_interrupted_analyses()
    if interrupted:
        logger.warning("marked %s interrupted analyses as failed", interrupted)
    yield


app = FastAPI(
    title="JudgeAI",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
