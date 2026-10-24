"""Opt-in tests: actual Ollama model and actual MCP stdio process.

RUN_OLLAMA_TESTS=1 makes service/model failures fail, never silently skip.
"""

import os
from pathlib import Path
import subprocess
import sys

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


@pytest.mark.parametrize("question,tool,expected", [
    ("Öncesi ve sonrası tansiyon farkı 5 mmHg, standart sapması 10 mmHg. Alpha 0.05, güç %80 ve çift yönlü test için kaç hasta gerekir?",
     "calculate_from_differences", {"mean_diff": 5, "sd_diff": 10}),
    ("Etki büyüklüğü dz=0.5, alpha=0.05, güç %80, çift yönlü eşleştirilmiş test için kaç katılımcı gerekir?",
     "calculate_sample_size", {"effect_size_dz": 0.5}),
    ("Aynı kişilerin öncesi ortalama 140, sonrası ortalama 135, öncesi standart sapma 10, sonrası standart sapma 10. Korelasyon 0.5, alpha 0.05, güç %80, çift yönlü test için kaç kişi gerekir?",
     "calculate_from_groups", {"mean1": 140, "mean2": 135, "sd1": 10, "sd2": 10, "correlation": 0.5}),
], ids=["differences", "effect-size", "groups"])
async def test_real_ollama_to_mcp(question, tool, expected):
    config = Config.from_env()
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp(config.mcp_timeout) as gateway:
            agent = Agent(model, gateway)
            answer = await agent.ask(question)
            execution = agent.last_execution
            assert execution is not None, answer
            assert execution.tool == "power_analysis"
            assert execution.arguments == {"test": "t-paired", "mode": "a-priori", "dz": 0.5, "alpha": 0.05, "power": 0.8, "tails": 2}
            assert execution.result["n_total"] == 34
            assert "34 tamamlanmış" in answer


async def test_live_missing_parameter_followup():
    config = Config.from_env()
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp(config.mcp_timeout) as gateway:
            agent = Agent(model, gateway)
            question = await agent.ask("mean_diff=5 sd_diff=10 alpha=0.05 güç %80")
            assert "test yönü" in question
            assert agent.last_execution is None
            answer = await agent.ask("çift yönlü")
            assert "34 tamamlanmış" in answer


async def test_live_post_hoc_single_tool():
    config = Config.from_env()
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp(config.mcp_timeout) as gateway:
            agent = Agent(model, gateway)
            answer = await agent.ask("Post-hoc analiz: dz=0.5, alpha=0.05, n_total=45, tek yönlü. Ulaşılan güç nedir?")
            assert agent.last_execution.tool == "power_analysis"
            assert agent.last_execution.arguments == {"test": "t-paired", "mode": "post-hoc", "dz": 0.5, "alpha": 0.05, "n_total": 45, "tails": 1}
            assert agent.last_execution.result["power"] == pytest.approx(0.951240, abs=1e-5, rel=0)
            assert "post-hoc" in answer and "hedef güç" not in answer


async def test_live_post_hoc_n_followup():
    config = Config.from_env()
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp(config.mcp_timeout) as gateway:
            agent = Agent(model, gateway)
            question = await agent.ask("Post-hoc dz=0.5 alpha=0.05 çift yönlü güç nedir?")
            assert "n_total" in question and agent.last_execution is None
            answer = await agent.ask("34")
            assert agent.last_execution.arguments["n_total"] == 34
            assert agent.last_execution.result["power"] == pytest.approx(0.807778, abs=1e-5, rel=0)
            assert "post-hoc" in answer


def test_live_terminal_question_and_exit():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    root = Path(__file__).resolve().parents[1]
    question = "Öncesi ve sonrası tansiyon farkı 5 mmHg, standart sapması 10 mmHg. Alpha 0.05, güç %80 ve çift yönlü test için kaç hasta gerekir?"
    with subprocess.Popen(
        [sys.executable, "-m", "agent"], cwd=root, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    ) as process:
        try:
            stdout, stderr = process.communicate(question + "\nçıkış\n", timeout=240)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            pytest.fail("Etkileşimli ajan kapanmadı")
    assert process.returncode == 0, stderr
    assert "34 tamamlanmış" in stdout
    assert "Hata:" not in stderr
