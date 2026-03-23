"""Environment health checks — researchclaw doctor."""

from __future__ import annotations

import importlib
import json
import logging
import os
import shutil
import socket
import sys
import urllib.error
import urllib.request
from collections.abc import Callable as AbcCallable
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import ContextManager, cast

import yaml

from researchclaw.config import RCConfig, validate_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str  # pass | fail | warn
    detail: str
    fix: str = ""


@dataclass(frozen=True)
class DoctorReport:
    timestamp: str
    checks: list[CheckResult]
    overall: str

    @property
    def actionable_fixes(self) -> list[str]:
        return [check.fix for check in self.checks if check.fix]

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "overall": self.overall,
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail, "fix": c.fix}
                for c in self.checks
            ],
            "actionable_fixes": self.actionable_fixes,
        }


def check_python_version() -> CheckResult:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 11):
        return CheckResult("python_version", "pass", f"Python {v.major}.{v.minor}.{v.micro}")
    return CheckResult(
        "python_version", "fail",
        f"Python {v.major}.{v.minor}.{v.micro} is unsupported",
        fix="Install Python 3.11 or newer",
    )


def check_yaml_import() -> CheckResult:
    try:
        importlib.import_module("yaml")
    except ImportError:
        return CheckResult("yaml_import", "fail", "PyYAML is not importable", fix="pip install pyyaml")
    return CheckResult("yaml_import", "pass", "PyYAML import ok")


def check_config_valid(config_path: str | Path) -> CheckResult:
    path = Path(config_path)
    if not path.exists():
        return CheckResult("config_valid", "fail", f"Config file not found: {path}",
                           fix="Provide --config path to an existing YAML config file")
    try:
        with path.open(encoding="utf-8") as handle:
            data_obj = yaml.safe_load(handle.read())
    except yaml.YAMLError as exc:
        return CheckResult("config_valid", "fail", f"Config YAML parse error: {exc}",
                           fix="Fix YAML syntax errors in the config file")
    except OSError as exc:
        return CheckResult("config_valid", "fail", f"Could not read config file: {exc}",
                           fix="Verify file permissions and path")

    data: object = {} if data_obj is None else data_obj
    if not isinstance(data, dict):
        return CheckResult("config_valid", "fail", "Config root must be a mapping",
                           fix="Ensure the config file starts with key-value mappings")
    data_map = cast(Mapping[object, object], data)
    typed_data = {str(key): value for key, value in data_map.items()}
    result = validate_config(typed_data)
    if result.ok:
        return CheckResult("config_valid", "pass", "Config validation ok")
    return CheckResult("config_valid", "fail", "; ".join(result.errors),
                       fix="Fix validation errors in config file")


def check_llm_connectivity(base_url: str) -> CheckResult:
    if not base_url.strip():
        return CheckResult("llm_connectivity", "fail", "LLM base URL is empty",
                           fix="Set llm.base_url in config")
    url = f"{base_url.rstrip('/')}/models"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=5):
            return CheckResult("llm_connectivity", "pass", f"Reachable: {url}")
    except urllib.error.HTTPError as exc:
        if exc.code == 405:
            return CheckResult("llm_connectivity", "pass", f"Reachable: {url}")
        return CheckResult("llm_connectivity", "fail", f"LLM endpoint HTTP {exc.code}",
                           fix="Check llm.base_url and provider status")
    except (urllib.error.URLError, TimeoutError, OSError):
        return CheckResult("llm_connectivity", "fail", "LLM endpoint unreachable",
                           fix="Verify endpoint URL and network connectivity")


def check_api_key_valid(base_url: str, api_key: str) -> CheckResult:
    if not api_key.strip():
        return CheckResult("api_key_valid", "fail", "API key is empty",
                           fix="Set llm.api_key or environment variable defined by llm.api_key_env")
    try:
        url = f"{base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=5):
            return CheckResult("api_key_valid", "pass", "API key accepted")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return CheckResult("api_key_valid", "fail", "Invalid API key",
                               fix="Set a valid API key for the configured endpoint")
        return CheckResult("api_key_valid", "warn", f"API key check returned HTTP {exc.code}",
                           fix="Verify endpoint health and API key permissions")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return CheckResult("api_key_valid", "warn", f"Could not verify API key: {exc}",
                           fix="Retry when endpoint/network is available")


def check_sandbox_python(python_path: str) -> CheckResult:
    if not python_path.strip():
        return CheckResult("sandbox_python", "warn", "Sandbox python path is empty",
                           fix="Set experiment.sandbox.python_path in config")
    path = Path(python_path)
    if path.exists() and os.access(path, os.X_OK):
        return CheckResult("sandbox_python", "pass", f"Sandbox python found: {path}")
    return CheckResult("sandbox_python", "warn",
                       f"Sandbox python missing or not executable: {path}",
                       fix="Install sandbox interpreter or update experiment.sandbox.python_path")


def check_matplotlib() -> CheckResult:
    try:
        importlib.import_module("matplotlib")
    except ImportError:
        return CheckResult("matplotlib", "warn", "Not installed; charts will be skipped",
                           fix="pip install matplotlib")
    return CheckResult("matplotlib", "pass", "matplotlib import ok")


def check_experiment_mode(mode: str) -> CheckResult:
    if mode == "simulated":
        return CheckResult("experiment_mode", "warn",
                           "Experiment mode is simulated — results will be synthetic",
                           fix="Use sandbox or docker mode for real execution")
    return CheckResult("experiment_mode", "pass", f"Experiment mode: {mode}")


def check_acp_agent(agent_command: str) -> CheckResult:
    resolved = shutil.which(agent_command)
    if resolved:
        return CheckResult("acp_agent", "pass", f"ACP agent found: {resolved}")
    return CheckResult("acp_agent", "fail",
                       f"ACP agent '{agent_command}' not found on PATH",
                       fix=f"Install {agent_command} or update llm.acp.agent in config")


def run_doctor(config_path: str | Path) -> DoctorReport:
    """Run all health checks and return report."""
    checks: list[CheckResult] = []
    path = Path(config_path)

    checks.append(check_python_version())
    checks.append(check_yaml_import())
    checks.append(check_config_valid(path))

    base_url = ""
    api_key = ""
    model = ""
    fallback_models: tuple[str, ...] = ()
    sandbox_python_path = ""
    experiment_mode = ""
    provider = ""
    acp_agent_command = "claude"

    try:
        config = RCConfig.load(path, check_paths=False)
        provider = config.llm.provider
        base_url = config.llm.base_url
        api_key = config.llm.api_key or os.environ.get(config.llm.api_key_env, "")
        model = config.llm.primary_model
        fallback_models = config.llm.fallback_models
        sandbox_python_path = config.experiment.sandbox.python_path
        experiment_mode = config.experiment.mode
        acp_agent_command = config.llm.acp.agent
    except (FileNotFoundError, OSError, ValueError, yaml.YAMLError) as exc:
        logger.debug("Could not fully load config for doctor checks: %s", exc)

    if provider == "acp":
        checks.append(check_acp_agent(acp_agent_command))
    else:
        checks.append(check_llm_connectivity(base_url))
        checks.append(check_api_key_valid(base_url, api_key))
    checks.append(check_sandbox_python(sandbox_python_path))
    checks.append(check_matplotlib())
    checks.append(check_experiment_mode(experiment_mode))

    overall = "fail" if any(c.status == "fail" for c in checks) else "pass"
    return DoctorReport(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        checks=checks, overall=overall,
    )


def print_doctor_report(report: DoctorReport) -> None:
    icon_map = {"pass": "[OK]", "fail": "[FAIL]", "warn": "[WARN]"}
    print(f"ResearchClaw Doctor Report ({report.timestamp})")
    for check in report.checks:
        icon = icon_map.get(check.status, "-")
        print(f" {icon} {check.name}: {check.detail}")
        if check.fix:
            print(f"      Fix: {check.fix}")

    fail_count = sum(1 for c in report.checks if c.status == "fail")
    warn_count = sum(1 for c in report.checks if c.status == "warn")
    if report.overall == "pass":
        print("Result: PASS")
    else:
        print(f"Result: FAIL ({fail_count} errors, {warn_count} warnings)")


def write_doctor_report(report: DoctorReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
