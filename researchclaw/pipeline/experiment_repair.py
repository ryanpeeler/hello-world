"""Experiment repair — self-healing code repair through LLM interventions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def repair_experiment(
    *,
    script_path: Path,
    error_message: str,
    llm: Any,
    pm: Any,
    max_rounds: int = 5,
) -> tuple[bool, str]:
    """Attempt to repair a failing experiment script.

    Returns (success, repaired_code).
    """
    code = script_path.read_text(encoding="utf-8")

    for round_num in range(1, max_rounds + 1):
        logger.info("Repair attempt %d/%d for %s", round_num, max_rounds, script_path.name)

        prompt = pm.sub_prompt("code_repair", error=error_message, code=code)
        resp = llm.chat(
            [{"role": "user", "content": prompt.user}],
            system=prompt.system,
            strip_thinking=True,
        )

        repaired_code = _extract_code(resp.content)
        if not repaired_code:
            logger.warning("No code extracted from repair response")
            continue

        # Validate AST
        if _validate_ast(repaired_code):
            script_path.write_text(repaired_code, encoding="utf-8")
            return True, repaired_code

        code = repaired_code
        error_message = "Code failed AST validation after repair attempt"

    return False, code


def _extract_code(text: str) -> str:
    """Extract Python code from LLM response."""
    # Try to find code block
    import re
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no code block, assume entire response is code
    return text.strip()


def _validate_ast(code: str) -> bool:
    """Check if Python code has valid syntax."""
    try:
        compile(code, "<repair>", "exec")
        return True
    except SyntaxError:
        return False
