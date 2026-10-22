# mcp-service-kit — Implementation Plan

## Goal
`mcp-service-kit` is a small library for building FastMCP servers. You import it, subclass
`BaseService`, and get stdio and HTTP transports, a standard CLI, env-based config and an
optional Redis cache. It has no REST API and no built-in identity provider.

## Starting state
`src/mcp_service_kit/` is an unmodified copy of `mcp-weather/core/`. Every import in it
still says `from core...`. `src/mcp_service_kit/README.md` is the old `core/` README and
describes REST and Authentik. `examples/translation/` is an unmodified copy of the
mcp-weather translation example. It imports from both `core.*` and `mcp_translation.*`, and it
builds a nested `AppConfig` with `server`, `redis_cache`, `translation_api` and `authentik`
fields. It also declares CORS origins and discovers `routes.py` modules with importlib.

## Target layout
```
pyproject.toml          # hatchling, src layout, name mcp-service-kit, version from git tags (hatch-vcs), requires-python >=3.11
README.md               # replaces src/mcp_service_kit/README.md, which gets deleted
src/mcp_service_kit/
  __init__.py           # explicit __all__
  py.typed
  server.py             # BaseService, BaseMCPServer, create_main_with_modes, CLI helpers
  config.py             # BaseServerConfig, BaseCacheConfig, RedisCacheConfig (pydantic-settings)
  cache.py              # create_redis_store() -> py-key-value AsyncKeyValue (needs the [redis] extra)
  utils/                # inject_docstring, load_instruction (unchanged)
examples/__init__.py    # makes `python -m examples.translation.server` work
examples/translation/   # MCP-only port
tests/
```

## Steps
0. **Baseline commit.** Commit the unmodified copies before changing anything, so every later step shows up as a reviewable diff against the original `core/`.
1. **Rename imports.** Change `from core.` and `import core` to `mcp_service_kit` everywhere. Most of `core` already uses relative imports. The absolute ones are in `cache.py` and `auth_mcp.py`.
2. **Delete Authentik:** `auth_mcp.py`, `auth_rest.py`, `authentik_client.py`, and `AuthentikConfig` in `config.py`. Remove their exports from `__init__.py`. This also removes the stray `mcp_weather` import (`auth_rest.py:89`) and the undeclared `requests` dependency.
3. **Delete REST from `server.py`.** Remove these from `BaseMCPServer`: `create_router`, `register_exception_handlers`, `create_fastapi_app`, `run_rest_and_mcp`, `allowed_cors_origins`, the FastAPI-based `create_app()`, the OpenAPI OPTIONS middleware and the CORS setup. Remove the `fastapi` imports.
4. **Pass-through auth.** Replace the abstract `create_auth_provider()` with a non-abstract hook, `def create_auth_provider(self) -> AuthProvider | None: return None`, typed with `fastmcp.server.auth.AuthProvider`. `create_mcp_app()` uses it only when the transport is HTTP and `auth_enabled` is true. Log a warning when HTTP runs with no provider.
5. **Simplify run modes.** `run()` picks stdio or HTTP from `transport` only. Delete `mcp_only` and `run_mcp_only` (it's always MCP-only now). Add `create_asgi_app()` that returns `mcp.http_app()`, so the server can run under uvicorn or gunicorn.
6. **Simplify the CLI.** In `create_standard_cli_parser`, `--mode` becomes `stdio|http` (drop `rest`). Drop the `MCP_ONLY` env var in `apply_cli_args_to_environment`. Keep `--no-auth`, which only matters when a provider exists.
7. **Remove the two-level config lookups.** `BaseMCPServer.__init__(self, config: BaseServerConfig, service)` takes the server config directly. Read `self.config.<field>` and drop `flatdict` and `get_config()`. If an app has a nested config like the example's `AppConfig`, it passes `app_config.server` to the server. Its other sections go to the service, which it builds before the server.
8. **Remove side effects on import.**
   - Remove `logging.basicConfig` from `server.py` and call it inside `create_main_with_modes()`, using the `--log-level` argument.
   - Remove `load_dotenv()` from `config.py` and call it inside `create_main_with_modes()` (with a `load_env: bool = True` parameter). Also stop re-exporting `load_dotenv` from `config.py`, because the example imports it from there.
9. **Clean up `config.py` and `cache.py`.**
   - Redis host defaults to `localhost`, not `redis.mixwarecs-home.net`.
   - Namespace defaults to `"mcp-cache"`.
   - Change the cache log line to say "operating without caching".
   - Raise a clear `ImportError` that mentions `pip install mcp-service-kit[redis]` when aiocache is missing.
10. **Dependencies.** Floors are the versions we test against (see step 15). Base: `fastmcp>=4.1.3`, `pydantic>=2.14`, `pydantic-settings>=2.16`, `python-dotenv>=1.2`. Extra `[redis]`: `py-key-value-aio[redis]>=0.4.6`. Extra `[dev]`: `pytest>=9.1`, `pytest-asyncio>=1.4`, `ruff>=0.17`.
11. **Docs.** Write a README with a quickstart: subclass `BaseService`, write `create_main_with_modes(...)`, run it with `--mode stdio` or `--mode http`. Include an auth example that overrides `create_auth_provider()` with a FastMCP `JWTVerifier`. Fix the docstrings that mention weather or `core.server` (for example `server.py:5` and `server.py:661`). Delete `src/mcp_service_kit/README.md`.
12. **Port the example.** In `examples/translation/`:
    - Delete every `features/*/routes.py`. In `server.py`, remove the importlib route discovery, the FastAPI imports and exception handlers, `allowed_cors_origins` and the Authentik-based `create_auth_provider` override.
    - In `config.py`, drop `cors_origins`, the `authentik` field and its `AuthentikConfig` import.
    - Change `core.*` imports to `mcp_service_kit`. Change `mcp_translation.*` imports to relative imports.
    - Build the server with `TranslationMCPServer(config.server, mcp_service)` (see step 7).
    - Add `examples/__init__.py`.
13. **Tests:**
    - Each config class loads the right values from its environment variables.
    - CLI arguments map to the right env vars.
    - `create_mcp_app()` registers a dummy service's tools. Use `fastmcp.Client` in-memory to call one.
    - The auth hook is used only when the transport is HTTP and auth is enabled.
    - The Redis store falls back to no caching when Redis is unreachable, and warns once. Point it at an unused localhost port, so the test runs without a Redis server.
    - A round-trip test against a real Redis runs when `TEST_REDIS_PORT` is set.
    - `instructions`, `service_version` and `create_middleware()` reach FastMCP.

### Modernization (added after the port)
After the port, the libraries were checked for current versions and current recommended usage.
14. **Python.** `.python-version` is 3.14 (current stable). `requires-python` is `>=3.11`, because pydantic-settings 2.16 requires it and 3.10 reaches end of life in October 2026.
15. **Version floors.** Raise every floor to the version actually tested (step 10). CI-style check: run the tests with `--resolution lowest-direct` on Python 3.11.
16. **Config on pydantic-settings.** Config classes subclass `BaseSettings` with an `env_prefix` (`MCP_`, `MCP_REDIS_`, `MCP_CACHE_`) and drop the hand-written `from_env()` methods. Instantiating a class reads the environment. `_env_prefix=` overrides the prefix. `transport` is `Literal["stdio", "http"]`, so bad values fail validation. `BaseCacheConfig.cache_dir` becomes `path`.
17. **Replace aiocache.** aiocache has had no release since 2024-09 and calls APIs that redis-py has deprecated. Replace `RedisCacheClient` with `create_redis_store()`. It returns py-key-value's `RedisStore`, which FastMCP itself uses, wrapped like this:
    - `TimeoutWrapper` bounds each operation.
    - `FallbackWrapper` falls back to a `NullStore` that logs once.
    - `TTLClampWrapper` applies the default TTL.
    The Redis client has retries disabled, so a down Redis fails fast instead of adding backoff to every call. The store also works with FastMCP's `ResponseCachingMiddleware`.
18. **Use FastMCP's own APIs.**
    - Run transports with `mcp.run(transport=...)` instead of calling uvicorn directly, and drop `uvicorn` as a direct dependency.
    - Pass `version` and an optional `instructions` property to `FastMCP(...)`.
    - Add a `create_middleware()` hook.
    - `validate_configuration()` becomes a no-op hook, because pydantic validates the transport.

### Releases (added after modernization)
19. **Version from git tags.** `hatch-vcs` derives the version (`v0.2.0` → `0.2.0`, untagged → `.devN`). `mcp_service_kit.__version__` reads it from package metadata. `[project.urls]` points to `github.com/geosp/mcp-service-kit`.
20. **CI** (`.github/workflows/ci.yml`), on pull requests, pushes to `main` and `workflow_call`:
    - ruff;
    - pytest on Python 3.11 and 3.14 with a Redis service container;
    - the minimum-versions test;
    - a check that the wheel imports without `[redis]`.
21. **Release** (`.github/workflows/release.yml`), on `v*` tags:
    - reruns CI;
    - requires the tag to be on `main` and the wheel version to match the tag;
    - creates a GitHub Release with `gh release create` (generated notes, wheel and sdist attached, `-` tags marked prerelease).

    No PyPI publishing for now; installs come from git tags. Branch model: `main` plus pull requests, with releases tagged on `main`.

## Out of scope
- Any change to `mcp-weather`. Migrating it to this library is a later, separate task.
- Pushing to GitHub or creating tags (done by the maintainer), and publishing to PyPI.

## Verification
- `uv sync --all-extras && uv run pytest`
- Against real Redis: `docker run -d --rm -p 56379:6379 redis:8-alpine` then `TEST_REDIS_PORT=56379 uv run pytest`.
- Version floors: `uv run --python 3.11 --resolution lowest-direct --all-extras pytest` in a separate environment (`UV_PROJECT_ENVIRONMENT=...`). Afterwards, run `uv lock --resolution highest`, because the lowest-resolution run rewrites `uv.lock`.
- `uv run ruff check`
- `grep -rniE "authentik|fastapi|weather|from core|mcp_translation|cors|aiocache" src/ examples/` returns nothing.
- `uv run python -m examples.translation.server --mode stdio`, or its entry point, starts. Test it with `npx @modelcontextprotocol/inspector`.
- `--mode http --port 3000` serves MCP at `http://localhost:3000/mcp/`.
- `uv build` produces a wheel. Install that wheel in a scratch venv and check that `import mcp_service_kit` works without the `[redis]` extra.
