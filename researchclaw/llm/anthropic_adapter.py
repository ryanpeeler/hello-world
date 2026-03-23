"""Anthropic Messages API adapter — translates OpenAI-style calls to Anthropic."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class AnthropicAdapter:
    """Adapter for Anthropic's Messages API (Claude models)."""

    def __init__(self, base_url: str, api_key: str, timeout_sec: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_sec = timeout_sec

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> dict[str, Any]:
        """Make a chat completion call using the Anthropic Messages API."""
        # Separate system message
        system_text = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                user_messages.append(msg)

        if json_mode:
            system_text += "\nYou MUST respond with valid JSON only. No text outside the JSON object."

        # Build request body
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_text.strip():
            body["system"] = system_text.strip()

        payload = json.dumps(body).encode("utf-8")
        url = f"{self.base_url}/v1/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(url, data=payload, headers=headers)

        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            data = json.loads(resp.read())

        # Convert Anthropic response to OpenAI format
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})

        return {
            "choices": [{
                "message": {"role": "assistant", "content": content},
                "finish_reason": data.get("stop_reason", "end_turn"),
            }],
            "model": data.get("model", model),
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
        }
