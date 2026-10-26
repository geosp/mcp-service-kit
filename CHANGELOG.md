# Changelog

## 0.2.1

### Fixed

- `MCP_TRANSPORT` now selects the transport when `--mode` isn't passed, as the README
  documents. Before, the CLI's `--mode` default (`stdio`) always overwrote it. `--mode`
  still takes precedence, and the default is still stdio when neither is set. If
  `MCP_TRANSPORT=http` is set in the environment or a `.env` file, a launch without
  `--mode` now starts HTTP; pass `--mode stdio` to force stdio.

## 0.2.0

### Breaking

- **HTTP fails closed when there is no auth provider.** If the transport is `http`, auth is
  enabled (the default) and `create_auth_provider()` returns `None` (also the default),
  the server now refuses to start instead of serving every tool without authentication.
  `create_mcp_app()` and `create_asgi_app()` raise `ValueError`; `run()` logs
  `Configuration error: ...` and exits with code 1. To serve without auth, return an
  `AuthProvider` or pass `--no-auth` (`MCP_AUTH_ENABLED=false`). stdio is unaffected.

### Added

- `BaseMCPServer.http_endpoint_url()` returns the URL of the MCP endpoint, built from the
  configured host and port and FastMCP's streamable HTTP path.

### Fixed

- The startup log, the CLI help and the docs now give the endpoint as `/mcp`, the path
  FastMCP actually serves. They used to say `/mcp/` with a trailing slash, which only
  answers with a 307 redirect.
- `--no-auth` logs a single warning instead of two.
