# VPS Manager

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![GitHub release](https://img.shields.io/github/v/release/kiffness/vps-manager)
![Tests](https://github.com/kiffness/vps-manager/actions/workflows/tests.yml/badge.svg)

A self-hosted web UI for managing a Linux VPS — built with FastAPI and vanilla JS. No framework overhead, no cloud dependency, runs entirely in a Docker container on the server.

## Features

**Files**
- Browse the server filesystem via a VS Code-style file tree
- View and edit files in-browser using Monaco Editor (the editor that powers VS Code)
- Save changes directly to the server
- Upload files via drag-and-drop or file picker

![Files](assets/Files%20Showcase.gif)

**Docker**
- View all containers with live status, start/stop/restart controls and log viewer
- Browse networks, volumes, and images
- Filter images by usage and bulk-delete unused ones

![Docker](assets/Docker%20Showcase.gif)

**Terminal**
- Full interactive terminal in the browser via xterm.js and WebSockets
- SSHes into the host over an ed25519 key — gives a real shell on the server, not just inside the container
- Supports copy (select to copy) and paste (Ctrl+V or right-click)

![Terminal](assets/Terminal%20Showcase.gif)

**Server Resources**
- Live CPU, memory, and disk usage streamed via SSE

![Server](assets/Server%20Section.gif)

**Cheat Sheet**
- Quick reference for common Docker, Linux, and Caddy commands

![Cheat Sheet](assets/Cheat%20Sheet.gif)

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Docker control | docker-py (Docker SDK) |
| Terminal | WebSockets + SSH (asyncssh) |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla HTML/CSS/JS |
| File editor | Monaco Editor (CDN) |
| Browser terminal | xterm.js (CDN) |
| Auth | API key middleware |
| Deployment | Docker Compose |

## Project Structure

```
vps-manager/
├── app/
│   ├── main.py                  # FastAPI app, router registration, static files
│   ├── config.py                # Settings (API key, base dir, SSH config, log level)
│   ├── routers/
│   │   ├── files.py             # File browse, read, write, delete
│   │   ├── docker_router.py     # Containers, networks, images, logs, exec
│   │   ├── server_resources.py  # CPU, memory, disk via SSE
│   │   └── terminal.py          # WebSocket terminal (SSH via asyncssh)
│   └── dependency/
│       └── api_key_dependency.py
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── Dockerfile
└── docker-compose.yml
```

## Testing

The project has a unit test suite with 87% coverage across the core business logic.

```
tests/
├── conftest.py       # shared fixtures (test client, temp dir, auth headers)
├── test_files.py     # file endpoint tests
└── test_docker.py    # docker endpoint tests (docker SDK is mocked)
```

### Running the tests

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### What's tested

| Area | Coverage | Notes |
|---|---|---|
| File endpoints | 100% | Real filesystem via pytest `tmp_path` fixture |
| Docker endpoints | 100% | Docker SDK mocked — no live socket needed |
| Auth middleware | ✓ | Valid key accepted, invalid key rejected |
| Path traversal | ✓ | `../../etc/passwd`-style attacks return 403 |
| Error paths | ✓ | 404s, 400s, missing containers, binary files |

## Running It

### Prerequisites

- Docker and Docker Compose on your VPS
- An SSH server running on the host (`sshd`)

### Setup

1. Clone the repo onto your server:
   ```bash
   git clone https://github.com/kiffness/vps-manager.git
   cd vps-manager
   ```

2. Generate an SSH key pair for the terminal to use:
   ```bash
   ssh-keygen -t ed25519 -f ./ssh_key -N "" -C "vps-manager"
   cat ssh_key.pub >> ~/.ssh/authorized_keys
   ```

3. Create a `.env` file:
   ```bash
   API_KEY=your-secret-key-here
   BASE_DIR=/home/your-user     # optional, defaults to /home/runner
   SSH_USER=root                # user to SSH in as
   ```

4. Start the container:
   ```bash
   docker compose up -d
   ```

5. Open `http://<your-server-ip>:8080` in your browser and enter your API key.

### docker-compose.yml

The app mounts three things from the host:

```yaml
volumes:
  - /home/your-user:/home/your-user  # match your BASE_DIR
  - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
  - ./ssh_key:/run/secrets/ssh_key:ro  # SSH private key for terminal
extra_hosts:
  - "host.docker.internal:host-gateway"  # lets the container reach the host via SSH
```

## Security

Access is protected by an API key sent as an `X-API-Key` header (or query parameter for WebSocket/SSE connections). The key is stored in `localStorage` in the browser after first entry.

The browser terminal SSHes into the host using a dedicated ed25519 key — it does not use password authentication. Keep `ssh_key` out of version control (it is gitignored by default).

This is designed for personal use over a trusted network or behind a reverse proxy with HTTPS. Do not expose it directly to the public internet without TLS.
