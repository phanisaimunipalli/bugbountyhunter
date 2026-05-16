import asyncio
import uuid
import uvicorn
from config.settings import settings
from terminal.server import app, emit_event
from orchestrator.engine import run_pipeline


async def auto_run():
    run_id = str(uuid.uuid4())[:8]
    emit_event("ORCHESTRATOR", "Bounty Hunter online. Starting initial scan...", run_id)
    await run_pipeline(run_id)


async def main():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await asyncio.gather(
        server.serve(),
        auto_run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
