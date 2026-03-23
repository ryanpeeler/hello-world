"""ResearchClaw configuration — YAML-backed frozen dataclasses."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CONFIG_SEARCH_ORDER: tuple[str, ...] = ("config.arc.yaml", "config.yaml")
EXAMPLE_CONFIG = "config.researchclaw.example.yaml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Nested dict lookup."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectConfig:
    name: str = "my-research"
    mode: str = "full-auto"  # full-auto | semi-auto | docs-first


@dataclass(frozen=True)
class ResearchConfig:
    topic: str = ""
    domains: tuple[str, ...] = ("ml",)
    daily_papers: int = 10
    quality_threshold: float = 4.0
    graceful_degradation: bool = True


@dataclass(frozen=True)
class RuntimeConfig:
    timezone: str = "UTC"
    max_parallel: int = 3
    approval_timeout_hours: int = 12
    max_retries: int = 2


@dataclass(frozen=True)
class NotificationsConfig:
    enabled: bool = False
    channel: str = ""


@dataclass(frozen=True)
class KnowledgeBaseConfig:
    backend: str = "markdown"
    root: str = "docs/kb"


@dataclass(frozen=True)
class ACPConfig:
    agent: str = "claude"
    model: str = ""
    session_reuse: bool = True


@dataclass(frozen=True)
class LlmConfig:
    provider: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    api_key_env: str = "OPENAI_API_KEY"
    primary_model: str = "gpt-4o"
    fallback_models: tuple[str, ...] = ("gpt-4.1", "gpt-4o-mini")
    acp: ACPConfig = field(default_factory=ACPConfig)


@dataclass(frozen=True)
class SecurityConfig:
    hitl_required_stages: tuple[int, ...] = (5, 9, 20)
    allow_network_in_sandbox: bool = False
    network_policy: str = "block-all"


@dataclass(frozen=True)
class SandboxConfig:
    python_path: str = ".venv/bin/python"
    time_budget_sec: int = 300
    max_iterations: int = 10


@dataclass(frozen=True)
class DockerConfig:
    image: str = "researchclaw-sandbox:latest"
    gpu_enabled: bool = False
    network_policy: str = "block-all"
    memory_limit: str = "8g"


@dataclass(frozen=True)
class SSHConfig:
    host: str = ""
    user: str = ""
    key_path: str = ""
    remote_dir: str = "/tmp/researchclaw"


@dataclass(frozen=True)
class OpenCodeConfig:
    enabled: bool = False
    model: str = "gpt-4o"
    timeout_sec: int = 600


@dataclass(frozen=True)
class CodeAgentConfig:
    enabled: bool = True
    architecture_planning: bool = True
    multi_file: bool = True
    review_enabled: bool = True
    max_repair_rounds: int = 5


@dataclass(frozen=True)
class BenchmarkAgentConfig:
    enabled: bool = True
    huggingface_search: bool = True
    web_search: bool = True


@dataclass(frozen=True)
class FigureAgentConfig:
    enabled: bool = True
    backends: tuple[str, ...] = ("matplotlib",)


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str = "sandbox"  # sandbox | docker | ssh | simulated
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    ssh: SSHConfig = field(default_factory=SSHConfig)
    opencode: OpenCodeConfig = field(default_factory=OpenCodeConfig)
    code_agent: CodeAgentConfig = field(default_factory=CodeAgentConfig)
    benchmark_agent: BenchmarkAgentConfig = field(default_factory=BenchmarkAgentConfig)
    figure_agent: FigureAgentConfig = field(default_factory=FigureAgentConfig)


@dataclass(frozen=True)
class MetaClawBridgeConfig:
    enabled: bool = False
    proxy_url: str = ""
    fallback_url: str = ""
    fallback_api_key: str = ""
    skill_injection: bool = True
    quality_gates: bool = True


@dataclass(frozen=True)
class ExportConfig:
    format: str = "neurips2025"
    latex_engine: str = "pdflatex"


@dataclass(frozen=True)
class RCConfig:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    knowledge_base: KnowledgeBaseConfig = field(default_factory=KnowledgeBaseConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    metaclaw_bridge: MetaClawBridgeConfig = field(default_factory=MetaClawBridgeConfig)
    export: ExportConfig = field(default_factory=ExportConfig)

    @classmethod
    def load(cls, path: Path, *, check_paths: bool = True) -> RCConfig:
        """Load config from a YAML file."""
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        if not isinstance(raw, dict):
            raise ValueError(f"Config root must be a mapping, got {type(raw).__name__}")

        project_d = raw.get("project", {}) or {}
        research_d = raw.get("research", {}) or {}
        runtime_d = raw.get("runtime", {}) or {}
        notif_d = raw.get("notifications", {}) or {}
        kb_d = raw.get("knowledge_base", {}) or {}
        llm_d = raw.get("llm", {}) or {}
        sec_d = raw.get("security", {}) or {}
        exp_d = raw.get("experiment", {}) or {}
        mc_d = raw.get("metaclaw_bridge", {}) or {}
        export_d = raw.get("export", {}) or {}

        # LLM sub-configs
        acp_d = llm_d.get("acp", {}) or {}
        acp = ACPConfig(
            agent=acp_d.get("agent", "claude"),
            model=acp_d.get("model", ""),
            session_reuse=acp_d.get("session_reuse", True),
        )

        llm = LlmConfig(
            provider=llm_d.get("provider", "openai-compatible"),
            base_url=llm_d.get("base_url", "https://api.openai.com/v1"),
            api_key=llm_d.get("api_key", ""),
            api_key_env=llm_d.get("api_key_env", "OPENAI_API_KEY"),
            primary_model=llm_d.get("primary_model", "gpt-4o"),
            fallback_models=tuple(llm_d.get("fallback_models", ["gpt-4.1", "gpt-4o-mini"])),
            acp=acp,
        )

        # Experiment sub-configs
        sandbox_d = exp_d.get("sandbox", {}) or {}
        docker_d = exp_d.get("docker", {}) or {}
        ssh_d = exp_d.get("ssh", {}) or {}
        oc_d = exp_d.get("opencode", {}) or {}
        ca_d = exp_d.get("code_agent", {}) or {}
        ba_d = exp_d.get("benchmark_agent", {}) or {}
        fa_d = exp_d.get("figure_agent", {}) or {}

        sandbox = SandboxConfig(
            python_path=sandbox_d.get("python_path", ".venv/bin/python"),
            time_budget_sec=_safe_int(sandbox_d.get("time_budget_sec"), 300),
            max_iterations=_safe_int(sandbox_d.get("max_iterations"), 10),
        )
        docker = DockerConfig(
            image=docker_d.get("image", "researchclaw-sandbox:latest"),
            gpu_enabled=docker_d.get("gpu_enabled", False),
            network_policy=docker_d.get("network_policy", "block-all"),
            memory_limit=docker_d.get("memory_limit", "8g"),
        )
        ssh = SSHConfig(
            host=ssh_d.get("host", ""),
            user=ssh_d.get("user", ""),
            key_path=ssh_d.get("key_path", ""),
            remote_dir=ssh_d.get("remote_dir", "/tmp/researchclaw"),
        )
        opencode = OpenCodeConfig(
            enabled=oc_d.get("enabled", False),
            model=oc_d.get("model", "gpt-4o"),
            timeout_sec=_safe_int(oc_d.get("timeout_sec"), 600),
        )
        code_agent = CodeAgentConfig(
            enabled=ca_d.get("enabled", True),
            architecture_planning=ca_d.get("architecture_planning", True),
            multi_file=ca_d.get("multi_file", True),
            review_enabled=ca_d.get("review_enabled", True),
            max_repair_rounds=_safe_int(ca_d.get("max_repair_rounds"), 5),
        )
        benchmark_agent = BenchmarkAgentConfig(
            enabled=ba_d.get("enabled", True),
            huggingface_search=ba_d.get("huggingface_search", True),
            web_search=ba_d.get("web_search", True),
        )
        figure_agent = FigureAgentConfig(
            enabled=fa_d.get("enabled", True),
            backends=tuple(fa_d.get("backends", ["matplotlib"])),
        )

        experiment = ExperimentConfig(
            mode=exp_d.get("mode", "sandbox"),
            sandbox=sandbox,
            docker=docker,
            ssh=ssh,
            opencode=opencode,
            code_agent=code_agent,
            benchmark_agent=benchmark_agent,
            figure_agent=figure_agent,
        )

        # Security
        hitl_raw = sec_d.get("hitl_required_stages", [5, 9, 20])
        hitl = tuple(_safe_int(s) for s in (hitl_raw or []))

        security = SecurityConfig(
            hitl_required_stages=hitl,
            allow_network_in_sandbox=sec_d.get("allow_network_in_sandbox", False),
            network_policy=sec_d.get("network_policy", "block-all"),
        )

        # MetaClaw bridge
        metaclaw = MetaClawBridgeConfig(
            enabled=mc_d.get("enabled", False),
            proxy_url=mc_d.get("proxy_url", ""),
            fallback_url=mc_d.get("fallback_url", ""),
            fallback_api_key=mc_d.get("fallback_api_key", ""),
            skill_injection=mc_d.get("skill_injection", True),
            quality_gates=mc_d.get("quality_gates", True),
        )

        # Validate paths
        if check_paths and kb_d.get("root"):
            kb_path = Path(kb_d["root"])
            if not kb_path.exists():
                logger.warning("Knowledge base root does not exist: %s", kb_path)

        domains_raw = research_d.get("domains", ["ml"])
        if isinstance(domains_raw, str):
            domains_raw = [d.strip() for d in domains_raw.split(",")]

        return cls(
            project=ProjectConfig(
                name=project_d.get("name", "my-research"),
                mode=project_d.get("mode", "full-auto"),
            ),
            research=ResearchConfig(
                topic=research_d.get("topic", ""),
                domains=tuple(domains_raw),
                daily_papers=_safe_int(research_d.get("daily_papers"), 10),
                quality_threshold=_safe_float(research_d.get("quality_threshold"), 4.0),
                graceful_degradation=research_d.get("graceful_degradation", True),
            ),
            runtime=RuntimeConfig(
                timezone=runtime_d.get("timezone", "UTC"),
                max_parallel=_safe_int(runtime_d.get("max_parallel"), 3),
                approval_timeout_hours=_safe_int(runtime_d.get("approval_timeout_hours"), 12),
                max_retries=_safe_int(runtime_d.get("max_retries"), 2),
            ),
            notifications=NotificationsConfig(
                enabled=notif_d.get("enabled", False),
                channel=notif_d.get("channel", ""),
            ),
            knowledge_base=KnowledgeBaseConfig(
                backend=kb_d.get("backend", "markdown"),
                root=kb_d.get("root", "docs/kb"),
            ),
            llm=llm,
            security=security,
            experiment=experiment,
            metaclaw_bridge=metaclaw,
            export=ExportConfig(
                format=export_d.get("format", "neurips2025"),
                latex_engine=export_d.get("latex_engine", "pdflatex"),
            ),
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_VALID_MODES = {"full-auto", "semi-auto", "docs-first"}
_VALID_EXP_MODES = {"sandbox", "docker", "ssh", "simulated", "colab"}
_VALID_NETWORK_POLICIES = {"block-all", "allow-downloads", "allow-all"}


def validate_config(
    data: dict[str, Any], *, check_paths: bool = True
) -> ValidationResult:
    """Validate raw config dict before loading."""
    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    project = data.get("project", {}) or {}
    research = data.get("research", {}) or {}
    llm = data.get("llm", {}) or {}

    if not project.get("name"):
        errors.append("project.name is required")
    if not research.get("topic"):
        errors.append("research.topic is required")

    # Mode validation
    mode = project.get("mode", "full-auto")
    if mode not in _VALID_MODES:
        errors.append(f"project.mode must be one of {_VALID_MODES}, got '{mode}'")

    exp = data.get("experiment", {}) or {}
    exp_mode = exp.get("mode", "sandbox")
    if exp_mode not in _VALID_EXP_MODES:
        errors.append(f"experiment.mode must be one of {_VALID_EXP_MODES}, got '{exp_mode}'")

    # Network policy
    sec = data.get("security", {}) or {}
    net_policy = sec.get("network_policy", "block-all")
    if net_policy not in _VALID_NETWORK_POLICIES:
        warnings.append(
            f"security.network_policy '{net_policy}' not in {_VALID_NETWORK_POLICIES}"
        )

    # HITL stage validation
    hitl = sec.get("hitl_required_stages", [])
    if hitl:
        for s in hitl:
            si = _safe_int(s, -1)
            if si < 1 or si > 23:
                errors.append(f"security.hitl_required_stages: {s} not in range 1-23")

    # LLM
    if not llm.get("primary_model"):
        warnings.append("llm.primary_model not set, defaulting to gpt-4o")

    # Path checks
    if check_paths:
        kb = data.get("knowledge_base", {}) or {}
        root = kb.get("root", "")
        if root and not Path(root).exists():
            warnings.append(f"knowledge_base.root does not exist: {root}")

    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


def resolve_config_path(explicit: str | None = None) -> Path | None:
    """Resolve the config file path."""
    if explicit:
        return Path(explicit)
    for name in CONFIG_SEARCH_ORDER:
        p = Path(name)
        if p.exists():
            return p
    return None
