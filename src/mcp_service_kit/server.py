"""
Base MCP server implementation for reusable server components

Provides abstract base classes and factory functions for creating FastMCP
servers that run over stdio or HTTP, with an optional authentication hook
and a standard command-line interface.
"""

import abc
import argparse
import logging
import os
import sys
from typing import Any, Callable, Optional, Type, TypeVar

import fastmcp
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import AuthProvider
from fastmcp.server.middleware import Middleware
from starlette.types import ASGIApp

from .config import BaseServerConfig

# Get module logger
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T')

TRANSPORTS = ("stdio", "http")
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class BaseService(abc.ABC):
    """
    Abstract base class for MCP services

    Service classes handle business logic and should be independent of the
    transport mechanism (HTTP, stdio).
    """

    @abc.abstractmethod
    def initialize(self) -> None:
        """
        Initialize the service

        This method is called during application startup to prepare
        any resources needed by the service.
        """
        pass

    @abc.abstractmethod
    def get_service_name(self) -> str:
        """
        Get the name of this service

        Returns:
            Name of the service (used as the FastMCP server name)
        """
        pass

    @abc.abstractmethod
    def register_mcp_tools(self, mcp: FastMCP) -> None:
        """
        Register MCP tools for this service

        This method should register all MCP tools provided by the service.

        Args:
            mcp: FastMCP instance to register tools with
        """
        pass

    def cleanup(self) -> None:
        """
        Clean up service resources

        This method is called during application shutdown to release
        any resources held by the service. Default implementation does nothing.
        """
        pass


class BaseMCPServer(abc.ABC):
    """
    Base class for MCP servers

    Provides common functionality for MCP servers including:
    - Server startup over stdio or HTTP
    - An optional authentication hook for HTTP transport
    - Service registration

    This class should be extended for specific service types.
    """

    def __init__(self, config: BaseServerConfig, service: BaseService):
        """
        Initialize the MCP server

        Args:
            config: Server configuration. Applications with a nested config
                pass its server section here (e.g. ``app_config.server``).
            service: Service instance to expose via MCP
        """
        self.config = config
        self.service = service
        self._mcp_app: Optional[FastMCP] = None

    @property
    @abc.abstractmethod
    def service_title(self) -> str:
        """
        Get the human-readable title for this MCP service
        """
        pass

    @property
    @abc.abstractmethod
    def service_description(self) -> str:
        """
        Get the description for this MCP service
        """
        pass

    @property
    @abc.abstractmethod
    def service_version(self) -> str:
        """
        Get the version string for this MCP service
        """
        pass

    @property
    def instructions(self) -> str | None:
        """
        Optional instructions sent to MCP clients on initialization

        Override this to tell clients' LLMs how to use the server's tools.
        """
        return None

    def create_middleware(self) -> list[Middleware]:
        """
        Create FastMCP middleware for this server

        Override this to add middleware such as FastMCP's
        ``ResponseCachingMiddleware`` or ``RateLimitingMiddleware``.

        Returns:
            Middleware to install, in order. Defaults to none.
        """
        return []

    def create_auth_provider(self) -> AuthProvider | None:
        """
        Create an authentication provider for HTTP transport

        Override this to protect the HTTP endpoint, for example with
        ``fastmcp.server.auth.JWTVerifier``. It is only called when the
        transport is HTTP and ``auth_enabled`` is true.

        Returns:
            A FastMCP auth provider. Returning None (the default) makes the
            HTTP server refuse to start; use ``--no-auth`` to serve without
            authentication.
        """
        return None

    def create_mcp_app(self) -> FastMCP:
        """
        Create FastMCP application for this server

        Returns:
            Configured FastMCP application with tools registered

        Raises:
            ValueError: If the transport is HTTP, auth is enabled and
                create_auth_provider() returns None
        """
        auth_provider = None

        if self.config.transport == "http":
            if self.config.auth_enabled:
                auth_provider = self.create_auth_provider()
                if auth_provider is None:
                    raise ValueError(
                        "HTTP transport has auth enabled, but create_auth_provider() "
                        "returned None. Return an AuthProvider, or pass --no-auth "
                        "(MCP_AUTH_ENABLED=false) to serve without authentication."
                    )
                logger.info("Authentication is enabled for HTTP transport")
            else:
                logger.warning(
                    "Authentication is disabled for HTTP transport (--no-auth): "
                    "anyone who can reach the port can call every tool"
                )

        # Create MCP app
        mcp = FastMCP(
            self.service.get_service_name(),
            instructions=self.instructions,
            version=self.service_version,
            auth=auth_provider,
            middleware=self.create_middleware(),
        )

        # Register service tools
        self.service.register_mcp_tools(mcp)

        logger.info(f"FastMCP application created for {self.service.get_service_name()}")
        return mcp

    def validate_configuration(self) -> None:
        """
        Validate server configuration

        The base config is already validated by pydantic; override this to
        add service-specific checks. The default does nothing.

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    def create_asgi_app(self) -> ASGIApp:
        """
        Create an ASGI application serving MCP over HTTP

        Use this to run the server under uvicorn or gunicorn instead of
        calling run(). MCP is served at FastMCP's streamable HTTP path,
        ``/mcp`` by default. Note that service.cleanup() is not called
        automatically in this mode.

        Returns:
            Starlette ASGI application from FastMCP

        Raises:
            ValueError: If the configuration is invalid, including when auth
                is enabled and create_auth_provider() returns None. Unlike
                run(), this method lets the error propagate.
        """
        self.validate_configuration()
        self.service.initialize()
        self._mcp_app = self.create_mcp_app()
        return self._mcp_app.http_app()

    def http_endpoint_url(self) -> str:
        """
        Get the URL of the MCP endpoint for HTTP transport

        Returns:
            URL built from the configured host and port and FastMCP's
            streamable HTTP path (``/mcp`` by default)
        """
        return (
            f"http://{self.config.host}:{self.config.port}"
            f"{fastmcp.settings.streamable_http_path}"
        )

    def run_stdio_transport(self) -> None:
        """
        Run MCP server with stdio transport
        """
        logger.info(f"Starting {self.service_title} with stdio transport")
        self._mcp_app.run(transport="stdio")

    def run_http_transport(self) -> None:
        """
        Run MCP server with HTTP transport
        """
        host = self.config.host
        port = self.config.port

        logger.info(f"Starting {self.service_title} with HTTP transport")
        logger.info(f"MCP endpoint: {self.http_endpoint_url()}")

        self._mcp_app.run(
            transport="http",
            host=host,
            port=port,
            log_level=logging.getLevelName(logging.getLogger().getEffectiveLevel()).lower(),
        )

    def run(self) -> None:
        """
        Run the server using the transport from the configuration
        """
        try:
            self.validate_configuration()
            self.service.initialize()
            self._mcp_app = self.create_mcp_app()

            if self.config.transport == "stdio":
                self.run_stdio_transport()
            else:
                self.run_http_transport()

        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
            sys.exit(0)
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Fatal error during startup: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.service.cleanup()


# Type-safe factory function for creating server instances
def create_server(
    server_class: Type[T],
    config: BaseServerConfig,
    service: BaseService
) -> T:
    """
    Create a server instance with the specified configuration and service

    Args:
        server_class: Class to instantiate (must extend BaseMCPServer)
        config: Server configuration
        service: Service instance to expose

    Returns:
        Configured server instance
    """
    return server_class(config, service)


def create_standard_cli_parser(
    service_name: str,
    description: Optional[str] = None
) -> argparse.ArgumentParser:
    """
    Create a standard CLI parser with mode support for MCP servers

    Args:
        service_name: Name of the service (used in help text)
        description: Description of the service (optional)

    Returns:
        Configured ArgumentParser with standard MCP server options

    Example:
        >>> parser = create_standard_cli_parser("my-service", "My MCP Service")
        >>> args = parser.parse_args()
        >>> # Use args.mode, args.host, args.port, args.no_auth, args.log_level
        >>> # (mode, host and port are None when not given on the command line)
    """
    if description is None:
        description = f"{service_name} - MCP Server"

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {service_name}                          # stdio, unless MCP_TRANSPORT says otherwise
  {service_name} --mode stdio             # Run with stdio transport
  {service_name} --mode http --port 3000  # Serve MCP over HTTP at :3000/mcp

Standard Environment Variables:
  MCP_TRANSPORT         Transport mode: stdio or http (default: stdio)
  MCP_HOST              Host to bind to for HTTP mode (default: 0.0.0.0)
  MCP_PORT              Port to bind to for HTTP mode (default: 3000)
  MCP_AUTH_ENABLED      Use the server's auth provider in HTTP mode (default: true)
        """
    )

    # Mode, host and port default to None so that MCP_TRANSPORT / MCP_HOST /
    # MCP_PORT from the environment are only overridden when given explicitly.
    parser.add_argument(
        "--mode",
        choices=list(TRANSPORTS),
        default=None,
        help="Transport: stdio or http (default: MCP_TRANSPORT, else stdio)"
    )

    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to for HTTP mode (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to for HTTP mode (default: 3000)"
    )

    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable the auth provider in HTTP mode (not recommended for production)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )

    return parser


def apply_cli_args_to_environment(args: argparse.Namespace) -> None:
    """
    Apply parsed CLI arguments to environment variables

    Sets the variables that ``BaseServerConfig()`` reads, so that
    configuration loaded afterwards reflects the command line.

    Args:
        args: Parsed arguments from create_standard_cli_parser()
    """
    if args.mode is not None:
        os.environ["MCP_TRANSPORT"] = args.mode
    if args.host is not None:
        os.environ["MCP_HOST"] = args.host
    if args.port is not None:
        os.environ["MCP_PORT"] = str(args.port)
    if args.no_auth:
        os.environ["MCP_AUTH_ENABLED"] = "false"

    os.environ["LOG_LEVEL"] = args.log_level


def create_main_with_modes(
    server_class: Type["BaseMCPServer"],
    service_factory: Callable[[Any], BaseService],
    config_factory: Callable[[], Any],
    service_name: str,
    description: Optional[str] = None,
    load_env: bool = True,
) -> Callable[[], None]:
    """
    Create a main() function with standard CLI mode support

    The returned main() parses the command line, configures logging (to
    stderr, so stdio transport stays clean), loads a .env file, builds the
    config, service and server, and runs it.

    Args:
        server_class: Class that extends BaseMCPServer
        service_factory: Function that takes the config and returns a BaseService
        config_factory: Function that returns either a BaseServerConfig or an
            object with a ``server`` attribute holding one
        service_name: Name of the service
        description: Description for help text
        load_env: Whether to load a .env file before reading configuration

    Returns:
        A main() function that can be used as the entry point

    Example:
        >>> from mcp_service_kit import create_main_with_modes
        >>> from my_service import MyServer, MyService, MyConfig
        >>>
        >>> main = create_main_with_modes(
        ...     MyServer,
        ...     lambda config: MyService(config),
        ...     MyConfig,
        ...     "my-service",
        ...     "My Custom MCP Service"
        ... )
        >>>
        >>> if __name__ == "__main__":
        ...     main()
    """
    def main() -> None:
        parser = create_standard_cli_parser(service_name, description)
        args = parser.parse_args()

        logging.basicConfig(level=args.log_level, format=LOG_FORMAT, stream=sys.stderr)

        try:
            # .env first, so that explicit CLI arguments override it
            if load_env:
                load_dotenv()
            apply_cli_args_to_environment(args)

            config = config_factory()
            service = service_factory(config)
            server_config = config if isinstance(config, BaseServerConfig) else config.server
            server = server_class(server_config, service)

        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error during startup: {e}", exc_info=True)
            sys.exit(1)

        server.run()

    return main
