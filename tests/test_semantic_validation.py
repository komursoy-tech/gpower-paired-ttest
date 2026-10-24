"""Regression checks for the distinction between measurement SD and difference SD."""

from unittest.mock import AsyncMock, patch

from ollama import Message
import pytest

from agent.errors import AgentError
from agent.inputs import extract_explicit
from agent.mcp_client import open_mcp
from agent.orchestrator import Agent
from agent.contract import prepare_arguments


BASE = "Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, {sd}. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?"
COMMON = {"alpha": 0.05, "target_power": 0.8, "tails": "two-tailed"}
DIFF = {"mean_diff": 5, "sd_diff": 10, **COMMON}
GROUP = {"mean1": 140, "mean2": 135, "sd1": 10, "sd2": 10, "correlation": 0.5, **COMMON}


def model_for(tool="calculate_from_differences", arguments=None):
    model = AsyncMock()
    model.choose.return_value = Message(role="assistant", tool_calls=[{"function": {
        "name": "power_analysis", "arguments": prepare_arguments(tool, DIFF if arguments is None else arguments),
    }}])
    return model


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def gateway(anyio_backend):
    async with open_mcp() as client:
        yield client


@pytest.mark.parametrize("phrase", [
    "farkların standart sapması 10", "farkın standart sapması 10", "sd_diff=10",
])
def test_explicit_difference_sd(phrase):
    assert extract_explicit(BASE.format(sd=phrase))["sd_diff"] == 10


@pytest.mark.parametrize("phrase", [
    "her bir ölçümün standart sapması 10", "her ölçümün standart sapması 10",
    "her iki ölçümün standart sapması 10", "ölçümlerin standart sapması 10",
    "standart sapma 10", "birinci ölçümün standart sapması 10",
])
def test_non_difference_sd_never_becomes_sd_diff(phrase):
    assert "sd_diff" not in extract_explicit(BASE.format(sd=phrase))


def test_shared_measurement_sd_has_no_invented_parameters():
    values = extract_explicit(BASE.format(sd="her bir ölçümün standart sapması 10"))
    assert values["sd1"] == values["sd2"] == 10
    assert not {"mean1", "mean2", "correlation", "sd_diff"} & values.keys()


@pytest.mark.anyio
@pytest.mark.parametrize("phrase", [
    "her bir ölçümün standart sapması 10", "ölçümlerin standart sapması 10", "standart sapma 10",
])
async def test_unclear_or_incomplete_data_cannot_reach_mcp(gateway, phrase):
    model = model_for()  # Even an eager/hallucinating model must never be consulted.
    agent = Agent(model, gateway)
    with patch.object(gateway.session, "call_tool", AsyncMock(wraps=gateway.session.call_tool)) as call:
        answer = await agent.ask(BASE.format(sd=phrase))
        assert "MCP hesaplama sonucu" not in answer
        assert agent.last_execution is None
        call.assert_not_awaited()
        model.choose.assert_not_awaited()


@pytest.mark.anyio
async def test_measurement_sd_asks_for_means_and_correlation(gateway):
    agent = Agent(model_for(), gateway)
    answer = await agent.ask(BASE.format(sd="her bir ölçümün standart sapması 10"))
    assert all(label in answer for label in ("mean1", "mean2", "correlation"))
    assert "sd_diff" not in agent.values


@pytest.mark.anyio
async def test_missing_correlation_never_calls_tool(gateway):
    agent = Agent(model_for("calculate_from_groups", GROUP), gateway)
    with patch.object(gateway.session, "call_tool", AsyncMock(wraps=gateway.session.call_tool)) as call:
        answer = await agent.ask("mean1=140 mean2=135 sd1=10 sd2=10 alpha=0.05 güç %80 çift yönlü")
        assert "correlation" in answer
        call.assert_not_awaited()


@pytest.mark.anyio
async def test_group_followup_only_calls_after_all_data(gateway):
    agent = Agent(model_for("calculate_from_groups", GROUP), gateway)
    with patch.object(gateway.session, "call_tool", AsyncMock(wraps=gateway.session.call_tool)) as call:
        await agent.ask(BASE.format(sd="her bir ölçümün standart sapması 10"))
        call.assert_not_awaited()
        answer = await agent.ask("correlation=0.5")
        assert "mean1" in answer and "mean2" in answer
        call.assert_not_awaited()
        answer = await agent.ask("mean1=140 mean2=135")
        call.assert_awaited_once_with("power_analysis", prepare_arguments("calculate_from_groups", GROUP))
        assert agent.last_execution.result["n_total"] == 34
        assert "34 tamamlanmış" in answer


@pytest.mark.anyio
async def test_correlation_followup(gateway):
    agent = Agent(model_for("calculate_from_groups", GROUP), gateway)
    await agent.ask("mean1=140 mean2=135 sd1=10 sd2=10 alpha=0.05 güç %80 çift yönlü")
    assert "34 tamamlanmış" in await agent.ask("0.5")


@pytest.mark.anyio
@pytest.mark.parametrize("initial_sd", ["standart sapma 10", "her bir ölçümün standart sapması 10"])
async def test_explicit_difference_followup_can_select_difference_method(gateway, initial_sd):
    agent = Agent(model_for(), gateway)
    with patch.object(gateway.session, "call_tool", AsyncMock(wraps=gateway.session.call_tool)) as call:
        await agent.ask(BASE.format(sd=initial_sd))
        call.assert_not_awaited()
        answer = await agent.ask("Farkların standart sapması 10")
        call.assert_awaited_once_with("power_analysis", prepare_arguments("calculate_from_differences", DIFF))
        assert "34 tamamlanmış" in answer


@pytest.mark.anyio
async def test_bare_number_does_not_answer_a_type_question(gateway):
    model = model_for()
    agent = Agent(model, gateway)
    await agent.ask(BASE.format(sd="standart sapma 10"))
    answer = await agent.ask("10")
    assert agent.last_execution is None
    model.choose.assert_not_awaited()
    assert "34 tamamlanmış" not in answer


@pytest.mark.anyio
async def test_ambiguous_followup_invalidates_cached_sd(gateway):
    model = model_for()
    model.choose.return_value = Message(role="assistant", content="No tool")
    agent = Agent(model, gateway)
    with pytest.raises(AgentError):
        await agent.ask(BASE.format(sd="farkların standart sapması 10"))
    assert "sd_diff" in agent.values
    with patch.object(gateway.session, "call_tool", AsyncMock(wraps=gateway.session.call_tool)) as call:
        await agent.ask("Ölçümlerin standart sapması 20")
        assert "sd_diff" not in agent.values
        call.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("sd", [0, -10])
async def test_invalid_explicit_sd_is_rejected_by_real_engine(gateway, sd):
    agent = Agent(model_for(), gateway)
    with pytest.raises(AgentError, match="Girdi hatası"):
        await agent.ask(BASE.format(sd=f"farkların standart sapması {sd}"))
    assert agent.last_execution is None


@pytest.mark.anyio
async def test_explicit_difference_sd_real_mcp_n34(gateway):
    agent = Agent(model_for(), gateway)
    assert "34 tamamlanmış" in await agent.ask(BASE.format(sd="farkların standart sapması 10"))
    assert agent.last_execution.result["n_total"] == 34
