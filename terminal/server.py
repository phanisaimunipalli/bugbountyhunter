import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Bounty Hunter Terminal")

_event_buffer: list[dict] = []
_subscribers: list[asyncio.Queue] = []


def emit_event(agent: str, message: str, run_id: str = "") -> None:
    event = {
        "agent": agent.upper(),
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "run_id": run_id,
    }
    _event_buffer.append(event)
    if len(_event_buffer) > 200:
        _event_buffer.pop(0)
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def _event_generator() -> AsyncIterator[dict]:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    try:
        for buffered in _event_buffer[-50:]:
            yield {"data": json.dumps(buffered)}
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
                yield {"data": json.dumps(event)}
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"ping": True})}
    finally:
        _subscribers.remove(q)


@app.get("/stream")
async def stream():
    return EventSourceResponse(_event_generator())


@app.post("/trigger")
async def trigger_run():
    from orchestrator.engine import run_pipeline
    run_id = str(uuid.uuid4())[:8]
    asyncio.create_task(run_pipeline(run_id))
    return {"run_id": run_id, "status": "started"}


@app.get("/")
async def root():
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
