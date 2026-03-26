import docker
import docker.errors

from app.models.docker import (ContainerResponse, ContainerActionRequest, ContainerLogsResponse,
                               NetworkResponse, ImageResponse)
from fastapi import APIRouter, HTTPException

client = docker.from_env()

router = APIRouter(
    prefix="/docker",
    tags=["docker"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not found"}
    }
)

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
            image=container.image.tags[0]
        )
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