import os
from unittest.mock import patch, MagicMock

# Set a fake API key before the app loads.
# app/config.py requires this env var — if it's missing, Settings() raises an error.
# setdefault won't overwrite a real value if one is already set in the environment
os.environ.setdefault("API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

# Patch docker.from_env before importing the app.
# docker_router.py calls docker.from_env() at module level (line 8), which tries
# to connect to a real Docker socket. On a dev machine that has no socket, it crashes.
# We swap it out with a MagicMock — an object that accepts any call without doing anything real.
# # The `with` block ensures the patch is only active during the import.
with patch('docker.from_env', return_value=MagicMock()):
    from app.main import app

# A fixture is a reusable setup function. Any test that declares `client` as a
# parameter will automatically receive a TestClient pointed at our app.
# TestClient runs the app in-memory — no real server needed.
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def file_client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.files.base", tmp_path)
    return TestClient(app)