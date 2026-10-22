"""
mcp-service-kit: build FastMCP servers with stdio and HTTP transports

Subclass BaseService for your tools and BaseMCPServer for the server, then
use create_main_with_modes() for a standard CLI. The optional Redis cache
lives in mcp_service_kit.cache and needs the [redis] extra.
"""

from importlib.metadata import PackageNotFoundError, version

from .config import (
    BaseCacheConfig,
    BaseServerConfig,
    RedisCacheConfig,
)
from .server import (
    BaseMCPServer,
    BaseService,
    apply_cli_args_to_environment,
    create_main_with_modes,
    create_server,
    create_standard_cli_parser,
)

try:
    __version__ = version("mcp-service-kit")
except PackageNotFoundError:  # pragma: no cover - running from a source tree without install
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "BaseCacheConfig",
    "BaseServerConfig",
    "RedisCacheConfig",
    "BaseMCPServer",
    "BaseService",
    "create_server",
    "create_standard_cli_parser",
    "apply_cli_args_to_environment",
    "create_main_with_modes",
]
