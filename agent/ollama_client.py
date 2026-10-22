from contextlib import asynccontextmanager

import anyio
import httpx
from ollama import AsyncClient, ResponseError

from .errors import AgentError


SYSTEM = """Sen Türkçe eşleştirilmiş t-testi araç seçicisisin. Matematik hesaplama.
Yalnızca verilen MCP araçlarından birini çağır. Kullanıcı verilerini verilen
doğrulanmış girdi tablosuyla eşleştir. Asla eksik alan, korelasyon, alpha, güç
veya test yönü varsayma. mean_diff farkların ortalaması; sd_diff farkların SD'si.
Grup aracı aynı kişilerin iki ölçümü içindir. Bağımsız grupları hesaplama.
%80 güç 0.80'dir. Sayıları JSON number, tails değerini one-tailed/two-tailed ver.
Araç sonucu veya N uydurma. Bir mesajda en fazla bir araç çağır.
"""


class OllamaModel:
    def __init__(self, client, config):
        self.client = client
        self.config = config

    async def _request(self, operation):
        try:
            with anyio.fail_after(self.config.ollama_timeout):
                return await operation()
        except (ConnectionError, httpx.ConnectError) as exc:
            raise AgentError(f"Ollama servisine bağlanılamadı ({self.config.host}). Ollama'yı başlatın.") from exc
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise AgentError("Ollama yanıt süresi aşıldı; model ve OLLAMA_TIMEOUT ayarını kontrol edin.") from exc
        except ResponseError as exc:
            raise AgentError(f"Ollama model/API hatası: {exc}") from exc
        except httpx.HTTPError as exc:
            raise AgentError(f"Ollama iletişim hatası: {exc}") from exc

    async def check_connection(self):
        listing = await self._request(self.client.list)
        names = {entry.model for entry in listing.models}
        model = self.config.model
        if model not in names and f"{model}:latest" not in names:
            raise AgentError(f"Ollama modeli kurulu değil: {model}. Önce ollama pull ile indirin.")

    async def choose(self, messages, tools):
        response = await self._request(lambda: self.client.chat(
            model=self.config.model,
            messages=[{"role": "system", "content": SYSTEM}, *messages],
            tools=tools, stream=False, options={"temperature": 0, "num_predict": 512},
        ))
        return response.message


@asynccontextmanager
async def open_ollama(config):
    async with AsyncClient(host=config.host, timeout=config.ollama_timeout, trust_env=False) as client:
        yield OllamaModel(client, config)
