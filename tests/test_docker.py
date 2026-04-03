from unittest.mock import MagicMock, patch
from http import HTTPStatus

AUTH_HEADERS = {"X-API-Key": "test-key"}


def make_fake_container(id="abc123", name="my-app", status="running", tag="nginx:latest"):
    # Builds a MagicMock that mimics the attributes the router reads from a real container object
    container = MagicMock()
    container.id = id
    container.name = name
    container.status = status
    container.image.tags = [tag]
    container.image.id = "sha256:abc"
    return container


# ── Containers ─────────────────────────────────────────────────────────────────

def test_get_containers(client):
    # GET /docker/containers should return a list with the correct fields
    fake = make_fake_container()

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.list.return_value = [fake]
        response = client.get("/docker/containers", headers=AUTH_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "my-app"
    assert data[0]["status"] == "running"

def test_container_action_start(client):
    # POST with action=start should call .start() on the container
    fake = make_fake_container()

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.post(
            "/docker/containers",
            json={"id": "abc123", "action": "start"},
            headers=AUTH_HEADERS
        )

    assert response.status_code == HTTPStatus.OK
    fake.start.assert_called_once()

def test_container_action_stop(client):
    # POST with action=stop should call .stop() on the container
    fake = make_fake_container()

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.post(
            "/docker/containers",
            json={"id": "abc123", "action": "stop"},
            headers=AUTH_HEADERS
        )

    assert response.status_code == HTTPStatus.OK
    fake.stop.assert_called_once()

def test_container_action_restart(client):
    # POST with action=restart should call .restart() on the container
    fake = make_fake_container()

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.post(
            "/docker/containers",
            json={"id": "abc123", "action": "restart"},
            headers=AUTH_HEADERS
        )

    assert response.status_code == HTTPStatus.OK
    fake.restart.assert_called_once()

def test_container_action_invalid(client):
    # An unrecognised action should return 400 Bad Request
    fake = make_fake_container()

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.post(
            "/docker/containers",
            json={"id": "abc123", "action": "explode"},
            headers=AUTH_HEADERS
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST

def test_container_not_found(client):
    # A container ID that doesn't exist should return 404
    import docker.errors

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        response = client.post(
            "/docker/containers",
            json={"id": "doesnotexist", "action": "start"},
            headers=AUTH_HEADERS
        )

    assert response.status_code == HTTPStatus.NOT_FOUND

def test_get_container_stats(client):
    fake = make_fake_container()
    fake.stats.return_value = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 1100},
            "system_cpu_usage": 200000,
            "online_cpus": 2
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 1000},
            "system_cpu_usage": 100000
        },
        "memory_stats": {
            "usage": 114466816,
            "limit": 33590267904
        }  
    }

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.get("/docker/containers/abc123/stats", headers=AUTH_HEADERS)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["cpu_percent"] == 0.2
        assert data["memory_usage_bytes"] == 114466816
        assert data["memory_limit_bytes"] == 33590267904

# ── Env vars ──────────────────────────────────────────────────────────────────

def test_get_container_env(client):
    # GET /docker/containers/{id}/env should return parsed key/value env vars
    fake = make_fake_container()
    fake.attrs = {"Config": {"Env": ["KEY=value", "PATH=/usr/bin", "EQUAL=a=b"]}}

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.get("/docker/containers/abc123/env", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    env = {v["key"]: v["value"] for v in response.json()["env"]}
    assert env["KEY"] == "value"
    assert env["PATH"] == "/usr/bin"
    # Values that contain = should not be split incorrectly
    assert env["EQUAL"] == "a=b"

def test_get_container_env_not_found(client):
    # Requesting env for a missing container should return 404
    import docker.errors
    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        response = client.get("/docker/containers/abc123/env", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.NOT_FOUND

# ── Live log stream ────────────────────────────────────────────────────────────

def test_stream_container_logs(client):
    # GET /docker/containers/{id}/logs/stream should stream log lines as SSE
    fake = make_fake_container()
    fake.logs.return_value = iter([b"line one\n", b"line two\n"])

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.get(
            "/docker/containers/abc123/logs/stream?api_key=test-key",
            headers={"Accept": "text/event-stream"}
        )

    assert response.status_code == HTTPStatus.OK
    assert "line one" in response.text
    assert "line two" in response.text

def test_stream_container_logs_not_found(client):
    # Streaming logs for a missing container should return 404
    import docker.errors
    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        response = client.get("/docker/containers/abc123/logs/stream?api_key=test-key")

    assert response.status_code == HTTPStatus.NOT_FOUND

def test_stream_container_logs_invalid_key(client):
    # A wrong API key should return 403
    with patch("app.routers.docker_router.client"):
        response = client.get("/docker/containers/abc123/logs/stream?api_key=wrong")

    assert response.status_code == HTTPStatus.FORBIDDEN

# ── Logs ───────────────────────────────────────────────────────────────────────

def test_get_container_logs(client):
    # GET /docker/containers/{id} should return the last 50 log lines
    fake = make_fake_container()
    fake.logs.return_value = b"line1\nline2\n"

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.return_value = fake
        response = client.get("/docker/containers/abc123", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    assert "line1" in response.json()["logs"]

def test_get_container_logs_not_found(client):
    # Requesting logs for a missing container should return 404
    import docker.errors

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.get.side_effect = docker.errors.NotFound("not found")
        response = client.get("/docker/containers/abc123", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.NOT_FOUND

# ── Networks ───────────────────────────────────────────────────────────────────

def test_get_networks(client):
    # GET /docker/networks should return a list of networks with no attached containers
    fake_network = MagicMock()
    fake_network.id = "net1"
    fake_network.name = "bridge"
    fake_network.attrs = {"Driver": "bridge", "Containers": {}}

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.networks.list.return_value = [fake_network]
        response = client.get("/docker/networks", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    assert response.json()[0]["name"] == "bridge"

def test_get_networks_with_containers(client):
    # Container names attached to a network should appear in the response
    fake_network = MagicMock()
    fake_network.id = "net1"
    fake_network.name = "bridge"
    fake_network.attrs = {
        "Driver": "bridge",
        "Containers": {"abc123": {"Name": "my-app"}}
    }

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.networks.list.return_value = [fake_network]
        response = client.get("/docker/networks", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    assert "my-app" in response.json()[0]["containers"]

# ── Volumes ────────────────────────────────────────────────────────────────────

def test_get_volumes(client):
    # GET /docker/volumes should return volumes with in_use=False when no containers mount them
    fake_volume = MagicMock()
    fake_volume.name = "my-vol"
    fake_volume.attrs = {"Driver": "local", "Mountpoint": "/var/lib/docker/volumes/my-vol"}

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.list.return_value = []
        mock_client.volumes.list.return_value = [fake_volume]
        response = client.get("/docker/volumes", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    assert response.json()[0]["name"] == "my-vol"

def test_get_volumes_in_use(client):
    # A volume mounted by a running container should be marked in_use=True
    fake_container = MagicMock()
    fake_container.attrs = {"Mounts": [{"Type": "volume", "Name": "my-vol"}]}

    fake_volume = MagicMock()
    fake_volume.name = "my-vol"
    fake_volume.attrs = {"Driver": "local", "Mountpoint": "/var/lib/docker/volumes/my-vol"}

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.containers.list.return_value = [fake_container]
        mock_client.volumes.list.return_value = [fake_volume]
        response = client.get("/docker/volumes", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    assert response.json()[0]["in_use"] is True

# ── Images ─────────────────────────────────────────────────────────────────────

def test_get_images(client):
    # GET /docker/images should return image tags and size
    fake_image = MagicMock()
    fake_image.id = "sha256:abc"
    fake_image.tags = ["nginx:latest"]
    fake_image.attrs = {"Size": 50000000}

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.images.list.return_value = [fake_image]
        response = client.get("/docker/images", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK
    assert response.json()[0]["tags"] == ["nginx:latest"]

def test_delete_image(client):
    # DELETE /docker/images/{id} should return 200 on success
    with patch("app.routers.docker_router.client"):
        response = client.delete("/docker/images/sha256:abc", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.OK

def test_delete_image_not_found(client):
    # Deleting an image that doesn't exist should return 404
    import docker.errors

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.images.remove.side_effect = docker.errors.ImageNotFound("not found")
        response = client.delete("/docker/images/sha256:abc", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.NOT_FOUND

def test_delete_image_api_error(client):
    # Deleting an image that is in use by a container should return 400
    import docker.errors

    with patch("app.routers.docker_router.client") as mock_client:
        mock_client.images.remove.side_effect = docker.errors.APIError("image in use")
        response = client.delete("/docker/images/sha256:abc", headers=AUTH_HEADERS)

    assert response.status_code == HTTPStatus.BAD_REQUEST
