import json
from typing import Optional

from redis.asyncio import Redis
from vkbottle import ABCStateDispenser, BaseStateGroup, StatePeer


class RedisStateDispenser(ABCStateDispenser):
    def __init__(self, redis_url: str, key_prefix: str, ttl_seconds: int = 86400):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix.rstrip(":")
        self._ttl_seconds = ttl_seconds

    def _key(self, peer_id: int) -> str:
        return f"{self._key_prefix}:{peer_id}"

    async def get(self, peer_id: int) -> Optional[StatePeer]:
        raw = await self._redis.get(self._key(peer_id))
        if not raw:
            return None
        data = json.loads(raw)
        return StatePeer(
            peer_id=peer_id,
            state=data["state"],
            payload=data.get("payload", {}),
        )

    async def set(self, peer_id: int, state: BaseStateGroup, **payload):
        state_value = str(state)
        data = {"state": state_value, "payload": payload}
        await self._redis.set(
            self._key(peer_id),
            json.dumps(data, ensure_ascii=False),
            ex=self._ttl_seconds,
        )

    async def delete(self, peer_id: int):
        await self._redis.delete(self._key(peer_id))

    async def close(self):
        await self._redis.close()

    async def healthcheck(self) -> bool:
        return bool(await self._redis.ping())
