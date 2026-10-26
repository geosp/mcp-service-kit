# mcp-service-kit

A small library for building [FastMCP](https://gofastmcp.com) servers. Subclass two
base classes and you get:

- stdio and HTTP (streamable HTTP) transports
- a standard CLI: `--mode stdio|http`, `--host`, `--port`, `--no-auth`, `--log-level`
- configuration from environment variables and `.env`, via pydantic-settings
- hooks for an HTTP auth provider and FastMCP middleware
- an optional Redis-backed key-value store (`[redis]` extra)

It has no REST API and no built-in identity provider.

For how the pieces fit together, with diagrams, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Install

The package isn't on PyPI yet. Install a tagged release straight from GitHub
(see [Releases](https://github.com/geosp/mcp-service-kit/releases) for available versions):

```bash
# core
pip install "mcp-service-kit @ git+https://github.com/geosp/mcp-service-kit@v0.2.0"
# with create_redis_store()
pip install "mcp-service-kit[redis] @ git+https://github.com/geosp/mcp-service-kit@v0.2.0"

# with uv (records the exact commit in uv.lock)
uv add "mcp-service-kit[redis] @ git+https://github.com/geosp/mcp-service-kit" --tag v0.2.0
```

To depend on it from another project, pin the tag in `pyproject.toml`:

```toml
dependencies = [
    "mcp-service-kit[redis] @ git+https://github.com/geosp/mcp-service-kit@v0.2.0",
]
```

Each GitHub Release also has the built wheel attached, if you'd rather install a file.

Requires Python 3.11+ and FastMCP 4.1+.

### Upgrading from 0.1

- HTTP servers whose `create_auth_provider()` returns `None` now refuse to start. Return
  an auth provider, or add `--no-auth` (`MCP_AUTH_ENABLED=false`) to the HTTP launch
  command to keep serving without auth.
- The MCP endpoint is `/mcp`, with no trailing slash. The server always served `/mcp`; only
  the logs and docs were wrong. Point clients and gateways at `/mcp` to avoid a 307 redirect.

See [CHANGELOG.md](CHANGELOG.md).

## Quickstart

```python
# my_server.py
from fastmcp import FastMCP

from mcp_service_kit import BaseMCPServer, BaseServerConfig, BaseService, create_main_with_modes


class GreetingService(BaseService):
    def initialize(self) -> None:
        pass

    def get_service_name(self) -> str:
        return "greeting"

    def register_mcp_tools(self, mcp: FastMCP) -> None:
        @mcp.tool()
        def greet(name: str) -> str:
            """Greet someone by name"""
            return f"Hello, {name}!"


class GreetingServer(BaseMCPServer):
    service_title = "Greeting MCP Server"
    service_description = "Says hello"
    service_version = "0.1.0"


main = create_main_with_modes(
    GreetingServer,
    service_factory=lambda config: GreetingService(),
    config_factory=BaseServerConfig,
    service_name="greeting-server",
)

if __name__ == "__main__":
    main()
```

```bash
python my_server.py --mode stdio                       # for local MCP clients
python my_server.py --mode http --port 3000 --no-auth  # local use only: serves http://localhost:3000/mcp
```

`GreetingServer` has no auth provider, so over HTTP it needs `--no-auth`. Without it the
server refuses to start (see [Authentication](#authentication)).

To debug interactively, run `npx @modelcontextprotocol/inspector` and point it at either transport.

`config_factory` can return a `BaseServerConfig` or your own config object with a
`server: BaseServerConfig` field. In the second case the whole object goes to
`service_factory` and `config.server` goes to the server. See
[examples/translation](examples/translation/config.py).

## Configuration

Config classes are pydantic-settings models. Instantiating one reads its variables, so
`BaseServerConfig()` reads the ones below. The CLI flags set them, and the flags take
precedence over `.env`. Pass `_env_prefix="APP_"` to read a different prefix.

| Variable           | CLI flag    | Default   |
|--------------------|-------------|-----------|
| `MCP_TRANSPORT`    | `--mode`    | `stdio`   |
| `MCP_HOST`         | `--host`    | `0.0.0.0` |
| `MCP_PORT`         | `--port`    | `3000`    |
| `MCP_AUTH_ENABLED` | `--no-auth` | `true`    |

Logs go to stderr so they never mix with the stdio protocol stream.

For your own settings, subclass `pydantic_settings.BaseSettings` and combine the sections in
one model. See [examples/translation/config.py](examples/translation/config.py).

## Server hooks

Besides the three required properties, `BaseMCPServer` has optional overrides:

| Override                 | Default | Purpose                                                    |
|--------------------------|---------|------------------------------------------------------------|
| `instructions`           | `None`  | Guidance sent to clients on connect, telling their LLM how to use your tools |
| `create_middleware()`    | `[]`    | FastMCP middleware, e.g. `ResponseCachingMiddleware`, `RateLimitingMiddleware` |
| `create_auth_provider()` | `None`  | Auth for HTTP transport (see below)                        |
| `validate_configuration()` | no-op | Extra startup checks; raise `ValueError` to abort        |

`service_version` is reported to clients as the server version.

## Authentication

Authentication applies only to HTTP transport. Override `create_auth_provider()` to
return any FastMCP `AuthProvider`. For example, you can verify JWTs from your identity
provider:

```python
from fastmcp.server.auth import JWTVerifier


class GreetingServer(BaseMCPServer):
    ...

    def create_auth_provider(self):
        return JWTVerifier(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="greeting-server",
        )
```

The hook runs only when the transport is `http` and `MCP_AUTH_ENABLED` is true.
If it returns `None` (the default), the HTTP server refuses to start: `run()` logs a
configuration error and exits with code 1. To serve without auth, for example locally,
pass `--no-auth` (`MCP_AUTH_ENABLED=false`). The server then logs one warning.

## Running under an ASGI server

`create_asgi_app()` returns the FastMCP Starlette app, so you can run it with uvicorn or
gunicorn:

```python
# asgi.py
from mcp_service_kit import BaseServerConfig

# No auth provider, so auth must be off, or create_asgi_app() raises ValueError
config = BaseServerConfig(transport="http", auth_enabled=False)
app = GreetingServer(config, GreetingService()).create_asgi_app()
```

```bash
uvicorn asgi:app --port 3000
```

## Redis cache

`create_redis_store()` returns a py-key-value `AsyncKeyValue` store, the same storage
interface FastMCP uses:

```python
from mcp_service_kit import RedisCacheConfig
from mcp_service_kit.cache import create_redis_store

store = create_redis_store(RedisCacheConfig())   # reads MCP_REDIS_*
await store.put("key", {"value": 1}, collection="translations", ttl=3600)
await store.get("key", collection="translations")
```

It reads `MCP_REDIS_HOST`, `_PORT`, `_DB`, `_PASSWORD`, `_NAMESPACE` (the default
collection), `_TTL` (the default TTL) and `_TIMEOUT`. If Redis is unreachable or times out,
reads return `None` and writes are dropped. A single warning is logged and the service
keeps working without caching.

To cache whole tool results instead, pass the store to FastMCP's middleware:

```python
from fastmcp.server.middleware.caching import ResponseCachingMiddleware


class GreetingServer(BaseMCPServer):
    ...

    def create_middleware(self):
        return [ResponseCachingMiddleware(cache_storage=create_redis_store())]
```

## Utilities

- `mcp_service_kit.utils.inject_docstring`: sets a function's docstring from a string or callable.
- `mcp_service_kit.utils.load_instruction`: reads a markdown file next to a module.

## Development

```bash
uv sync --all-extras
uv run pytest
# optional: also test against a real Redis
docker run -d --rm -p 56379:6379 redis:8-alpine && TEST_REDIS_PORT=56379 uv run pytest
uv run ruff check
uv run python -m examples.translation.server --mode stdio
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs on every pull request and push to
`main`:
- ruff;
- the tests on Python 3.11 and 3.14 against a real Redis;
- the tests against the minimum dependency versions;
- a check that the built wheel imports without the `[redis]` extra.

## Releasing

Releases are git tags on `main`. The version comes from the tag (via `hatch-vcs`), so there's
no version number to edit by hand.

```bash
git checkout main && git pull
git tag v0.2.0            # semver; use v0.2.0-rc1 for a prerelease
git push origin v0.2.0
```

The [release workflow](.github/workflows/release.yml) then:
1. runs the full CI suite;
2. checks that the tag is on `main` and that the built version matches it;
3. creates a GitHub Release with generated notes and the wheel and sdist attached. Tags
   containing `-` are marked as prereleases.

Untagged builds get a development version such as `0.2.1.dev3+g1a2b3c4`. Publishing to PyPI
can be added later as one more job in the release workflow, using trusted publishing.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
