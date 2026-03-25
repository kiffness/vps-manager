from pydantic import BaseModel

class ListDirectoryResponse(BaseModel):
    name: str
    type: str
    size: int = 0

class ListDirectoryRequest(BaseModel):
    path: str = ""