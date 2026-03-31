from pydantic import BaseModel

class ListDirectoryResponse(BaseModel):
    name: str
    type: str
    size: int = 0

class FileContentResponse(BaseModel):
    path: str
    content: str

class WriteFileRequest(BaseModel):
    path: str
    content: str

class FileUploadResponse(BaseModel):
    filename: str
    path: str