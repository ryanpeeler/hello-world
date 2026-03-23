"""OpenCode Beast Mode bridge — delegates complex code generation to OpenCode."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def is_opencode_available() -> bool:
    """Check if the opencode CLI is on PATH."""
    return shutil.which("opencode") is not None


def generate_with_opencode(
    *,
    spec: str,
    output_dir: Path,
    model: str = "gpt-4o",
    timeout_sec: int = 600,
) -> bool:
    """Use OpenCode to generate a multi-file experiment project.

    Returns True on success.
    """
    if not is_opencode_available():
        logger.warning("OpenCode not available — falling back to built-in code generation")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    opencode = shutil.which("opencode") or "opencode"
    try:
        result = subprocess.run(
            [opencode, "--print", "-p", spec],
            capture_output=True, text=True,
            timeout=timeout_sec, cwd=str(output_dir),
            check=False,
        )
        if result.returncode == 0:
            logger.info("OpenCode generated code successfully")
            return True
        else:
            logger.warning("OpenCode failed (exit %d): %s", result.returncode, result.stderr[:200])
            return False
    except subprocess.TimeoutExpired:
        logger.warning("OpenCode timed out after %ds", timeout_sec)
        return False
    except (FileNotFoundError, OSError) as exc:
        logger.warning("OpenCode execution failed: %s", exc)
        return False
