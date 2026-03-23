"""LLM integration — OpenAI-compatible and ACP agent clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from researchclaw.config import RCConfig
    from researchclaw.llm.acp_client import ACPClient
    from researchclaw.llm.client import LLMClient

PROVIDER_PRESETS = {
    "openai": {"base_url": "https://api.openai.com/v1"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1"},
    "anthropic": {"base_url": "https://api.anthropic.com"},
    "kimi-anthropic": {"base_url": "https://api.kimi.com/coding/"},
    "novita": {"base_url": "https://api.novita.ai/openai"},
    "minimax": {"base_url": "https://api.minimax.io/v1"},
    "openai-compatible": {"base_url": None},
}


def create_llm_client(config: RCConfig) -> LLMClient | ACPClient:
    """Factory: return the right LLM client based on ``config.llm.provider``."""
    if config.llm.provider == "acp":
        from researchclaw.llm.acp_client import ACPClient as _ACP
        return _ACP.from_rc_config(config)

    from researchclaw.llm.client import LLMClient as _LLM
    return _LLM.from_rc_config(config)
