from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from typing import Any
from uuid import uuid4

import httpx

from .config import settings
from .datasource import DataUnavailableError, RealStreamSource
from .models import DashboardState, ReplayMode
from .scoring import score_snapshot
from .services.alerts import AlertManager
from .services.database import insert_snapshot, load_recent_snapshots
from .services.pubsub import RedisPubSub


class RiskEngine:
    def __init__(self) -> None:
        self.source = RealStreamSource()
        self.history: deque[dict[str, Any]] = deque(maxlen=settings.history_limit)
        self._listeners: set[asyncio.Queue[dict[str, Any]]] = set()
        self._task: asyncio.Task[None] | None = None
        self._pubsub_task: asyncio.Task[None] | None = None
        self.pubsub = RedisPubSub()
        self.alerts = AlertManager()
        self.mode = ReplayMode.live
        self._replay_task: asyncio.Task[None] | None = None
        self._instance_id = uuid4().hex

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
            if settings.redis_enabled:
                self._pubsub_task = asyncio.create_task(self._run_pubsub_listener())

    async def stop(self) -> None:
        for task in (self._task, self._pubsub_task, self._replay_task):
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        await self.source.close()
        await self.pubsub.close()

    async def _run_live(self) -> None:
        while True:
            if self.mode == ReplayMode.live:
                try:
                    snapshot = await self.source.next()
                    if snapshot is not None:
                        state = score_snapshot(snapshot)
                        await self._publish(state.model_dump(mode="json"), source="real-stream")
                except (DataUnavailableError, httpx.HTTPError, KeyError, ValueError) as exc:
                    print(f"Upstream refresh failed: {exc}")
            await asyncio.sleep(settings.update_interval_seconds)

    async def _run_pubsub_listener(self) -> None:
        async for message in self.pubsub.subscribe():
            if message["origin"] != self._instance_id:
                await self._broadcast(message["payload"])

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        self.history.append(payload)
        for q in list(self._listeners):
            await q.put(payload)

    async def _publish(self, payload: dict[str, Any], source: str) -> None:
        await insert_snapshot(source=source, payload=payload)
        await self._broadcast(payload)
        await self.pubsub.publish(payload, origin=self._instance_id)
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
            await self._broadcast(payload)
            await self.pubsub.publish(payload, origin=self._instance_id)
            await asyncio.sleep(delay)
        self.mode = ReplayMode.live
