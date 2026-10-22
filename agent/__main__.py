import asyncio
import logging
import sys

from .config import Config
from .errors import AgentError
from .mcp_client import open_mcp
from .ollama_client import open_ollama
from .orchestrator import Agent


async def interactive(config):
    async with open_ollama(config) as model:
        await model.check_connection()
        async with open_mcp(config.mcp_timeout) as gateway:
            agent = Agent(model, gateway)
            print(f"G*Power ajanı hazır ({config.model}). Çıkış: çıkış / exit; yeni hesaplama: yeni.")
            while True:
                try:
                    text = input("Siz> ").strip()
                except EOFError:
                    break
                if text.casefold() in {"çıkış", "cikis", "exit", "quit"}:
                    break
                if text.casefold() in {"yeni", "reset"}:
                    agent.reset()
                    print("Yeni hesaplama başlatıldı.")
                    continue
                try:
                    print(await agent.ask(text))
                except AgentError as exc:
                    print(f"Hata: {exc}", file=sys.stderr)


def error_details(exc):
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(error_details(child) for child in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    if "--verbose" in sys.argv[1:]:
        logging.getLogger("agent").setLevel(logging.INFO)
    try:
        asyncio.run(interactive(Config.from_env()))
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Başlatma/bağlantı hatası: {error_details(exc)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
