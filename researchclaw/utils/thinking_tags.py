"""Strip <think>…</think> reasoning tags from LLM output."""

from __future__ import annotations

import re


def strip_thinking_tags(text: str) -> str:
    """Remove <think>…</think> blocks from LLM responses.

    These tags contain chain-of-thought reasoning that should not
    appear in final artifacts (papers, scripts, etc.).
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
