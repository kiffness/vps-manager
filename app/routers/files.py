from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.models.files import ListDirectoryResponse
from app.config import settings

base = Path(settings.base_dir).resolve()

router = APIRouter(
    prefix="/api/files",
    tags=["files"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "forbidden"}
        }
)

@router.get("/",response_model=list[ListDirectoryResponse])
async def list_files(path: str = ""):
    results: list[ListDirectoryResponse] = []

    resolved = (base / path).resolve()

    if not resolved.is_relative_to(base):
        raise HTTPException(status_code=403, detail="Forbidden path")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    
    for entry in resolved.iterdir():
        results.append(
            ListDirectoryResponse(
                name=entry.name,
                type="directory" if entry.is_dir() else "file",
                size=entry.stat().st_size if entry.is_file() else 0,
            )
        )

    return results