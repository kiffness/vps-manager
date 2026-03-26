import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.routers.files import router as files_router
from app.routers.docker_router import router as docker_router

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VPS Manager starting up")
    yield
    logger.info("VPS manager shutting down")

app = FastAPI(
    title="VPS Manager",
    description=(
        "A lightweight python api that sits over my vps so I can run commands and browse the files"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(files_router)
app.include_router(docker_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/health", tags=["Meta"])
async def health_check():
    """Simple liveness probe — returns 200 OK when the service is running."""
    return {"status": "ok"}

