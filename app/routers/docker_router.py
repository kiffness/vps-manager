import asyncio
import docker
import docker.errors

from app.models.docker import (ContainerResponse, ContainerActionRequest, ContainerLogsResponse,
                               NetworkResponse, ImageResponse, VolumeResponse,
                               ContainerStatsResponse, EnvVar, ContainerEnvResponse)
from app.config import settings
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

client = docker.from_env()

router = APIRouter(
    prefix="/docker",
    tags=["docker"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not found"}
    }
)

# Separate router for SSE endpoints — EventSource can't set headers so auth uses query param
log_stream_router = APIRouter(prefix="/docker", tags=["docker"])

@router.get("/containers", response_model=list[ContainerResponse])
async def get_containers():
    containers_result = []
    containers = client.containers.list(all=True)
    for container in containers:
        containers_result.append(
            ContainerResponse(
                id=container.id,
                name=container.name,
                status=container.status,
                image=container.image.tags[0],
                image_id=container.image.id,
            )
        )

    return containers_result

@router.post("/containers", response_model=ContainerResponse)
async def container_action(body: ContainerActionRequest):
    container_id = body.id

    try:
        container = client.containers.get(container_id)

        match body.action:
            case "start":
                container.start()
            case "stop":
                container.stop()
            case "restart":
                container.restart()
            case _:
                raise HTTPException(status_code=400, detail=f"Bad Request, Command unknown {body.action}")

        container.reload()

        return ContainerResponse(
            id=container.id,
            name=container.name,
            status=container.status,
            image=container.image.tags[0],
            image_id=container.image.id,
        )
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    
@router.get("/containers/{container_id}/stats", response_model=ContainerStatsResponse)
async def get_container_stats(container_id: str):
    try:
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)

        # CPU calculation
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"]["online_cpus"]
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100

        return ContainerStatsResponse(
            id=container.id,
            cpu_percent=round(cpu_percent, 2),
            memory_usage_bytes=stats["memory_stats"]["usage"],
            memory_limit_bytes=stats["memory_stats"]["limit"]
        )
    except docker.errors.NotFound:
          raise HTTPException(status_code=404, detail="Container not found")

@router.get("/containers/{container_id}/env", response_model=ContainerEnvResponse)
async def get_container_env(container_id: str):
    try:
        container = client.containers.get(container_id)
        raw_env = container.attrs["Config"]["Env"] or []
        env_vars = []
        for entry in raw_env:
            # Each entry is "KEY=value" — split on first = only to handle values that contain =
            key, _, value = entry.partition("=")
            env_vars.append(EnvVar(key=key, value=value))
        return ContainerEnvResponse(id=container.id, env=env_vars)
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")

@router.get("/containers/{container_id}", response_model=ContainerLogsResponse)
async def get_container_log(container_id: str):
    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=50).decode("utf-8").splitlines()
        return ContainerLogsResponse(
            id=container.id,
            logs=logs
        )
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")


# Networks
@router.get("/networks", response_model=list[NetworkResponse])
async def get_networks():
    networks_result = []

    for network in client.networks.list():
        network.reload()
        containers_name_list = []

        network_id = network.id
        network_name = network.name
        driver = network.attrs["Driver"]
        containers = network.attrs.get("Containers", {})
        for container_id, container_info in containers.items():
            containers_name_list.append(container_info["Name"])

        networks_result.append(
            NetworkResponse(
                id=network_id,
                name=network_name,
                driver=driver,
                containers=containers_name_list
            )
        )

    return networks_result

# Volumes

@router.get("/volumes", response_model=list[VolumeResponse])
async def get_volumes():
    containers = client.containers.list(all=True)
    used_volumes = set()
    for container in containers:
        for mount in container.attrs.get("Mounts", []):
            if mount.get("Type") == "volume":
                used_volumes.add(mount.get("Name"))

    volumes_result = []
    for volume in client.volumes.list():
        volumes_result.append(
            VolumeResponse(
                name=volume.name,
                driver=volume.attrs["Driver"],
                mountpoint=volume.attrs["Mountpoint"],
                in_use=volume.name in used_volumes,
            )
        )

    return volumes_result

# Images
@router.get("/images", response_model=list[ImageResponse])
async def get_images():
    images_result = []

    for image in client.images.list():
        images_result.append(
            ImageResponse(
                id=image.id,
                tags=image.tags,
                size=image.attrs["Size"]
            )
        )

    return images_result

@router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    try:
        client.images.remove(image_id)
        return {"message": "Image deleted"}
    except docker.errors.ImageNotFound:
        raise HTTPException(status_code=404, detail="Image not found")
    except docker.errors.APIError as e:
        raise HTTPException(status_code=400, detail=str(e))

@log_stream_router.get("/containers/{container_id}/logs/stream")
async def stream_container_logs(container_id: str, api_key: str = Query(...)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        container = client.containers.get(container_id)
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")

    async def event_generator():
        loop = asyncio.get_event_loop()
        log_iter = container.logs(stream=True, follow=True, tail=50)
        try:
            while True:
                # Run the blocking next() call in a thread so we don't block the event loop
                line = await loop.run_in_executor(None, next, log_iter, None)
                if line is None:
                    break
                yield f"data: {line.decode('utf-8', errors='replace').rstrip()}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")