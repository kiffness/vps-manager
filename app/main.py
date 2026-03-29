import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI,Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.routers.files import router as files_router
from app.routers.docker_router import router as docker_router
from app.routers.server_resources import router as server_resources_router
from app.dependancy.api_key_dependency import verify_api_key

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

app.include_router(files_router, dependencies=[Depends(verify_api_key)])
app.include_router(docker_router, dependencies=[Depends(verify_api_key)])
app.include_router(server_resources_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/health", tags=["Meta"])
async def health_check():
    """Simple liveness probe — returns 200 OK when the service is running."""
    return {"status": "ok"}

