"""ACP (Agent Client Protocol) client — spawns local AI agents."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ACPResponse:
    content: str
    model: str = "acp"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    truncated: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


class ACPClient:
    """Client for ACP-compatible agents (Claude, Codex, etc.)."""

    def __init__(self, agent_command: str = "claude", model: str = "", timeout_sec: int = 600) -> None:
        self.agent_command = agent_command
        self.model = model
        self.timeout_sec = timeout_sec

    @classmethod
    def from_rc_config(cls, config: Any) -> ACPClient:
        acp_cfg = config.llm.acp
        return cls(
            agent_command=acp_cfg.agent,
            model=acp_cfg.model,
            timeout_sec=600,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        system: str | None = None,
        strip_thinking: bool = False,
    ) -> ACPResponse:
        """Send a chat request via the ACP agent CLI."""
        # Build prompt from messages
        prompt_parts = []
        if system:
            prompt_parts.append(system)
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(msg["content"])
            else:
                prompt_parts.append(msg["content"])

        full_prompt = "\n\n".join(prompt_parts)

        if json_mode:
            full_prompt += "\n\nRespond with valid JSON only."

        # Call agent
        agent = shutil.which(self.agent_command)
        if not agent:
            raise RuntimeError(f"ACP agent '{self.agent_command}' not found on PATH")

        try:
            result = subprocess.run(
                [agent, "--print", "-p", full_prompt],
                capture_output=True, text=True,
                timeout=self.timeout_sec, check=False,
            )

            content = result.stdout.strip()
            if not content and result.stderr:
                content = result.stderr.strip()

            if strip_thinking:
                from researchclaw.utils.thinking_tags import strip_thinking_tags
                content = strip_thinking_tags(content)

            return ACPResponse(content=content, model=self.agent_command)

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ACP agent timed out after {self.timeout_sec}s")
        except (FileNotFoundError, OSError) as exc:
            raise RuntimeError(f"ACP agent failed: {exc}") from exc

    def preflight(self) -> tuple[bool, str]:
        """Quick check that the agent CLI works."""
        try:
            agent = shutil.which(self.agent_command)
            if not agent:
                return False, f"Agent '{self.agent_command}' not found on PATH"
            result = subprocess.run(
                [agent, "--version"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if result.returncode == 0:
                return True, f"ACP agent '{self.agent_command}' available"
            return False, f"Agent returned exit code {result.returncode}"
        except Exception as exc:
            return False, f"ACP check failed: {exc}"
