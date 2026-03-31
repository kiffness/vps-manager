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

**Docker**
- View all containers with live status, start/stop/restart controls and log viewer
- Browse networks, volumes, and images
- Filter images by usage and bulk-delete unused ones

**Terminal**
- Full interactive terminal in the browser via xterm.js and WebSockets
- Connects to a real bash shell on the server over a PTY

**Server Resources**
- Live CPU, memory, and disk usage streamed via SSE

**Cheat Sheet**
- Quick reference for common Docker, Linux, and Caddy commands

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Docker control | docker-py (Docker SDK) |
| Terminal | WebSockets + PTY (Python `pty` module) |
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
│   ├── config.py                # Settings (API key, base dir, log level)
│   ├── routers/
│   │   ├── files.py             # File browse, read, write, delete
│   │   ├── docker_router.py     # Containers, networks, images, logs, exec
│   │   ├── server_resources.py  # CPU, memory, disk via SSE
│   │   └── terminal.py          # WebSocket terminal (PTY + bash)
│   └── dependency/
│       └── api_key_dependency.py
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── Dockerfile
└── docker-compose.yml
```

## Running It

### Prerequisites

- Docker and Docker Compose on your VPS

### Setup

1. Clone the repo onto your server:
   ```bash
   git clone https://github.com/kiffness/vps-manager.git
   cd vps-manager
   ```

2. Create a `.env` file:
   ```bash
   API_KEY=your-secret-key-here
   BASE_DIR=/home/your-user     # optional, defaults to /home/runner
   ```

3. Start the container:
   ```bash
   docker compose up -d
   ```

4. Open `http://<your-server-ip>:8080` in your browser and enter your API key.

### docker-compose.yml

The app mounts two things from the host:

```yaml
volumes:
  - /home/your-user:/home/your-user  # match your BASE_DIR
  - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
```

## Security

Access is protected by an API key sent as an `X-API-Key` header (or query parameter for WebSocket/SSE connections). The key is stored in `localStorage` in the browser after first entry.

This is designed for personal use over a trusted network or behind a reverse proxy with HTTPS. Do not expose it directly to the public internet without TLS.
