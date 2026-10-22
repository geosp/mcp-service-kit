"""
Optional Redis cache built on py-key-value

``create_redis_store()`` returns an ``AsyncKeyValue`` store, the same
interface FastMCP uses for its own storage. Use it directly in your service:

    store = create_redis_store()
    await store.put("key", {"value": 1}, collection="translations")
    await store.get("key", collection="translations")

or hand it to FastMCP's ``ResponseCachingMiddleware`` to cache tool results.

If Redis is unreachable or slow, operations fall back to a store that keeps
nothing, so the service keeps working without caching.

Requires the ``redis`` extra: ``pip install mcp-service-kit[redis]``.
"""

import logging

try:
    from key_value.aio.stores.redis import RedisStore
    from redis.asyncio import Redis
    from redis.asyncio.retry import Retry
    from redis.backoff import NoBackoff
except ImportError as e:  # pragma: no cover - depends on installed extras
    raise ImportError(
        "mcp_service_kit.cache requires the 'redis' extra. "
        "Install it with: pip install mcp-service-kit[redis]"
    ) from e

from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.null import NullStore
from key_value.aio.wrappers.fallback import FallbackWrapper
from key_value.aio.wrappers.timeout import TimeoutWrapper
from key_value.aio.wrappers.ttl_clamp import TTLClampWrapper

from .config import RedisCacheConfig

logger = logging.getLogger(__name__)


class UnavailableCacheStore(NullStore):
    """
    Store used when Redis fails: keeps nothing and warns once

    Later failures are logged at debug level so a Redis outage does not
    flood the logs.
    """

    def __init__(self, description: str) -> None:
        super().__init__(stable_api=True)
        self._description = description
        self._warned = False

    def _report(self) -> None:
        if not self._warned:
            logger.warning(
                f"Redis at {self._description} is unavailable: operating without caching"
            )
            self._warned = True
        else:
            logger.debug(f"Redis at {self._description} still unavailable")

    async def _get_managed_entry(self, *, key, collection):
        self._report()
        return await super()._get_managed_entry(key=key, collection=collection)

    async def _put_managed_entry(self, *args, **kwargs):
        self._report()
        return await super()._put_managed_entry(*args, **kwargs)

    async def _delete_managed_entry(self, *, key, collection):
        self._report()
        return await super()._delete_managed_entry(key=key, collection=collection)


def create_redis_store(config: RedisCacheConfig | None = None) -> AsyncKeyValue:
    """
    Create a Redis-backed key-value store that degrades to no caching

    Args:
        config: Redis configuration. Defaults to ``RedisCacheConfig()``,
            which reads the MCP_REDIS_* environment variables.

    Returns:
        An AsyncKeyValue store. Keys go to the ``config.namespace``
        collection unless another collection is given, and values without
        an explicit TTL expire after ``config.ttl`` seconds.
    """
    config = config or RedisCacheConfig()
    description = f"{config.host}:{config.port}/{config.db}"

    # No retries: when Redis is down, fail fast and fall back instead of
    # adding retry backoff to every cache operation.
    client = Redis(
        host=config.host,
        port=config.port,
        db=config.db,
        password=config.password,
        decode_responses=True,
        socket_connect_timeout=config.timeout,
        retry=Retry(NoBackoff(), retries=0),
    )
    redis = RedisStore(client=client, default_collection=config.namespace)
    store = FallbackWrapper(
        primary_key_value=TimeoutWrapper(redis, timeout=config.timeout),
        fallback_key_value=UnavailableCacheStore(description),
        write_to_fallback=True,
    )

    logger.info(f"Configured Redis cache at {description}")
    return TTLClampWrapper(store, min_ttl=1, max_ttl=float("inf"), missing_ttl=config.ttl)
