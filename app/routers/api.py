from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import settings
from app.engine import RiskEngine
from app.models import ReplayRequest
from app.services.auth import require_token
from app.services.database import load_recent_snapshots


def build_router(engine: RiskEngine) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/state")
    async def state():
        return {
            "latest": engine.latest(),
            "history": engine.history_payload(),
            "mode": engine.mode,
        }

    @router.get("/history")
    async def history(limit: int = settings.replay_default_limit, _: None = Depends(require_token)):
        return {"history": await load_recent_snapshots(limit)}

    @router.post("/replay")
    async def replay(request: ReplayRequest, _: None = Depends(require_token)):
        await engine.replay(request.limit, request.speed_multiplier)
        return {"status": "started", "mode": engine.mode}

    return router
