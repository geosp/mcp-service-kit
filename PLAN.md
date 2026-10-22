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
pyproject.toml          # hatchling, src layout, name mcp-service-kit, version 0.1.0, requires-python >=3.10
README.md               # replaces src/mcp_service_kit/README.md, which gets deleted
src/mcp_service_kit/
  __init__.py           # explicit __all__
  py.typed
  server.py             # BaseService, BaseMCPServer, create_main_with_modes, CLI helpers
  config.py             # BaseServerConfig, BaseCacheConfig, RedisCacheConfig
  cache.py              # RedisCacheClient (needs the [redis] extra)
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
10. **Dependencies.** Base: `fastmcp>=2.12`, `pydantic>=2`, `python-dotenv`, `uvicorn`. Extra `[redis]`: `aiocache>=0.12`, `redis>=5`. Extra `[dev]`: pytest, pytest-asyncio, ruff.
11. **Docs.** Write a README with a quickstart: subclass `BaseService`, write `create_main_with_modes(...)`, run it with `--mode stdio` or `--mode http`. Include an auth example that overrides `create_auth_provider()` with a FastMCP `JWTVerifier`. Fix the docstrings that mention weather or `core.server` (for example `server.py:5` and `server.py:661`). Delete `src/mcp_service_kit/README.md`.
12. **Port the example.** In `examples/translation/`:
    - Delete every `features/*/routes.py`. In `server.py`, remove the importlib route discovery, the FastAPI imports and exception handlers, `allowed_cors_origins` and the Authentik-based `create_auth_provider` override.
    - In `config.py`, drop `cors_origins`, the `authentik` field and its `AuthentikConfig` import.
    - Change `core.*` imports to `mcp_service_kit`. Change `mcp_translation.*` imports to relative imports.
    - Build the server with `TranslationMCPServer(config.server, mcp_service)` (see step 7).
    - Add `examples/__init__.py`.
13. **Tests:**
    - Each config's `from_env` loads the right values.
    - CLI arguments map to the right env vars.
    - `create_mcp_app()` registers a dummy service's tools. Use `fastmcp.Client` in-memory to call one.
    - The auth hook is used only when the transport is HTTP and auth is enabled.
    - `RedisCacheClient` falls back to no caching when Redis is unreachable. Point it at an unused localhost port with a short timeout, so the test runs without a Redis server.

## Out of scope
- Any change to `mcp-weather`. Migrating it to this library is a later, separate task.
- Pushing to GitHub or publishing to PyPI.

## Verification
- `uv sync --all-extras && uv run pytest`
- `uv run ruff check`
- `grep -rniE "authentik|fastapi|weather|from core|mcp_translation|cors" src/ examples/` returns nothing.
- `uv run python -m examples.translation.server --mode stdio`, or its entry point, starts. Test it with `npx @modelcontextprotocol/inspector`.
- `--mode http --port 3000` serves MCP at `http://localhost:3000/mcp/`.
- `uv build` produces a wheel. Install that wheel in a scratch venv and check that `import mcp_service_kit` works without the `[redis]` extra.
