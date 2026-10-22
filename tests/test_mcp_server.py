"""Real stdio integration plus isolated verification of engine delegation."""

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError
import pytest

from mcp_server import server


ROOT = Path(__file__).resolve().parents[1]
COMMON = {"alpha": 0.05, "target_power": 0.80, "tails": "two-tailed"}
CASES = [
    ("calculate_sample_size", {"effect_size_dz": 0.5}),
    ("calculate_from_differences", {"mean_diff": 5, "sd_diff": 10}),
    ("calculate_from_groups", {
        "mean1": 140, "mean2": 135, "sd1": 10, "sd2": 10, "correlation": 0.5,
    }),
]


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def session(anyio_backend, tmp_path_factory):
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server"], cwd=str(ROOT),
    )
    # Real child process; timeout covers startup, calls and teardown.
    with anyio.fail_after(60):
        with (tmp_path_factory.mktemp("mcp") / "stderr.log").open("w", encoding="utf-8") as log:
            async with stdio_client(parameters, errlog=log) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    yield client


@pytest.mark.anyio
async def test_discovery(session):
    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
    assert set(tools) == {name for name, _ in CASES}
    for name, inputs in CASES:
        tool = tools[name]
        assert set(tool.inputSchema["required"]) == set(inputs) | set(COMMON)
        assert tool.outputSchema is not None
        assert set(tool.outputSchema["properties"]) == {
            "sample_size", "df", "delta", "critical_t", "actual_power",
        }


@pytest.mark.anyio
@pytest.mark.parametrize("name,inputs", CASES)
async def test_real_stdio_results(session, name, inputs):
    result = await session.call_tool(name, {**inputs, **COMMON})
    assert not result.isError
    values = result.structuredContent
    assert values["sample_size"] == 34
    assert values["df"] == 33
    for field, expected in {
        "delta": 2.915476, "critical_t": 2.034515, "actual_power": 0.807778,
    }.items():
        assert values[field] == pytest.approx(expected, abs=1e-5, rel=0)
    assert json.loads(result.content[0].text) == values


@pytest.mark.anyio
@pytest.mark.parametrize("name,inputs", CASES)
@pytest.mark.parametrize("bad", [True, False, "0.5", "null", None])
async def test_strict_numeric_inputs(session, name, inputs, bad):
    arguments = {**inputs, **COMMON}
    for field in arguments.keys() - {"tails"}:
        result = await session.call_tool(name, {**arguments, field: bad})
        assert result.isError, (name, field, bad)


@pytest.mark.anyio
@pytest.mark.parametrize("arguments", [
    {"effect_size_dz": 0.5, **COMMON, "tails": "left"},
    {"effect_size_dz": 0.5, **COMMON, "alpha": 1},
    {"effect_size_dz": 0.5, **COMMON, "target_power": 0},
    {"effect_size_dz": 0.5, **COMMON, "unexpected": 1},
    {"effect_size_dz": 0.5},
])
async def test_invalid_arguments(session, arguments):
    assert (await session.call_tool("calculate_sample_size", arguments)).isError


@pytest.mark.anyio
@pytest.mark.parametrize("name,inputs,message", [
    ("calculate_sample_size", {"effect_size_dz": -0.5},
     "ValueError: Effect size must be strictly positive"),
    ("calculate_sample_size", {"effect_size_dz": 0.001},
     "RuntimeError: Sample size exceeded maximum threshold"),
    ("calculate_from_differences", {"mean_diff": 5, "sd_diff": 0},
     "ZeroDivisionError: Standard deviation of difference cannot be zero"),
    ("calculate_from_groups", {"mean1": 140, "mean2": 135, "sd1": 10,
                               "sd2": 10, "correlation": 1.5},
     "ValueError: Correlation must be between -1 and 1"),
])
async def test_engine_errors_over_stdio(session, name, inputs, message):
    result = await session.call_tool(name, {**inputs, **COMMON})
    assert result.isError
    assert message in result.content[0].text


@pytest.mark.anyio
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
async def test_nonfinite_adapter_inputs(bad):
    # Nonfinite numbers are not valid JSON; test before transport serialization.
    with pytest.raises(ToolError, match="finite"):
        await server.mcp.call_tool("calculate_sample_size", {"effect_size_dz": bad, **COMMON})


@pytest.mark.anyio
@pytest.mark.parametrize("name,inputs", CASES)
async def test_engine_delegation(monkeypatch, name, inputs):
    expected = {"sample_size": 34, "df": 33, "delta": 2.915476,
                "critical_t": 2.034515, "actual_power": 0.807778}
    power = Mock(return_value=expected)
    differences = Mock(return_value=0.5)
    groups = Mock(return_value=0.5)
    monkeypatch.setattr(server.core_engine, "power_matched_pairs", power)
    monkeypatch.setattr(server.core_engine, "calculate_dz_from_differences", differences)
    monkeypatch.setattr(server.core_engine, "calculate_dz_from_groups", groups)
    await server.mcp.call_tool(name, {**inputs, **COMMON})
    power.assert_called_once_with(0.5, 0.05, 0.8, "two-tailed")
    if name == "calculate_from_differences":
        differences.assert_called_once_with(5, 10)
        groups.assert_not_called()
    elif name == "calculate_from_groups":
        groups.assert_called_once_with(140, 135, 10, 10, 0.5)
        differences.assert_not_called()
    else:
        differences.assert_not_called()
        groups.assert_not_called()


def test_process_eof_shutdown_and_protocol_only_stdout():
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "shutdown-test", "version": "1"},
    }}
    with subprocess.Popen(
        [sys.executable, "-m", "mcp_server"], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    ) as process:
        try:
            stdout, stderr = process.communicate(json.dumps(request) + "\n", timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            pytest.fail("MCP server did not shut down after stdin EOF")
    assert process.returncode == 0, stderr
    messages = [json.loads(line) for line in stdout.splitlines()]
    assert messages
    assert all(message["jsonrpc"] == "2.0" for message in messages)
    assert any(message.get("id") == 1 and "result" in message for message in messages)
