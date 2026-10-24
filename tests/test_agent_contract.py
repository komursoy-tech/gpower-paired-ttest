"""Single-tool a-priori/post-hoc agent regressions using real MCP stdio."""

from unittest.mock import AsyncMock, patch

from ollama import Message
import pytest

from agent.errors import AgentError
from agent.inputs import extract_explicit
from agent.mcp_client import open_mcp, validate_result
from agent.orchestrator import Agent


AP = {"test": "t-paired", "mode": "a-priori", "tails": 2, "dz": 0.5, "alpha": 0.05, "power": 0.8}
PH = {"test": "t-paired", "mode": "post-hoc", "tails": 2, "dz": 0.5, "alpha": 0.05, "n_total": 34}


def model(arguments):
    fake = AsyncMock()
    fake.choose.return_value = Message(role="assistant", tool_calls=[{"function": {
        "name": "power_analysis", "arguments": arguments,
    }}])
    return fake


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def gateway(anyio_backend):
    async with open_mcp() as client:
        yield client


@pytest.mark.anyio
async def test_post_hoc_real_mcp(gateway):
    agent = Agent(model(PH), gateway)
    with patch.object(gateway.session, "call_tool", AsyncMock(wraps=gateway.session.call_tool)) as call:
        answer = await agent.ask("Post-hoc dz=0.5 alpha=0.05 n_total=34 çift yönlü güç nedir?")
        call.assert_awaited_once_with("power_analysis", PH)
    assert "post-hoc" in answer and "%80.7778" in answer
    assert set(agent.last_execution.result) == {"ncp", "critical_t", "df", "power"}


@pytest.mark.anyio
async def test_missing_n_total_then_followup(gateway):
    fake = model(PH)
    agent = Agent(fake, gateway)
    question = await agent.ask("Post-hoc dz=0.5 alpha=0.05 çift yönlü")
    assert "n_total" in question
    fake.choose.assert_not_awaited()
    assert "post-hoc" in await agent.ask("34")


@pytest.mark.anyio
async def test_a_priori_wire_schema(gateway):
    agent = Agent(model(AP), gateway)
    answer = await agent.ask("dz=0.5 alpha=0.05 power=0.8 tails=2 a-priori")
    assert "34 tamamlanmış" in answer
    assert agent.last_execution.arguments == AP


@pytest.mark.anyio
async def test_tool_selection_does_not_receive_raw_clinical_field_names(gateway):
    fake = model(AP)
    agent = Agent(fake, gateway)
    await agent.ask("mean_diff=5 sd_diff=10 alpha=0.05 güç %80 çift yönlü")
    messages = fake.choose.call_args.args[0]
    assert len(messages) == 1
    assert "mean_diff" not in messages[0]["content"]
    assert "sd_diff" not in messages[0]["content"]
    assert '"dz": 0.5' in messages[0]["content"]


@pytest.mark.anyio
async def test_mode_specific_result_consistency(gateway):
    result = await gateway.call("power_analysis", PH)
    with pytest.raises(AgentError, match="tutarsız"):
        validate_result(gateway.tools["power_analysis"], result, {**PH, "n_total": 35})


@pytest.mark.anyio
async def test_cli_error_not_presented_as_result(gateway):
    agent = Agent(model({**AP, "alpha": 1}), gateway)
    with pytest.raises(AgentError, match="OUT_OF_RANGE / alpha"):
        await agent.ask("dz=0.5 alpha=1 power=0.8 çift yönlü")
    assert agent.last_execution is None


@pytest.mark.anyio
async def test_post_hoc_target_power_not_invented(gateway):
    fake = model(PH)
    agent = Agent(fake, gateway)
    with pytest.raises(AgentError):
        await agent.ask("post-hoc dz=0.5 alpha=0.05 güç %80 n_total=34 çift yönlü")
    fake.choose.assert_not_awaited()


@pytest.mark.parametrize("text", ["mode=criterion", "tails=1.5", "n_total=34.5", "tails=3"])
def test_invalid_contract_input(text):
    with pytest.raises(AgentError):
        extract_explicit(text)
