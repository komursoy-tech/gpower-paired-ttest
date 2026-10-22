"""Independent delivery checks; does not modify application or existing tests.

Run from the repository root: python -m scripts.verify_delivery suite|demo|negative|audit
Evidence is UTF-8 and personal path prefixes are redacted before saving.
"""

import argparse
import asyncio
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from unittest.mock import patch

from ollama import Message

from agent.__main__ import error_details
from agent.config import Config
from agent.errors import AgentError
from agent import mcp_client
from agent.mcp_client import open_mcp
from agent.ollama_client import open_ollama
from agent.orchestrator import Agent


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"
QUERY = "Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, farkların standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?"
ARGS = {"mean_diff": 5, "sd_diff": 10, "alpha": 0.05, "target_power": 0.8, "tails": "two-tailed"}
PROTECTED = ["SPEC.md", "core_engine.py", "cli.py", "requirements.txt", ".gitignore",
             "MCP_OLLAMA_PLAN.md", "requirements-integration.txt", "requirements-dev.txt",
             "requirements-agent.txt", "validation_report.md"]
for folder in ["agent", "mcp_server", "tests"]:
    PROTECTED.extend(str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / folder).glob("*.py"))


def redact(text):
    for prefix, label in [(str(ROOT), "<REPO>"), (str(Path.home()), "<HOME>")]:
        for candidate in [prefix, prefix.replace("\\", "/"), prefix.replace("\\", "\\\\")]:
            text = text.replace(candidate, label)
    return re.sub(r"[A-Za-z]:\\Users\\[^\\\r\n]+", "<HOME>", text)


def save(name, value):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    content = redact(content)
    (EVIDENCE / name).write_text(content + "\n", encoding="utf-8")
    print(content, flush=True)


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(PROTECTED)}


def execute(args, *, input_text=None, env=None, timeout=900):
    completed = subprocess.run(
        args, cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})},
        input=input_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )
    return completed


def suite():
    save("protected-before.json", hashes())
    result = execute([sys.executable, "-m", "pytest", "-q", "-rA", "--tb=short"], env={
        "RUN_OLLAMA_TESTS": "1", "OLLAMA_MODEL": "qwen2.5:7b",
        "OLLAMA_HOST": "http://127.0.0.1:11434",
    })
    save("pytest-full.txt", result.stdout + result.stderr + f"\nEXIT_CODE={result.returncode}")
    check = execute([sys.executable, "-m", "pip", "check"])
    save("pip-check.txt", check.stdout + check.stderr + f"\nEXIT_CODE={check.returncode}")
    environment = {
        "python": sys.version.split()[0], "platform": sys.platform,
        "packages": {name: version(name) for name in ["mcp", "ollama", "pydantic", "numpy", "scipy", "pytest", "anyio", "jsonschema", "httpx"]},
        "model": "qwen2.5:7b", "ollama_cli": execute(["ollama", "--version"]).stdout.strip(),
    }
    save("environment.json", environment)
    return result.returncode or check.returncode


async def demo_receipt():
    config = Config(model="qwen2.5:7b")
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp() as gateway:
            wire = []
            original = gateway.session.call_tool
            async def observe(name, arguments, *args, **kwargs):
                # Observe the actual SDK call, never replace its calculation result.
                response = await original(name, arguments, *args, **kwargs)
                wire.append({"name": name, "arguments": arguments,
                             "response": response.model_dump(mode="json", exclude_none=True)})
                return response
            with patch.object(gateway.session, "call_tool", observe):
                agent = Agent(model, gateway)
                answer = await agent.ask(QUERY)
            receipt = agent.last_execution
            assert receipt is not None, answer
            assert receipt.tool == "calculate_from_differences"
            assert receipt.arguments == ARGS
            assert len(wire) == 1 and wire[0]["response"]["structuredContent"]["sample_size"] == 34
            save("demo-mcp-receipt.json", {
                "model": config.model, "query": QUERY, "execution": asdict(receipt),
                "actual_sdk_calls": wire, "answer": answer,
                "discovered_tools": sorted(gateway.tools),
            })


def demo():
    result = execute([sys.executable, "-m", "agent", "--verbose"],
                     input_text=QUERY + "\nçıkış\n", env={
                         "OLLAMA_MODEL": "qwen2.5:7b", "OLLAMA_HOST": "http://127.0.0.1:11434",
                     }, timeout=240)
    save("demo-terminal.txt", "QUERY=" + QUERY + "\nSTDOUT:\n" + result.stdout
         + "\nSTDERR:\n" + result.stderr + f"\nEXIT_CODE={result.returncode}")
    assert result.returncode == 0
    assert "34 tamamlanmış" in result.stdout
    assert "tool=calculate_from_differences" in result.stderr and "MCP success" in result.stderr
    asyncio.run(demo_receipt())
    return 0


class FixedModel:
    """Fault injection for hostile model output, clearly separate from live tests."""
    def __init__(self, name="calculate_from_differences", arguments=None):
        self.name = name
        self.arguments = ARGS if arguments is None else arguments

    async def choose(self, messages, tools):
        return Message(role="assistant", tool_calls=[{"function": {
            "name": self.name, "arguments": self.arguments,
        }}])


class ObservedGateway:
    def __init__(self, gateway):
        self.gateway = gateway
        self.tools = gateway.tools
        self.calls = []

    def ollama_tools(self):
        return self.gateway.ollama_tools()

    async def call(self, name, arguments):
        self.calls.append({"name": name, "arguments": arguments})
        return await self.gateway.call(name, arguments)


async def negatives():
    rows = []
    async with open_mcp() as real_gateway:
        async def check(name, text, model, expect_no_call=True):
            gateway = ObservedGateway(real_gateway)
            agent = Agent(model, gateway)
            try:
                message = await agent.ask(text)
            except AgentError as exc:
                message = str(exc)
            safe = agent.last_execution is None and "MCP hesaplama sonucu:" not in message
            passed = safe and (not gateway.calls if expect_no_call else True)
            rows.append({"scenario": name, "status": "PASS" if passed else "FAIL",
                         "message": message, "mcp_calls": gateway.calls,
                         "execution": asdict(agent.last_execution) if agent.last_execution else None})

        await check("missing_tails", "mean_diff=5 sd_diff=10 alpha=0.05 güç %80", FixedModel())
        await check("ambiguous_sd_alternatives", "mean_diff=5 standart sapması 10 standart sapması 20 alpha=0.05 güç %80 çift yönlü", FixedModel())
        await check("invalid_alpha", QUERY.replace("Alfa 0.05", "Alfa 1"), FixedModel(arguments={**ARGS, "alpha": 1}), False)
        await check("invented_tool", QUERY, FixedModel(name="invented_tool"))
        await check("missing_tool_argument", QUERY, FixedModel(arguments={key: value for key, value in ARGS.items() if key != "sd_diff"}))
        await check("wrong_type_tool_argument", QUERY, FixedModel(arguments={**ARGS, "sd_diff": "10"}))
        # Independent semantic probe: per-measurement SD cannot stand in for SD of differences.
        async with open_ollama(Config()) as live_model:
            await live_model.check_connection()
            await check("single_measurement_sd_must_be_clarified",
                        "Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, her bir ölçümün standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?",
                        live_model)

    # Real TCP connection refusal at an ephemeral port; do not stop the user's service.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        try:
            async with open_ollama(Config(host=f"http://127.0.0.1:{port}", ollama_timeout=3)) as model:
                await model.check_connection()
            rows.append({"scenario": "ollama_connection_refused", "status": "FAIL"})
        except AgentError as exc:
            rows.append({"scenario": "ollama_connection_refused", "status": "PASS", "message": str(exc), "execution": None})

    # Real child process exits before MCP initialize. No application file is changed.
    original = mcp_client.StdioServerParameters
    def disconnected_server(**kwargs):
        return original(**{**kwargs, "args": ["-c", "pass"]})
    try:
        with patch.object(mcp_client, "StdioServerParameters", disconnected_server):
            async with open_mcp(timeout=3):
                pass
        rows.append({"scenario": "mcp_connection_closed", "status": "FAIL"})
    except Exception as exc:
        rows.append({"scenario": "mcp_connection_closed", "status": "PASS", "message": error_details(exc), "execution": None})
    save("negative-scenarios.json", {"model_fault_injection": "FixedModel; actual MCP server remains real",
         "live_semantic_probe": "qwen2.5:7b", "scenarios": rows,
         "passed": sum(row["status"] == "PASS" for row in rows),
         "failed": sum(row["status"] == "FAIL" for row in rows)})
    return int(any(row["status"] == "FAIL" for row in rows))


def audit():
    before = json.loads((EVIDENCE / "protected-before.json").read_text(encoding="utf-8"))
    after = hashes()
    changed = [name for name in before if before[name] != after.get(name)]
    save("protected-integrity.json", {"changed": changed, "sha256": after})
    files = execute(["git", "ls-files", "--cached", "--others", "--exclude-standard"]).stdout.splitlines()
    findings = []
    patterns = {
        "personal_path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+|/(?:home|Users)/[A-Za-z0-9_.-]+/"),
        "private_key": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
        "token_like": re.compile(r"(?:sk-|ghp_)[A-Za-z0-9_-]{20,}"),
    }
    for name in files:
        path = ROOT / name
        if path.name.startswith(".env") or path.suffix.lower() in {".exe", ".pem", ".key", ".gguf"}:
            findings.append({"file": name, "kind": "local_or_binary_artifact"})
        if path.suffix.lower() in {".py", ".md", ".txt", ".json"}:
            contents = path.read_text(encoding="utf-8")
            for kind, pattern in patterns.items():
                if pattern.search(contents):
                    findings.append({"file": name, "kind": kind})
    ignored = execute(["git", "check-ignore", ".venv/Scripts/python.exe", ".pytest_cache/README.md"])
    save("repository-audit.json", {
        "candidate_file_count": len(files), "findings": findings,
        "ignored_local_artifacts": ignored.stdout.splitlines(),
        "note": "Pattern scan of candidate text files, not a full secret/history audit; images are not decoded.",
    })
    return int(bool(changed or findings))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=["suite", "demo", "negative", "audit"])
    choice = parser.parse_args().check
    action = {"suite": suite, "demo": demo, "negative": lambda: asyncio.run(negatives()), "audit": audit}[choice]
    raise SystemExit(action())
