from contextlib import asynccontextmanager

import anyio
import httpx
from ollama import AsyncClient, ResponseError

from .errors import AgentError


SYSTEM = """Sen Türkçe eşleştirilmiş t-testi ajanısın. Matematik hesaplama.
Tek araç power_analysis. Argümanları verilen doğrulanmış girdi tablosundan al.
test='t-paired', mode='a-priori' veya 'post-hoc', tails tam sayı 1 veya 2.
A-priori için power kullan; n_total gönderme. Post-hoc için n_total kullan;
power gönderme. dz ve alpha sayıdır. Tablodaki alan adlarını değiştirme.
Tablo dışında hiçbir alan gönderme. Girdiler uygulama tarafından doğrulandı.
Asla N veya güç sonucu uydurma. Bir mesajda yalnızca bir power_analysis çağır.
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
