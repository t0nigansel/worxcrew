from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib import error, request


class LLMError(RuntimeError):
    pass


@dataclass
class LLMSettings:
    model: str
    api_key: str
    base_url: str
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "LLMSettings | None":
        model = os.getenv("CV_LLM_MODEL") or os.getenv("OPENAI_MODEL") or ""
        api_key = os.getenv("CV_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        base_url = os.getenv("CV_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        if not model or not api_key:
            return None
        timeout = float(os.getenv("CV_LLM_TIMEOUT_SECONDS", "60"))
        return cls(model=model, api_key=api_key, base_url=base_url.rstrip("/"), timeout_seconds=timeout)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


class OpenAICompatibleClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        payload = {
            "model": self.settings.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = self._post_json(payload)
        text = _extract_text(response)
        return _parse_json_response(text)

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = f"{self.settings.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"LLM request failed with HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise LLMError(f"LLM request failed: {exc.reason}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON envelope: {raw[:400]}") from exc


def _extract_text(payload: Dict[str, Any]) -> str:
    choices: List[Dict[str, Any]] = payload.get("choices") or []
    if not choices:
        raise LLMError("LLM response contained no choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        if parts:
            return "\n".join(parts)

    raise LLMError(f"Unsupported LLM content format: {content!r}")


def _parse_json_response(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        raise LLMError("LLM returned an empty response.")

    fenced = text
    if "```" in text:
        blocks = text.split("```")
        for block in blocks:
            candidate = block.strip()
            if candidate.startswith("json"):
                fenced = candidate[4:].strip()
                break
            if candidate.startswith("{"):
                fenced = candidate
                break

    for candidate in [text, fenced]:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise LLMError(f"LLM did not return a valid JSON object: {text[:600]}")
