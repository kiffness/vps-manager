from pydantic import BaseModel

class ResourcesResponse(BaseModel):
    cpu_percentage: float
    memory_usage: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    uptime: str
