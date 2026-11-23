"""Inference engines. `openai` talks to a vLLM (or any OpenAI-compatible) server that runs the model on OUR hardware; `fake` is deterministic and only for tests / development.
The service never calls an external AI provider: the URL must be an internal address."""
import base64
import json
import re
from typing import Protocol

import httpx

from .prompts import SYSTEM, user_prompt
from .schema import ModelAnswer


class ModelUnavailable(Exception):
    pass


class ModelError(Exception):
    """The model answered, but not with usable JSON."""


class Engine(Protocol):
    name: str
    model: str

    async def analyze(self, jpeg: bytes, doc_type: str, instructions: str | None) -> ModelAnswer: ...

    async def ready(self) -> bool: ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_answer(text: str) -> ModelAnswer:
    t = _FENCE.sub("", text.strip())
    try:
        start, end = t.index("{"), t.rindex("}")
        data = json.loads(t[start:end + 1])
        return ModelAnswer.model_validate(data)
    except Exception as e:
        raise ModelError("model output is not valid") from e


class OpenAICompatEngine:
    name = "openai-compatible"

    def __init__(self, url: str, model: str, timeout: float):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout

    async def ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{self.url}/v1/models")
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    async def analyze(self, jpeg: bytes, doc_type: str, instructions: str | None) -> ModelAnswer:
        body = {
            "model": self.model, "temperature": 0, "max_tokens": 1600,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}},
                    {"type": "text", "text": user_prompt(doc_type, instructions)}]},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.post(f"{self.url}/v1/chat/completions", json=body)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise ModelUnavailable("model server unreachable or too slow") from e
        if r.status_code >= 500 or r.status_code == 429:
            raise ModelUnavailable(f"model server answered {r.status_code}")
        if r.status_code != 200:
            raise ModelError(f"model server answered {r.status_code}")
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise ModelError("unexpected model server answer") from e
        return parse_answer(content if isinstance(content, str) else "")


class FakeEngine:
    """Deterministic stand-in (tests, local development without a GPU). Returns fixed, clearly fake content."""
    name = "fake"
    model = "fake-engine"

    def __init__(self, raw: str | None = None, fail: str | None = None, delay: float = 0.0):
        self.raw, self.fail, self.delay = raw, fail, delay

    async def ready(self) -> bool:
        return self.fail != "unavailable"

    async def analyze(self, jpeg: bytes, doc_type: str, instructions: str | None) -> ModelAnswer:
        import asyncio
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail == "unavailable":
            raise ModelUnavailable("fake: model down")
        if self.raw is not None:
            return parse_answer(self.raw)
        return ModelAnswer(document_type=doc_type if doc_type != "other" else "other", extracted_text="FAKE ENGINE TEXT",
                           fields={"surname": {"value": "EXAMPLE", "confidence": 0.5}}, missing_information=["expiry_date"])
