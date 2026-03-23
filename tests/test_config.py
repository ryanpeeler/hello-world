"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path

import yaml

from researchclaw.config import RCConfig, validate_config, resolve_config_path


def test_validate_valid_config():
    """Valid config should pass validation."""
    data = {
        "project": {"name": "test", "mode": "full-auto"},
        "research": {"topic": "test topic"},
        "llm": {"primary_model": "gpt-4o"},
    }
    result = validate_config(data, check_paths=False)
    assert result.ok


def test_validate_missing_topic():
    """Missing topic should fail."""
    data = {"project": {"name": "test"}, "research": {}}
    result = validate_config(data, check_paths=False)
    assert not result.ok
    assert any("topic" in e for e in result.errors)


def test_validate_invalid_mode():
    """Invalid mode should fail."""
    data = {
        "project": {"name": "test", "mode": "invalid"},
        "research": {"topic": "test"},
    }
    result = validate_config(data, check_paths=False)
    assert not result.ok


def test_load_config_from_yaml():
    """Config should load from YAML file."""
    config_data = {
        "project": {"name": "test-project", "mode": "semi-auto"},
        "research": {"topic": "Neural architecture search", "domains": ["ml"]},
        "llm": {
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "primary_model": "gpt-4o",
            "fallback_models": ["gpt-4o-mini"],
        },
        "experiment": {"mode": "sandbox"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        f.flush()
        config = RCConfig.load(Path(f.name), check_paths=False)

    assert config.project.name == "test-project"
    assert config.project.mode == "semi-auto"
    assert config.research.topic == "Neural architecture search"
    assert config.llm.primary_model == "gpt-4o"
    assert config.experiment.mode == "sandbox"


def test_resolve_config_path_explicit():
    """Explicit path should be returned."""
    result = resolve_config_path("some/path.yaml")
    assert result == Path("some/path.yaml")


def test_config_defaults():
    """Default config should have sane defaults."""
    config = RCConfig()
    assert config.project.mode == "full-auto"
    assert config.experiment.mode == "sandbox"
    assert config.llm.primary_model == "gpt-4o"
    assert config.security.hitl_required_stages == (5, 9, 20)
