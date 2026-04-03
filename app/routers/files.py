import shutil

from fastapi import APIRouter, HTTPException, status, File, UploadFile, Form, Query
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List

from app.models.files import ListDirectoryResponse, FileContentResponse, WriteFileRequest, FileUploadResponse
from app.config import settings
from app.dependancy.api_key_dependency import verify_api_key

base = Path(settings.base_dir).resolve()

router = APIRouter(
    prefix="/api/files",
    tags=["files"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "forbidden"}
        }
)

# Separate router for endpoints that authenticate via query param (e.g. browser downloads)
download_router = APIRouter(
    prefix="/api/files",
    tags=["files"],
)

def resolve_and_check(path: str, check_exists: bool = True) -> Path:
      resolved = (base / path).resolve()
      if not resolved.is_relative_to(base):
          raise HTTPException(status_code=403, detail="Forbidden path")
      
      if check_exists:
        if not resolved.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
      return resolved

@router.get("/",response_model=list[ListDirectoryResponse])
async def list_files(path: str = ""):
    results: list[ListDirectoryResponse] = []

    resolved = resolve_and_check(path)
    
    for entry in resolved.iterdir():
        results.append(
            ListDirectoryResponse(
                name=entry.name,
                type="directory" if entry.is_dir() else "file",
                size=entry.stat().st_size if entry.is_file() else 0,
            )
        )

    return results

@router.get("/content", response_model=FileContentResponse)
async def read_content(file: str = ""):
    resolved = resolve_and_check(file)

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    try:
        response = FileContentResponse(
            path=str(resolved),
            content=resolved.read_text(encoding="utf-8")
        )
        return response
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not utf-8")

@router.put("/content", status_code=status.HTTP_200_OK)
async def write_content(body: WriteFileRequest):
    resolved = resolve_and_check(body.path, False)

    if resolved.is_dir():
      raise HTTPException(status_code=400, detail="Path is a directory")

    resolved.parent.mkdir(parents=True, exist_ok=True)
    
    resolved.write_text(body.content, encoding="utf-8")

    return {"message": "File content succesfully updated"}

@download_router.get("/download")
async def download_file(file: str = "", api_key: str = Query(...)):
    # Download uses a query param for auth since browser <a> tags can't set headers
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    resolved = resolve_and_check(file)

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    return FileResponse(
        path=resolved,
        filename=resolved.name,
        media_type="application/octet-stream"
    )

@router.delete("/")
async def delete(path: str = ""):
    resolved = resolve_and_check(path)

    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()

    return {"message": "Deleted"}

@router.post("/upload", response_model=List[FileUploadResponse])
async def upload_files(path: str = Form(...), files: List[UploadFile] =File(...)):
    resolved = resolve_and_check(path)

    response = []

    for file in files:
        dest_path = resolved / file.filename

        with open(dest_path, 'wb') as dest:
            shutil.copyfileobj(file.file, dest)

        response.append(FileUploadResponse(
            filename=file.filename,
            path=str(dest_path)
        ))
    
    return response
