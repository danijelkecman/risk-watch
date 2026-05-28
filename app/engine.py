from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from .config import settings
from .datasource import MockStreamSource
from .models import DashboardState, ReplayMode
from .scoring import score_snapshot
from .services.alerts import AlertManager
from .services.database import insert_snapshot, load_recent_snapshots
from .services.pubsub import RedisPubSub


class RiskEngine:
    def __init__(self) -> None:
        self.source = MockStreamSource()
        self.history: deque[dict[str, Any]] = deque(maxlen=settings.history_limit)
        self._listeners: set[asyncio.Queue[dict[str, Any]]] = set()
        self._task: asyncio.Task[None] | None = None
        self.pubsub = RedisPubSub()
        self.alerts = AlertManager()
        self.mode = ReplayMode.live
        self._replay_task: asyncio.Task[None] | None = None

    async def bootstrap(self) -> None:
        recent = await load_recent_snapshots(settings.history_limit)
        for item in recent:
            self.history.append(item)

    def latest(self) -> dict[str, Any] | None:
        return self.history[-1] if self.history else None

    def history_payload(self) -> list[dict[str, Any]]:
        return list(self.history)

    def register_listener(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._listeners.add(q)
        return q

    def unregister_listener(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._listeners.discard(q)

    async def start(self) -> None:
        if self._task is None:
            await self.bootstrap()
            self._task = asyncio.create_task(self._run_live())
            asyncio.create_task(self._run_pubsub_listener())

    async def _run_live(self) -> None:
        while True:
            if self.mode == ReplayMode.live:
                snapshot = self.source.next()
                state = score_snapshot(snapshot)
                payload = state.model_dump(mode="json")
                await self._publish(payload, source="mock")
            await asyncio.sleep(settings.update_interval_seconds)

    async def _run_pubsub_listener(self) -> None:
        async for payload in self.pubsub.subscribe():
            self.history.append(payload)
            for q in list(self._listeners):
                await q.put(payload)

    async def _publish(self, payload: dict[str, Any], source: str) -> None:
        await insert_snapshot(source=source, payload=payload)
        self.history.append(payload)
        await self.pubsub.publish(payload)
        state = DashboardState.model_validate(payload)
        await self.alerts.maybe_send(state)

    async def replay(self, limit: int, speed_multiplier: float) -> None:
        if self._replay_task and not self._replay_task.done():
            self._replay_task.cancel()
        self.mode = ReplayMode.replay
        self._replay_task = asyncio.create_task(self._run_replay(limit, speed_multiplier))

    async def _run_replay(self, limit: int, speed_multiplier: float) -> None:
        history = await load_recent_snapshots(limit)
        delay = max(settings.update_interval_seconds / speed_multiplier, 0.05)
        for payload in history:
            await self.pubsub.publish(payload)
            await asyncio.sleep(delay)
        self.mode = ReplayMode.live
