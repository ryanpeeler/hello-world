"""Tests for the prompt management system."""

from researchclaw.prompts import PromptManager, _render


def test_render_simple():
    """Simple variable replacement."""
    result = _render("Hello {name}", {"name": "World"})
    assert result == "Hello World"


def test_render_missing_var():
    """Missing variables should be left as-is."""
    result = _render("Hello {name}", {})
    assert result == "Hello {name}"


def test_render_json_safe():
    """JSON-like patterns should not be substituted."""
    result = _render('{"key": "value"}', {"key": "replaced"})
    # The regex should only match bare {word} not {"word": ...}
    assert "value" in result


def test_prompt_manager_default_stages():
    """PromptManager should have all default stages."""
    pm = PromptManager()
    names = pm.stage_names()
    assert "topic_init" in names
    assert "paper_draft" in names
    assert "citation_verify" not in names  # This is handled differently


def test_prompt_manager_for_stage():
    """for_stage should return a rendered prompt."""
    pm = PromptManager()
    rp = pm.for_stage("topic_init", topic="RL for robotics", domains="ml, robotics",
                       hardware_tier="cpu_only", hardware_warning="No GPU")
    assert "RL for robotics" in rp.user
    assert rp.system  # Should have a system prompt


def test_prompt_manager_has_stage():
    pm = PromptManager()
    assert pm.has_stage("topic_init")
    assert not pm.has_stage("nonexistent_stage")


def test_prompt_manager_sub_prompt():
    pm = PromptManager()
    rp = pm.sub_prompt("code_repair", error="NameError: x", code="print(x)")
    assert "NameError" in rp.user
