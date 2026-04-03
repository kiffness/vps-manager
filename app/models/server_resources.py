from pydantic import BaseModel

class ResourcesResponse(BaseModel):
    cpu_percentage: float
    memory_usage: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    uptime: str
    net_sent_bytes_per_sec: float
    net_recv_bytes_per_sec: float

class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
