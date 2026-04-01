import asyncio
import asyncssh

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.config import settings

router = APIRouter(
    prefix="/api/terminal",
    tags=["terminal"],
    responses={
        403: {"description": "forbidden"}
    }
)


async def pty_to_ws(websocket: WebSocket, process: asyncssh.SSHClientProcess):
    """Read raw bytes from the SSH process and forward them to the browser."""
    try:
        while True:
            data = await process.stdout.read(1024)
            if not data:
                break
            await websocket.send_bytes(data)
    except (asyncssh.ChannelOpenError, asyncssh.ConnectionLost):
        pass


async def ws_to_pty(websocket: WebSocket, process: asyncssh.SSHClientProcess):
    """Receive keystrokes from the browser and write them to the SSH process stdin."""
    try:
        while True:
            text = await websocket.receive_text()
            process.stdin.write(text.encode())
            await process.stdin.drain()
    except WebSocketDisconnect:
        pass


@router.websocket("/ws")
async def stream_terminal(websocket: WebSocket, api_key: str = Query(...)):
    if api_key != settings.api_key:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    async with asyncssh.connect(
        host=settings.ssh_host,
        port=settings.ssh_port,
        username=settings.ssh_user,
        client_keys=[settings.ssh_key_path],
        known_hosts=None,
    ) as conn:
        # encoding=None gives raw bytes — avoids text buffering which delays echo
        async with conn.create_process(term_type="xterm-256color", encoding=None) as process:
            await asyncio.gather(
                pty_to_ws(websocket, process),
                ws_to_pty(websocket, process),
                return_exceptions=True,
            )
