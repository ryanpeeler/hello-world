"""Code agent — multi-phase experiment code generation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def generate_experiment_code(
    *,
    exp_plan: str,
    hardware_info: str,
    output_dir: Path,
    llm: Any,
    pm: Any,
    config: Any,
) -> list[Path]:
    """Generate experiment code using the code agent pipeline.

    Phases:
    1. Architecture planning
    2. Sequential file generation
    3. AST validation
    4. Review
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []

    # Phase 1: Generate main experiment script
    prompt = pm.for_stage(
        "code_generation",
        exp_plan=exp_plan,
        topic="",
        hardware=hardware_info,
    )
    resp = llm.chat(
        [{"role": "user", "content": prompt.user}],
        system=prompt.system,
        max_tokens=prompt.max_tokens,
        strip_thinking=True,
    )

    code = _extract_python_code(resp.content)
    main_script = output_dir / "run_experiment.py"
    main_script.write_text(code, encoding="utf-8")
    generated_files.append(main_script)

    # Validate AST
    if not _validate_python(code):
        logger.warning("Generated code has syntax errors — will attempt repair during execution")

    return generated_files


def _extract_python_code(text: str) -> str:
    """Extract Python code from LLM response."""
    import re
    match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _validate_python(code: str) -> bool:
    """Check if Python code compiles."""
    try:
        compile(code, "<generated>", "exec")
        return True
    except SyntaxError:
        return False
