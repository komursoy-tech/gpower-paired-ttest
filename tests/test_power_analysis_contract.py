"""K3: the single MCP tool must return K2's existing CLI JSON unchanged."""

import json
from pathlib import Path
import subprocess
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest

from mcp_server.server import mcp


ROOT = Path(__file__).resolve().parents[1]
AP = {"test": "t-paired", "mode": "a-priori", "tails": 1, "dz": 0.5, "alpha": 0.05, "power": 0.95}
PH = {"test": "t-paired", "mode": "post-hoc", "tails": 1, "dz": 0.5, "alpha": 0.05, "n_total": 45}


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client(anyio_backend, tmp_path_factory):
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server"], cwd=str(ROOT))
    with anyio.fail_after(90):
        with (tmp_path_factory.mktemp("contract") / "stderr.txt").open("w", encoding="utf-8") as log:
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session


def cli_result(arguments):
    argv = [sys.executable, str(ROOT / "cli.py")]
    for field, value in arguments.items():
        argv.extend((f"--{field}", str(value)))
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert not result.stderr
    assert len(result.stdout.strip().splitlines()) == 1
    return result.returncode, json.loads(result.stdout)


@pytest.mark.anyio
async def test_only_power_analysis_is_discovered(client):
    tools = (await client.list_tools()).tools
    assert [tool.name for tool in tools] == ["power_analysis"]
    assert set(tools[0].inputSchema["required"]) == {"test", "mode", "tails", "dz", "alpha"}
    assert tools[0].inputSchema["additionalProperties"] is False
    assert tools[0].outputSchema["type"] == "object"


@pytest.mark.anyio
@pytest.mark.parametrize("arguments", [AP, PH, {**AP, "tails": 2, "power": 0.8}, {**PH, "tails": 2, "n_total": 34}])
async def test_real_stdio_matches_cli_success(client, arguments):
    exit_code, expected = cli_result(arguments)
    response = await client.call_tool("power_analysis", arguments)
    assert exit_code == 0
    assert not response.isError
    assert response.structuredContent == expected
    assert json.loads(response.content[0].text) == expected
    assert "result" not in expected and "sample_size" not in expected and "delta" not in expected
    assert type(expected["df"]) is int
    if arguments["mode"] == "a-priori":
        assert set(expected) == {"ncp", "critical_t", "df", "n_total", "actual_power"}
        assert type(expected["n_total"]) is int
    else:
        assert set(expected) == {"ncp", "critical_t", "df", "power"}


@pytest.mark.anyio
@pytest.mark.parametrize("arguments", [
    {**AP, "alpha": 1}, {**AP, "dz": 0}, {**AP, "tails": 3},
    {**AP, "power": 0}, {**AP, "power": 0.01}, {**AP, "n_total": 45},
    {**PH, "power": 0.9}, {**PH, "n_total": 1}, {**AP, "test": "other"},
    {**AP, "mode": "other"}, {key: value for key, value in AP.items() if key != "dz"},
    {key: value for key, value in AP.items() if key != "power"},
    {key: value for key, value in AP.items() if key != "test"},
    {key: value for key, value in PH.items() if key != "n_total"},
    {**AP, "dz": 0.001},
])
async def test_real_stdio_matches_cli_errors(client, arguments):
    exit_code, expected = cli_result(arguments)
    response = await client.call_tool("power_analysis", arguments)
    assert exit_code != 0
    assert response.isError
    assert response.structuredContent == expected
    assert set(expected) == {"error", "code", "field"}


@pytest.mark.anyio
@pytest.mark.parametrize("field,bad", [
    ("dz", True), ("dz", "0.5"), ("dz", None), ("alpha", False),
    ("tails", True), ("tails", "1"), ("tails", 1.0), ("n_total", 45.0),
])
async def test_strict_json_inputs(client, field, bad):
    arguments = dict(PH if field == "n_total" else AP)
    arguments[field] = bad
    result = await client.call_tool("power_analysis", arguments)
    assert result.isError
    assert result.structuredContent["code"] == "INVALID_VALUE"
    assert result.structuredContent["field"] == field


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
async def test_nonfinite_numbers_before_json_transport(bad):
    result = await mcp.call_tool("power_analysis", {**AP, "dz": bad})
    assert result.isError
    assert result.structuredContent["code"] == "INVALID_VALUE"


@pytest.mark.anyio
async def test_unknown_parameter_and_old_tool_rejected(client):
    extra = await client.call_tool("power_analysis", {**AP, "extra": 1})
    assert extra.isError
    assert extra.structuredContent["code"] == "UNKNOWN_PARAM"
    old = await client.call_tool("calculate_sample_size", AP)
    assert old.isError


def test_eof_shutdown_protocol_stdout_only():
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "contract-check", "version": "1"},
    }}
    result = subprocess.run([sys.executable, "-m", "mcp_server"], cwd=ROOT,
                            input=json.dumps(request) + "\n", capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    messages = [json.loads(line) for line in result.stdout.splitlines()]
    assert messages and all(message["jsonrpc"] == "2.0" for message in messages)
    assert any(message.get("id") == 1 and "result" in message for message in messages)
