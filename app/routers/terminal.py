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
    """Read output from the SSH process and forward it to the browser over WebSocket."""
    try:
        async for data in process.stdout:
            await websocket.send_text(data)
    except asyncssh.ChannelOpenError:
        pass


async def ws_to_pty(websocket: WebSocket, process: asyncssh.SSHClientProcess):
    """Receive keystrokes from the browser and write them to the SSH process stdin."""
    try:
        while True:
            text = await websocket.receive_text()
            process.stdin.write(text)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws")
async def stream_terminal(websocket: WebSocket, api_key: str = Query(...)):
    if api_key != settings.api_key:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Open an SSH connection to the host VPS using the mounted private key.
    # known_hosts=None skips host key verification (safe since we're connecting
    # to ourselves over the Docker bridge, not the open internet).
    async with asyncssh.connect(
        host=settings.ssh_host,
        port=settings.ssh_port,
        username=settings.ssh_user,
        client_keys=[settings.ssh_key_path],
        known_hosts=None,
    ) as conn:
        # Start an interactive shell session with a proper terminal type so
        # colours, prompts, and control sequences render correctly in the browser.
        async with conn.create_process(term_type="xterm-256color") as process:
            await asyncio.gather(
                pty_to_ws(websocket, process),
                ws_to_pty(websocket, process),
                return_exceptions=True,
            )
