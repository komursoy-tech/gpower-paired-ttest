from dataclasses import dataclass
import math
import os
from urllib.parse import urlparse

from .errors import AgentError


@dataclass(frozen=True)
class Config:
    model: str = "qwen2.5:7b"
    host: str = "http://127.0.0.1:11434"
    ollama_timeout: float = 180
    mcp_timeout: float = 30

    @classmethod
    def from_env(cls):
        try:
            config = cls(
                model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip(),
                host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip(),
                ollama_timeout=float(os.getenv("OLLAMA_TIMEOUT", "180")),
                mcp_timeout=float(os.getenv("MCP_TIMEOUT", "30")),
            )
        except ValueError as exc:
            raise AgentError("Zaman aşımı ayarları pozitif sayılar olmalı.") from exc
        if not config.model or not urlparse(config.host).hostname or urlparse(config.host).scheme not in {"http", "https"}:
            raise AgentError("OLLAMA_MODEL boş olmamalı; OLLAMA_HOST tam bir HTTP adresi olmalı.")
        if any(not math.isfinite(v) or v <= 0 for v in (config.ollama_timeout, config.mcp_timeout)):
            raise AgentError("Zaman aşımı ayarları sonlu ve pozitif olmalı.")
        return config
