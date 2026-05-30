from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .engine import RiskEngine
from .routers.api import build_router
from .services.database import init_db


engine = RiskEngine()
templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await engine.start()
    try:
        yield
    finally:
        await engine.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(build_router(engine))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"app_name": settings.app_name})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = engine.register_listener()
    try:
        while True:
            payload = await queue.get()
            await websocket.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        pass
    finally:
        engine.unregister_listener(queue)
