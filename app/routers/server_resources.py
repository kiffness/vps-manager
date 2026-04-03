import asyncio
import time
import psutil
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.server_resources import ResourcesResponse

router = APIRouter(
    prefix="/server-resources",
    tags=["server-resources"],
    responses={
        400: {"description": "Bad Request"}
    }
)

@router.get("/stream")
async def stream_resources(api_key: str = Query(...)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    async def event_generator():
        try:
            while True:
                disk = psutil.disk_usage('/')

                uptime_seconds = int(time.time() - psutil.boot_time())
                days, remainder = divmod(uptime_seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes = remainder // 60
                uptime = f"{days}d {hours}h {minutes}m"

                data = ResourcesResponse(
                    cpu_percentage=psutil.cpu_percent(interval=1),
                    memory_usage=psutil.virtual_memory().percent,
                    disk_used_gb=round(disk.used / 1024 ** 3, 2),
                    disk_total_gb=round(disk.total / 1024 ** 3, 2),
                    disk_percent=disk.percent,
                    uptime=uptime,
                )
                yield f"data: {data.model_dump_json()}\n\n"
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
