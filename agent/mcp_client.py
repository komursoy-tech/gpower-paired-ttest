from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import timedelta
import math
from pathlib import Path
import sys

import anyio
from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .errors import AgentError


ALLOWED_TOOLS = frozenset({
    "calculate_sample_size", "calculate_from_differences", "calculate_from_groups",
})
RESULT_FIELDS = {"sample_size", "df", "delta", "critical_t", "actual_power"}
ROOT = Path(__file__).resolve().parents[1]


def validate_arguments(tool, arguments):
    if not isinstance(arguments, dict):
        raise AgentError("Araç argümanları bir nesne olmalı.")
    errors = list(Draft202012Validator(tool.inputSchema).iter_errors(arguments))
    if errors:
        raise AgentError(f"Geçersiz araç parametreleri: {errors[0].message}")
    for key, value in arguments.items():
        if key != "tails" and (
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise AgentError(f"{key}: sonlu bir sayı olmalı; metin/bool kabul edilmez.")


def validate_result(tool, result):
    if not isinstance(result, dict) or set(result) != RESULT_FIELDS:
        raise AgentError("MCP sonucu beklenen beş alanı içermiyor.")
    errors = list(Draft202012Validator(tool.outputSchema).iter_errors(result))
    if errors:
        raise AgentError(f"MCP çıktı şeması hatası: {errors[0].message}")
    for field, value in result.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise AgentError(f"MCP sonucu geçersiz: {field} sonlu sayı değil.")
    if type(result["sample_size"]) is not int or type(result["df"]) is not int:
        raise AgentError("MCP sonucu: N ve df tam sayı olmalı.")
    if result["df"] != result["sample_size"] - 1 or not 0 <= result["actual_power"] <= 1:
        raise AgentError("MCP sonucu tutarsız.")
    return deepcopy(result)


class MCPGateway:
    def __init__(self, session, tools, timeout):
        self.session = session
        self.tools = tools
        self.timeout = timeout

    @classmethod
    async def discover(cls, session, timeout=30):
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        if set(tools) != ALLOWED_TOOLS:
            raise AgentError("MCP discovery: beklenen üç araç bulunamadı veya ek araç var.")
        for tool in tools.values():
            if tool.outputSchema is None:
                raise AgentError("MCP aracı yapılandırılmış çıktı şeması sunmuyor.")
            Draft202012Validator.check_schema(tool.inputSchema)
            Draft202012Validator.check_schema(tool.outputSchema)
        return cls(session, tools, timeout)

    def ollama_tools(self):
        return [{"type": "function", "function": {
            "name": tool.name, "description": tool.description or "",
            "parameters": deepcopy(tool.inputSchema),
        }} for tool in self.tools.values()]

    async def call(self, name, arguments):
        if name not in ALLOWED_TOOLS or name not in self.tools:
            raise AgentError(f"İzin verilmeyen araç adı: {name}")
        tool = self.tools[name]
        validate_arguments(tool, arguments)
        try:
            with anyio.fail_after(self.timeout):
                response = await self.session.call_tool(name, arguments)
        except TimeoutError as exc:
            raise AgentError("MCP çağrısının süresi aşıldı. Hesaplama sonucu alınamadı.") from exc
        except Exception as exc:
            raise AgentError(f"MCP çağrısı başarısız: {exc}") from exc
        if response.isError:
            detail = " ".join(block.text for block in response.content if block.type == "text")
            raise AgentError(f"MCP araç hatası: {detail}")
        return validate_result(tool, response.structuredContent)


@asynccontextmanager
async def open_mcp(timeout=30):
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server"], cwd=str(ROOT),
    )
    async with stdio_client(parameters, errlog=sys.stderr) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout)) as session:
            with anyio.fail_after(timeout):
                await session.initialize()
                gateway = await MCPGateway.discover(session, timeout)
            yield gateway
