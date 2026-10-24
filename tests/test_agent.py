"""Agent safety tests; model mocks still use a real MCP stdio server."""

from unittest.mock import AsyncMock

import httpx
from ollama import AsyncClient, Message
import pytest

from agent.config import Config
from agent.errors import AgentError
from agent.inputs import extract_explicit
from agent.mcp_client import open_mcp, validate_arguments, validate_result
from agent.ollama_client import OllamaModel
from agent.orchestrator import Agent


EXAMPLE = "Öncesi ve sonrası tansiyon farkı 5 mmHg, standart sapması 10 mmHg. Alpha 0.05, güç %80 ve çift yönlü test için kaç hasta gerekir?"
DIFFERENCES = {"mean_diff": 5, "sd_diff": 10, "alpha": 0.05,
               "target_power": 0.8, "tails": "two-tailed"}
CONTRACT = {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8}
RESULT = {"n_total": 34, "df": 33, "ncp": 2.915476,
          "critical_t": 2.034515, "actual_power": 0.807778}


def tool_message(name="power_analysis", arguments=None):
    return Message(role="assistant", tool_calls=[{"function": {
        "name": name, "arguments": CONTRACT if arguments is None else arguments,
    }}])


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def gateway(anyio_backend):
    async with open_mcp() as client:
        yield client


@pytest.fixture
def model():
    fake = AsyncMock()
    fake.choose.return_value = tool_message()
    return fake


def test_input_extraction():
    assert extract_explicit(EXAMPLE) == DIFFERENCES


def test_config_defaults(monkeypatch):
    for key in ["OLLAMA_MODEL", "OLLAMA_HOST", "OLLAMA_TIMEOUT", "MCP_TIMEOUT"]:
        monkeypatch.delenv(key, raising=False)
    assert Config.from_env() == Config()
    monkeypatch.setenv("OLLAMA_MODEL", "another-model")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:1234")
    assert Config.from_env().model == "another-model"
    assert Config.from_env().host == "http://localhost:1234"


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "inf", "invalid"])
def test_invalid_timeout(monkeypatch, value):
    monkeypatch.setenv("OLLAMA_TIMEOUT", value)
    with pytest.raises(AgentError):
        Config.from_env()


@pytest.mark.anyio
async def test_discovery_and_conversion(gateway):
    converted = gateway.ollama_tools()
    assert {tool["function"]["name"] for tool in converted} == {
        "power_analysis",
    }
    for tool in converted:
        assert tool["function"]["parameters"] == gateway.tools[tool["function"]["name"]].inputSchema
        assert tool["function"]["parameters"]["additionalProperties"] is False


@pytest.mark.anyio
async def test_agent_real_mcp_n34(gateway, model, caplog):
    agent = Agent(model, gateway)
    with caplog.at_level("INFO", logger="agent.orchestrator"):
        answer = await agent.ask(EXAMPLE)
    assert "34 tamamlanmış" in answer
    assert "df): 33" in answer
    assert agent.last_execution.tool == "power_analysis"
    assert agent.last_execution.arguments == CONTRACT
    assert agent.last_execution.result["n_total"] == 34
    assert agent.last_execution.request_id in caplog.text
    assert "MCP success" in caplog.text
    model.choose.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize("field", ["mean_diff", "sd_diff", "alpha", "target_power", "tails"])
async def test_missing_fields_no_model_or_tool(gateway, model, field):
    args = {key: value for key, value in DIFFERENCES.items() if key != field}
    text = ", ".join(f"{key}={value}" for key, value in args.items())
    agent = Agent(model, gateway)
    answer = await agent.ask(text)
    assert "eksik" in answer
    assert "34" not in answer
    assert agent.last_execution is None
    model.choose.assert_not_awaited()


@pytest.mark.anyio
async def test_followup(gateway, model):
    agent = Agent(model, gateway)
    first = await agent.ask(EXAMPLE.replace(" ve çift yönlü test", ""))
    assert "test yönü" in first
    assert "34" not in first
    assert "34 tamamlanmış" in await agent.ask("Çift yönlü")


@pytest.mark.anyio
async def test_missing_correlation(gateway, model):
    agent = Agent(model, gateway)
    answer = await agent.ask("mean1=140 mean2=135 sd1=10 sd2=10 alpha=0.05 güç %80 çift yönlü")
    assert "korelasyon" in answer
    model.choose.assert_not_awaited()


@pytest.mark.anyio
async def test_natural_sd_followup(gateway, model):
    agent = Agent(model, gateway)
    first = await agent.ask("mean_diff=5 alpha=0.05 güç %80 çift yönlü")
    assert "standart sapması" in first
    assert "34 tamamlanmış" in await agent.ask("Standart sapması 10")


@pytest.mark.anyio
async def test_single_numeric_followup(gateway, model):
    agent = Agent(model, gateway)
    first = await agent.ask("mean_diff=5 sd_diff=10 güç %80 çift yönlü")
    assert "alpha" in first
    assert "34 tamamlanmış" in await agent.ask("0.05")


@pytest.mark.parametrize("text", [
    "mean_diff=5 mean_diff=6", "tek yönlü veya çift yönlü", "çift yönlü değil",
    "bağımsız iki grup", "mean_diff=5 standart sapması 10 standart sapması 20",
])
def test_ambiguous_input(text):
    with pytest.raises(AgentError):
        extract_explicit(text)


@pytest.mark.anyio
@pytest.mark.parametrize("message", [
    Message(role="assistant", content="Sonuç N=999"),
    tool_message("invented_tool"),
    tool_message(arguments={**DIFFERENCES, "mean_diff": 99}),
    Message(role="assistant", tool_calls=tool_message().tool_calls * 2),
])
async def test_model_hallucinations_rejected(gateway, model, message):
    model.choose.return_value = message
    agent = Agent(model, gateway)
    with pytest.raises(AgentError):
        await agent.ask(EXAMPLE)
    assert agent.last_execution is None
    assert model.choose.await_count == 1  # No unbounded retry loop.


@pytest.mark.anyio
async def test_mcp_error_never_becomes_result(gateway, model):
    args = {**DIFFERENCES, "sd_diff": 0}
    model.choose.return_value = tool_message(arguments=args)
    agent = Agent(model, gateway)
    with pytest.raises(AgentError, match="ZeroDivisionError"):
        await agent.ask(EXAMPLE.replace("sapması 10", "sapması 0"))
    assert agent.last_execution is None


@pytest.mark.anyio
async def test_result_not_reused(gateway, model):
    agent = Agent(model, gateway)
    await agent.ask(EXAMPLE)
    assert agent.last_execution is not None
    answer = await agent.ask("mean_diff=3")
    assert "eksik" in answer
    assert agent.last_execution is None
    assert "34" not in answer


@pytest.mark.anyio
@pytest.mark.parametrize("value", [True, "5", None, float("nan"), float("inf")])
async def test_client_strict_validation(gateway, value):
    with pytest.raises(AgentError):
        validate_arguments(gateway.tools["power_analysis"], {**CONTRACT, "dz": value})


@pytest.mark.anyio
@pytest.mark.parametrize("changes", [
    {"n_total": True}, {"n_total": 34.0}, {"df": 1},
    {"ncp": float("nan")}, {"actual_power": 2}, {"unknown": 1},
])
async def test_invalid_results(gateway, changes):
    with pytest.raises(AgentError):
        validate_result(gateway.tools["power_analysis"], {**RESULT, **changes})


@pytest.mark.anyio
async def test_ollama_connection_error():
    async def fail(request):
        raise httpx.ConnectError("offline", request=request)
    async with AsyncClient(host="http://127.0.0.1:11434", transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(AgentError, match="Ollama servisine bağlanılamadı"):
            await OllamaModel(client, Config()).check_connection()


@pytest.mark.anyio
async def test_ollama_model_missing():
    async with AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"models": []}))) as client:
        with pytest.raises(AgentError, match="kurulu değil"):
            await OllamaModel(client, Config()).check_connection()


@pytest.mark.anyio
async def test_official_ollama_request_serialization(gateway):
    seen = []
    def reply(request):
        import json
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"message": tool_message().model_dump(), "done": True})
    async with AsyncClient(transport=httpx.MockTransport(reply)) as client:
        message = await OllamaModel(client, Config()).choose(
            [{"role": "user", "content": EXAMPLE}], gateway.ollama_tools(),
        )
    assert message.tool_calls[0].function.arguments == CONTRACT
    assert seen[0]["model"] == "qwen2.5:7b"
    assert seen[0]["tools"][0]["type"] == "function"
