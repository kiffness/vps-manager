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

@router.websocket("/ws")
async def stream_terminal(websocket: WebSocket, api_key: str = Query(...)):
    if api_key != settings.api_key:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    master_fd, slave_fd = pty.openpty()

    process = subprocess.Popen(
        ["/usr/bin/bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    loop = asyncio.get_event_loop()

    try:
        while True:
            pty_task = asyncio.create_task(
                loop.run_in_executor(None, os.read, master_fd, 1024)
            )
            ws_task = asyncio.create_task(websocket.receive_text())

            done, pending = await asyncio.wait(
                [pty_task, ws_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for t in pending:
                t.cancel()

            if pty_task in done:
                try:
                    data = pty_task.result()
                    await websocket.send_bytes(data)
                except OSError:
                    break

            if ws_task in done:
                try:
                    text = ws_task.result()
                    os.write(master_fd, text.encode())
                except WebSocketDisconnect:
                    break

    except (WebSocketDisconnect, OSError):
        pass
    finally:
        process.kill()
        os.close(master_fd)
