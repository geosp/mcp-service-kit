import logging
import os
import socket

import pytest

from mcp_service_kit import RedisCacheConfig
from mcp_service_kit.cache import create_redis_store


@pytest.fixture
def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def test_unreachable_redis_falls_back(unused_port, caplog):
    store = create_redis_store(
        RedisCacheConfig(host="127.0.0.1", port=unused_port, timeout=0.5)
    )
    with caplog.at_level(logging.DEBUG, logger="mcp_service_kit.cache"):
        await store.put("key", {"value": 1})
        assert await store.get("key") is None
        assert await store.delete("key") is False
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "operating without caching" in warnings[0].getMessage()


@pytest.mark.skipif("TEST_REDIS_PORT" not in os.environ, reason="set TEST_REDIS_PORT to run")
async def test_round_trip_with_real_redis():
    store = create_redis_store(
        RedisCacheConfig(host="127.0.0.1", port=int(os.environ["TEST_REDIS_PORT"]), ttl=60)
    )
    await store.put("key", {"value": 1})
    assert await store.get("key") == {"value": 1}
    assert 0 < (await store.ttl("key"))[1] <= 60
    assert await store.delete("key") is True
    assert await store.get("key") is None
