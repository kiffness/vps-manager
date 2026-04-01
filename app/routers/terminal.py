import asyncio
import os
import pty
import subprocess

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.config import settings

router = APIRouter(
    prefix="/api/terminal",
    tags=["terminal"],
    responses={
        403: {"description": "forbidden"}
    }
)


async def pty_to_ws(websocket: WebSocket, master_fd: int, loop: asyncio.AbstractEventLoop):
    """Read output from the PTY (bash) and forward it to the browser over WebSocket."""
    try:
        while True:
            # os.read is a blocking call, so we run it in a thread pool to avoid
            # blocking the async event loop. It returns raw bytes from the terminal.
            data = await loop.run_in_executor(None, os.read, master_fd, 1024)
            await websocket.send_bytes(data)
    except OSError:
        # OSError means the PTY master fd is gone — bash has exited. Stop the task.
        pass


async def ws_to_pty(websocket: WebSocket, master_fd: int):
    """Receive keystrokes from the browser over WebSocket and write them to the PTY (bash)."""
    try:
        while True:
            # Wait for the next text message from the browser (a keystroke or paste).
            text = await websocket.receive_text()
            # Write the input into the PTY master — bash sees it as keyboard input.
            os.write(master_fd, text.encode())
    except WebSocketDisconnect:
        # Browser disconnected. Stop the task.
        pass


@router.websocket("/ws")
async def stream_terminal(websocket: WebSocket, api_key: str = Query(...)):
    if api_key != settings.api_key:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Open a pseudo-terminal (PTY). This gives us two connected file descriptors:
    # - master_fd: our side — we read output and write input here
    # - slave_fd:  bash's side — it uses this as its stdin/stdout/stderr
    master_fd, slave_fd = pty.openpty()

    # Start bash, connected to the slave end of the PTY.
    process = subprocess.Popen(
        ["/usr/bin/bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    # Close the slave fd in the parent process — only bash needs it.
    os.close(slave_fd)

    loop = asyncio.get_event_loop()

    try:
        # Run both directions concurrently. gather() keeps them alive side by side
        # without either one cancelling the other. If either task finishes, the
        # return_exceptions=True means the other isn't silently killed.
        await asyncio.gather(
            pty_to_ws(websocket, master_fd, loop),
            ws_to_pty(websocket, master_fd),
            return_exceptions=True,
        )
    finally:
        process.kill()
        os.close(master_fd)
