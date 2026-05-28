from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.config import settings


CHANNEL = "private-credit-risk-updates"


class RedisPubSub:
    def __init__(self) -> None:
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def publish(self, payload: dict) -> None:
        await self.redis.publish(CHANNEL, json.dumps(payload))

    async def subscribe(self) -> AsyncIterator[dict]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("data"):
                    yield json.loads(message["data"])
                await asyncio.sleep(0.05)
        finally:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.close()
