from copy import deepcopy
from dataclasses import dataclass
import json
import logging
import re
from uuid import uuid4

from .errors import AgentError
from .inputs import ambiguous_sd, clarification, extract_explicit, input_mode, required_fields, NUMBER, GROUP_FIELDS
from .contract import prepare_arguments
from .mcp_client import validate_arguments
from .presentation import present


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Execution:
    request_id: str
    tool: str
    arguments: dict
    result: dict


class Agent:
    def __init__(self, model, gateway):
        self.model = model
        self.gateway = gateway
        self.reset()

    def reset(self):
        self.values = {}
        self.messages = []
        self.last_execution = None

    async def ask(self, text):
        self.last_execution = None
        if not text.strip():
            return "Lütfen hesaplama sorunuzu yazın."
        if len(text) > 6000 or len(self.messages) >= 20:
            raise AgentError("Oturum girdi sınırına ulaşıldı. 'yeni' ile yeni hesaplama başlatın.")
        mode = input_mode(self.values)
        missing = [key for key in required_fields(mode, self.values) if key not in self.values]
        requested_sd_diff = (
            mode == "calculate_from_differences" and "sd_diff" in missing
            and bool(self.messages) and self.messages[-1]["role"] == "assistant"
            and self.messages[-1]["content"].startswith("Hesaplama için eksik")
            and "farkların standart sapması (sd_diff)" in self.messages[-1]["content"]
        )
        parsed_text = text
        if (len(missing) == 1 and missing[0] != "tails"
                and (missing[0] != "sd_diff" or requested_sd_diff)
                and re.fullmatch(rf"\s*%?\s*{NUMBER}\s*%?\s*", text)):
            parsed_text = f"{missing[0]}={text}"
        updates = extract_explicit(parsed_text, self.values, requested_sd_diff=requested_sd_diff)
        candidate = {**self.values, **updates}
        # An explicitly clarified input method supersedes the other method's SD.
        if "sd_diff" in updates and not (GROUP_FIELDS & updates.keys()):
            candidate = {key: value for key, value in candidate.items() if key not in GROUP_FIELDS}
        elif {"sd1", "sd2"} & updates.keys() and "sd_diff" not in updates:
            candidate.pop("sd_diff", None)
        sd_unclear = ambiguous_sd(parsed_text, updates)
        if sd_unclear:
            for key in ("sd_diff", "sd1", "sd2"):
                candidate.pop(key, None)
        mode = input_mode(candidate)
        # Commit only an unambiguous user turn; an error does not poison state.
        self.values = candidate
        self.messages.append({"role": "user", "content": text})
        if sd_unclear:
            question = "Standart sapmanın türünü netleştirin: farkların standart sapması mı, ayrı ölçümlerin standart sapmaları mı? Farklar için sd_diff; ölçümler için sd1, sd2, mean1, mean2 ve correlation belirtin."
            self.messages.append({"role": "assistant", "content": question})
            return question
        question = clarification(mode, candidate)
        if question:
            self.messages.append({"role": "assistant", "content": question})
            return question
        arguments = prepare_arguments(mode, candidate)
        validate_arguments(self.gateway.tools["power_analysis"], arguments)
        message = await self.model.choose(
            # Conversation state is for grounding/clarification, not tool fields.
            # Raw clinical names in earlier turns must not contaminate this API.
            [{"role": "user", "content":
                "Eşleştirilmiş t-testi hesabını yalnızca bu doğrulanmış CLI argümanlarıyla yap: "
                + json.dumps(arguments, ensure_ascii=False, allow_nan=False)}],
            self.gateway.ollama_tools(),
        )
        calls = message.tool_calls or []
        # No automatic tool loop and no display of model-authored results.
        if len(calls) != 1:
            raise AgentError("Model tam bir araç çağrısı üretmedi veya birden fazla çağrı önerdi. Hesaplama yapılmadı; modeli ve sorguyu kontrol edin.")
        call = calls[0].function
        if call.name not in self.gateway.tools:
            raise AgentError(f"Model izin verilmeyen araç önerdi: {call.name}")
        validate_arguments(self.gateway.tools[call.name], call.arguments)
        if call.name != "power_analysis" or call.arguments != arguments:
            raise AgentError("Modelin araç seçimi/parametreleri açık kullanıcı girdileriyle uyuşmuyor. Hesaplama yapılmadı; alan adlarıyla netleştirin.")
        request_id = str(uuid4())
        logger.info("MCP request id=%s tool=%s arguments=%s", request_id, call.name, arguments)
        result = await self.gateway.call(call.name, call.arguments)
        logger.info("MCP success id=%s result=%s", request_id, result)
        execution = Execution(request_id, call.name, deepcopy(arguments), deepcopy(result))
        answer = present(result, arguments)
        # Do not leak an earlier calculation into the next unrelated question.
        self.reset()
        self.last_execution = execution
        return answer
