import asyncio
import time
import psutil
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.server_resources import ResourcesResponse, ProcessInfo

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
            # Take an initial network reading — rates are calculated as delta per tick
            prev_net = psutil.net_io_counters()
            prev_time = time.time()

            while True:
                disk = psutil.disk_usage('/')

                uptime_seconds = int(time.time() - psutil.boot_time())
                days, remainder = divmod(uptime_seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes = remainder // 60
                uptime = f"{days}d {hours}h {minutes}m"

                curr_net = psutil.net_io_counters()
                curr_time = time.time()
                elapsed = curr_time - prev_time
                net_sent = (curr_net.bytes_sent - prev_net.bytes_sent) / elapsed
                net_recv = (curr_net.bytes_recv - prev_net.bytes_recv) / elapsed
                prev_net = curr_net
                prev_time = curr_time

                data = ResourcesResponse(
                    cpu_percentage=psutil.cpu_percent(interval=1),
                    memory_usage=psutil.virtual_memory().percent,
                    disk_used_gb=round(disk.used / 1024 ** 3, 2),
                    disk_total_gb=round(disk.total / 1024 ** 3, 2),
                    disk_percent=disk.percent,
                    uptime=uptime,
                    net_sent_bytes_per_sec=round(net_sent, 1),
                    net_recv_bytes_per_sec=round(net_recv, 1),
                )
                yield f"data: {data.model_dump_json()}\n\n"
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/processes", response_model=list[ProcessInfo])
async def get_processes(api_key: str = Query(...)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            cpu = round(info['cpu_percent'] or 0.0, 1)

            # Skip Windows system noise (System Idle Process reports accumulated idle time)
            if cpu > 100:
                continue

            processes.append(ProcessInfo(
                pid=info['pid'],
                name=info['name'],
                cpu_percent=cpu,
                memory_percent=round(info['memory_percent'] or 0.0, 2),
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process may have exited or be inaccessible — skip it
            continue

    processes.sort(key=lambda p: p.cpu_percent, reverse=True)
    return processes[:15]
