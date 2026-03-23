"""Docker-based experiment sandbox."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class DockerSandbox:
    """Docker-based experiment execution environment."""

    @staticmethod
    def check_docker_available() -> bool:
        """Check if Docker daemon is reachable."""
        docker = shutil.which("docker")
        if not docker:
            return False
        try:
            result = subprocess.run(
                [docker, "info"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def ensure_image(image: str) -> bool:
        """Check if a Docker image exists locally."""
        docker = shutil.which("docker")
        if not docker:
            return False
        try:
            result = subprocess.run(
                [docker, "image", "inspect", image],
                capture_output=True, text=True, timeout=10, check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False
