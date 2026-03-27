from pydantic import  BaseModel


class ContainerResponse(BaseModel):
    id: str
    name: str
    status: str
    image: str
    image_id: str

class ContainerActionRequest(BaseModel):
    id: str
    action: str

class ContainerLogsResponse(BaseModel):
    id: str
    logs: list[str]

class NetworkResponse(BaseModel):
    id: str
    name: str
    driver: str
    containers: list[str]

class ImageResponse(BaseModel):
    id: str
    tags: list[str]
    size: int