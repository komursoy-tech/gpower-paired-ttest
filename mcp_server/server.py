"""Thin FastMCP adapters; all statistical calculations belong to core_engine."""

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

import core_engine


# Strict float accepts JSON integers too, but never bool or numeric strings.
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Tails = Literal["one-tailed", "two-tailed"]


class PowerResult(BaseModel):
    """N counts completed matched pairs, not individual measurements."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    sample_size: Annotated[int, Field(ge=2)]
    df: Annotated[int, Field(ge=1)]
    delta: float
    critical_t: float
    actual_power: float


class StrictFastMCP(FastMCP):
    """Reject extra arguments, which FastMCP's default arg model ignores."""

    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            tool.inputSchema["additionalProperties"] = False
        return tools

    async def call_tool(self, name, arguments):
        for tool in await self.list_tools():
            if tool.name == name:
                extra = arguments.keys() - tool.inputSchema["properties"].keys()
                if extra:
                    raise ToolError(f"Unexpected parameters: {', '.join(sorted(extra))}")
                break
        return await super().call_tool(name, arguments)


mcp = StrictFastMCP("gpower-paired-ttest", log_level="INFO")


def _result(dz, alpha, target_power, tails):
    return PowerResult.model_validate(
        core_engine.power_matched_pairs(dz, alpha, target_power, tails)
    )


def _engine_error(exc):
    return ToolError(f"{type(exc).__name__}: {exc}")


ENGINE_ERRORS = (ValueError, TypeError, ZeroDivisionError, RuntimeError, OverflowError)


@mcp.tool()
def calculate_sample_size(
    effect_size_dz: Number, alpha: Number, target_power: Number, tails: Tails
) -> PowerResult:
    """Calculate a-priori matched-pairs sample size from positive dz.

    alpha and target_power must be strictly between 0 and 1. All inputs required.
    """
    try:
        return _result(effect_size_dz, alpha, target_power, tails)
    except ENGINE_ERRORS as exc:
        raise _engine_error(exc) from exc


@mcp.tool()
def calculate_from_differences(
    mean_diff: Number, sd_diff: Number, alpha: Number,
    target_power: Number, tails: Tails,
) -> PowerResult:
    """Calculate sample size from the mean and SD of paired differences.

    mean_diff must be nonzero; sd_diff positive. All inputs required.
    """
    try:
        dz = core_engine.calculate_dz_from_differences(mean_diff, sd_diff)
        return _result(dz, alpha, target_power, tails)
    except ENGINE_ERRORS as exc:
        raise _engine_error(exc) from exc


@mcp.tool()
def calculate_from_groups(
    mean1: Number, mean2: Number, sd1: Number, sd2: Number,
    correlation: Number, alpha: Number, target_power: Number, tails: Tails,
) -> PowerResult:
    """Calculate matched-pairs sample size from two measurements of the same people.

    Not an independent-groups test. SDs must be positive, correlation in [-1,1],
    and means different. All inputs required; no correlation is assumed.
    """
    try:
        dz = core_engine.calculate_dz_from_groups(mean1, mean2, sd1, sd2, correlation)
        return _result(dz, alpha, target_power, tails)
    except ENGINE_ERRORS as exc:
        raise _engine_error(exc) from exc
