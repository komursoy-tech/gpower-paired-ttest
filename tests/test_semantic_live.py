"""Opt-in regression flows with the actual local model and MCP server."""

import os
from unittest.mock import patch

import pytest

from agent.config import Config
from agent.mcp_client import open_mcp
from agent.ollama_client import open_ollama
from agent.orchestrator import Agent


pytestmark = [pytest.mark.anyio, pytest.mark.skipif(
    os.getenv("RUN_OLLAMA_TESTS") != "1", reason="Gerçek Ollama testi: RUN_OLLAMA_TESTS=1 gerekli",
)]


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("sd,followup,expected_tool", [
    ("her bir ölçümün standart sapması 10", "mean1=140 mean2=135 correlation=0.5", "calculate_from_groups"),
    ("standart sapma 10", "Farkların standart sapması 10", "calculate_from_differences"),
])
async def test_live_semantic_clarification_before_real_call(sd, followup, expected_tool):
    config = Config.from_env()
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp() as gateway:
            calls = []
            original = gateway.session.call_tool
            async def observe(name, arguments, *args, **kwargs):
                response = await original(name, arguments, *args, **kwargs)
                calls.append((name, arguments, response))
                return response
            with patch.object(gateway.session, "call_tool", observe):
                agent = Agent(model, gateway)
                question = await agent.ask(
                    f"Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, {sd}. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?"
                )
                assert calls == []
                assert agent.last_execution is None
                assert "MCP hesaplama sonucu" not in question
                answer = await agent.ask(followup)
                assert len(calls) == 1
                name, arguments, response = calls[0]
                assert name == "power_analysis"
                assert not response.isError
                assert response.structuredContent["n_total"] == 34
                assert "34 tamamlanmış" in answer
                if name == "calculate_from_groups":
                    assert "sd_diff" not in arguments
                    assert arguments["dz"] == 0.5
                    assert "correlation" not in arguments
