"""One MCP tool exposing the existing CLI contract without recalculating math."""

import json
import math
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from pydantic import Field

import cli


Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Integer = Annotated[int, Field(strict=True)]
Text = Annotated[str, Field(strict=True)]
FIELDS = ("test", "mode", "tails", "dz", "alpha", "power", "n_total")
COMMON = ("test", "mode", "tails", "dz", "alpha")


def _response(value: dict[str, Any]) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        ))],
        structuredContent=value,
        isError="error" in value,
    )


def _error(message, code, field):
    return _response({"error": message, "code": code, "field": field})


def _execute(arguments):
    # Reuse K2's parser, validation, error ordering and output-key selection.
    # No printing/capturing stdout and no shell or CLI subprocess are involved.
    argv = []
    for field, value in arguments.items():
        if value is not None:
            argv.extend((f"--{field}", str(value)))
    try:
        return _response(cli.execute(cli.parser().parse_args(argv)))
    except cli.CLIError as exc:
        return _error(str(exc), exc.code, exc.field)
    except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
        message = str(exc)
        if "maximum" in message.lower() or "no solution" in message.lower():
            return _error(message, "NO_SOLUTION", "n_total")
        return _error(message, "INTERNAL", "input")


class ContractFastMCP(FastMCP):
    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            tool.inputSchema["additionalProperties"] = False
        return tools

    async def call_tool(self, name, arguments):
        if name != "power_analysis":
            raise ToolError(f"Unknown tool: {name}")
        for field, value in arguments.items():
            if field not in FIELDS:
                return _error(f"Unknown parameter: {field}", "UNKNOWN_PARAM", "input")
            if field in ("test", "mode"):
                valid = type(value) is str
            elif field in ("tails", "n_total"):
                valid = type(value) is int
            else:
                try:
                    valid = type(value) in (int, float) and math.isfinite(value)
                except OverflowError:
                    valid = False
            if not valid:
                return _error(f"{field} has an invalid JSON type or non-finite value", "INVALID_VALUE", field)
        if any(field not in arguments for field in COMMON):
            return _execute(arguments)
        return await super().call_tool(name, arguments)


mcp = ContractFastMCP("gpower-paired-ttest", log_level="INFO")


@mcp.tool()
def power_analysis(
    test: Text,
    mode: Text,
    tails: Integer,
    dz: Number,
    alpha: Number,
    power: Number = None,
    n_total: Integer = None,
) -> Annotated[CallToolResult, dict[str, Any]]:
    """Paired t-test using exactly the existing CLI JSON contract.

    test must be 't-paired'; mode is 'a-priori' or 'post-hoc'; tails is 1 or 2.
    Supply power only for a-priori, n_total only for post-hoc. No defaults for
    analysis inputs. Returns the CLI JSON object, including error/code/field
    for rejected inputs. No extra sample_size/delta fields or result envelope.
    """
    arguments = {"test": test, "mode": mode, "tails": tails, "dz": dz, "alpha": alpha}
    if power is not None:
        arguments["power"] = power
    if n_total is not None:
        arguments["n_total"] = n_total
    return _execute(arguments)
