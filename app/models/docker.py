from pydantic import  BaseModel


class ContainerResponse(BaseModel):
    id: str
    name: str
    status: str
    image: str

class ContainerActionRequest(BaseModel):
    id: str
    action: str

class ContainerLogsResponse(BaseModel):
    id: str
    logs: list[str]

