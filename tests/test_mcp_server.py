"""Server regression checks migrated from the retired three-tool protocol."""

from unittest.mock import Mock

import pytest

from mcp_server import server


AP = {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8}
PH = {"test": "t-paired", "mode": "post-hoc", "tails": 2, "dz": 0.5, "alpha": 0.05, "n_total": 34}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize("arguments", [AP, PH])
async def test_delegates_to_existing_cli_execute(monkeypatch, arguments):
    expected = {"ncp": 2.915476, "critical_t": 2.034515, "df": 33}
    expected.update({"n_total": 34, "actual_power": 0.807778} if arguments["mode"] == "a-priori" else {"power": 0.807778})
    execute = Mock(return_value=expected)
    monkeypatch.setattr(server.cli, "execute", execute)
    result = await server.mcp.call_tool("power_analysis", arguments)
    assert result.structuredContent == expected
    namespace = execute.call_args.args[0]
    for field, value in arguments.items():
        assert getattr(namespace, field) == str(value)


@pytest.mark.anyio
@pytest.mark.parametrize("arguments", [AP, PH])
@pytest.mark.parametrize("field,bad", [("dz", True), ("alpha", "0.05"), ("tails", False), ("dz", None)])
async def test_type_rejection_does_not_invoke_cli(monkeypatch, arguments, field, bad):
    execute = Mock()
    monkeypatch.setattr(server.cli, "execute", execute)
    result = await server.mcp.call_tool("power_analysis", {**arguments, field: bad})
    assert result.isError
    assert result.structuredContent["field"] == field
    execute.assert_not_called()
