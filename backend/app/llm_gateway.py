from __future__ import annotations

import json
import os
from dataclasses import dataclass
from uuid import uuid4

import httpx


@dataclass
class LlmResult:
    data: dict | None
    warnings: list[str]


class LlmGateway:
    @staticmethod
    def completion_json(*, system_prompt: str, user_prompt: str, max_tokens: int) -> LlmResult:
        provider = os.getenv("DUI_LLM_PROVIDER", "apifree").strip().lower()
        if provider == "disabled":
            return LlmResult(data=None, warnings=["LLM provider is disabled. Using DUI rule-based fallback."])

        model = LlmGateway._resolve_model(provider)
        base_url = LlmGateway._resolve_base_url(provider)
        api_key = LlmGateway._resolve_api_key(provider)
        if not base_url or not model:
            return LlmResult(data=None, warnings=["LLM endpoint is not configured. Using DUI rule-based fallback."])
        if provider == "apifree" and not api_key:
            return LlmResult(data=None, warnings=["APIFREE_API_KEY is not set. Using DUI rule-based fallback."])

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        timeout_seconds = float(os.getenv("DUI_LLM_TIMEOUT_SEC", os.getenv("APIFREE_TIMEOUT_SEC", "60")))
        debug_enabled = LlmGateway._is_enabled("DUI_LLM_LOG_INPUT")
        request_id = str(uuid4())

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                if debug_enabled:
                    LlmGateway._log_llm_input(
                        request_id=request_id,
                        provider=provider,
                        base_url=base_url,
                        timeout_seconds=timeout_seconds,
                        stage="primary",
                        payload=payload,
                    )
                response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                if response.status_code >= 400:
                    # Many local OpenAI-compatible servers ignore response_format.
                    fallback_payload = dict(payload)
                    fallback_payload.pop("response_format", None)
                    if debug_enabled:
                        LlmGateway._log_llm_input(
                            request_id=request_id,
                            provider=provider,
                            base_url=base_url,
                            timeout_seconds=timeout_seconds,
                            stage="fallback_without_response_format",
                            payload=fallback_payload,
                        )
                    response = client.post(f"{base_url}/chat/completions", headers=headers, json=fallback_payload)
                response.raise_for_status()

            content = LlmGateway._extract_assistant_content(response.json())
            if not content:
                return LlmResult(data=None, warnings=["LLM returned empty content. Using DUI rule-based fallback."])
            parsed = LlmGateway._parse_json(content)
            if parsed is None:
                return LlmResult(data=None, warnings=["Failed to parse LLM JSON output. Using DUI rule-based fallback."])
            return LlmResult(data=parsed, warnings=[])
        except Exception as error:  # noqa: BLE001
            return LlmResult(data=None, warnings=[f"LLM call failed ({type(error).__name__}). Using DUI rule-based fallback."])

    @staticmethod
    def _resolve_model(provider: str) -> str:
        if provider == "apifree":
            return os.getenv("APIFREE_MODEL", "deepseek-ai/deepseek-r1-0528")
        return os.getenv("DUI_LLM_MODEL", "qwen2.5:14b-instruct")

    @staticmethod
    def _resolve_base_url(provider: str) -> str:
        if provider == "apifree":
            return os.getenv("APIFREE_BASE_URL", "https://api.apifree.ai/v1").rstrip("/")
        return os.getenv("DUI_LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")

    @staticmethod
    def _resolve_api_key(provider: str) -> str:
        if provider == "apifree":
            return os.getenv("APIFREE_API_KEY", "").strip()
        return os.getenv("DUI_LLM_API_KEY", "").strip()

    @staticmethod
    def _extract_assistant_content(body: dict) -> str | None:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            return "\n".join(chunks) if chunks else None
        return None

    @staticmethod
    def _parse_json(content: str) -> dict | None:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.removeprefix("```json").removeprefix("```")
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()

        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _is_enabled(env_name: str) -> bool:
        return os.getenv(env_name, "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _log_llm_input(
        *,
        request_id: str,
        provider: str,
        base_url: str,
        timeout_seconds: float,
        stage: str,
        payload: dict[str, object],
    ) -> None:
        event = {
            "event": "dui.llm.input",
            "request_id": request_id,
            "stage": stage,
            "provider": provider,
            "base_url": base_url,
            "timeout_seconds": timeout_seconds,
            "payload": payload,
        }
        print("[DUI_LLM_LOG_INPUT]", json.dumps(event, ensure_ascii=False, indent=2), flush=True)
