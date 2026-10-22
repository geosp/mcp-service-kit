import os

import pytest

from mcp_service_kit import apply_cli_args_to_environment, create_standard_cli_parser


def apply(*argv):
    args = create_standard_cli_parser("test").parse_args(list(argv))
    apply_cli_args_to_environment(args)


def test_default_is_stdio():
    apply()
    assert os.environ["MCP_TRANSPORT"] == "stdio"
    assert os.environ["LOG_LEVEL"] == "INFO"
    assert "MCP_HOST" not in os.environ
    assert "MCP_PORT" not in os.environ
    assert "MCP_AUTH_ENABLED" not in os.environ


def test_http_mode_sets_host_port_and_auth():
    apply("--mode", "http", "--host", "127.0.0.1", "--port", "4000", "--no-auth",
          "--log-level", "DEBUG")
    assert os.environ["MCP_TRANSPORT"] == "http"
    assert os.environ["MCP_HOST"] == "127.0.0.1"
    assert os.environ["MCP_PORT"] == "4000"
    assert os.environ["MCP_AUTH_ENABLED"] == "false"
    assert os.environ["LOG_LEVEL"] == "DEBUG"


def test_unset_host_keeps_environment(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "10.0.0.1")
    apply("--mode", "http")
    assert os.environ["MCP_HOST"] == "10.0.0.1"


def test_no_mcp_only_variable():
    apply("--mode", "http")
    assert "MCP_ONLY" not in os.environ


@pytest.mark.parametrize("mode", ["rest", "mcp"])
def test_removed_modes_are_rejected(mode):
    with pytest.raises(SystemExit):
        create_standard_cli_parser("test").parse_args(["--mode", mode])
