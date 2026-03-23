"""Tests for quality assessment."""

from researchclaw.quality import (
    assess_quality,
    check_strict_quality,
    compute_template_ratio,
    detect_template_content,
)


def test_clean_text_no_templates():
    """Clean text should have no template matches."""
    text = "This is a well-written paragraph about neural networks."
    matches = detect_template_content(text)
    assert len(matches) == 0


def test_detect_todo_placeholder():
    """TODO placeholders should be detected."""
    text = "[TODO: Add method description]"
    matches = detect_template_content(text)
    assert len(matches) > 0
    assert any("TODO" in m.pattern_desc for m in matches)


def test_detect_insert_placeholder():
    """INSERT placeholders should be detected."""
    text = "[INSERT results here]"
    matches = detect_template_content(text)
    assert len(matches) > 0


def test_detect_lorem_ipsum():
    """Lorem ipsum should be detected."""
    text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    matches = detect_template_content(text)
    assert len(matches) > 0


def test_clean_text_zero_ratio():
    """Clean text should have near-zero template ratio."""
    text = "Our method achieves state-of-the-art results on the benchmark."
    ratio = compute_template_ratio(text)
    assert ratio == 0.0


def test_template_text_nonzero_ratio():
    """Template text should have nonzero ratio."""
    text = "[TODO: Add results]\n[INSERT figure here]\nLorem ipsum dolor"
    ratio = compute_template_ratio(text)
    assert ratio > 0.0


def test_assess_quality_report():
    """Quality report should have expected structure."""
    report = assess_quality("This is a clean paper.")
    assert report.total_lines > 0
    assert report.total_chars > 0
    assert report.template_ratio == 0.0
    assert not report.has_template_content


def test_strict_quality_pass():
    """Clean text should pass strict quality check."""
    passed, msg = check_strict_quality("A well-written paper about deep learning.")
    assert passed


def test_strict_quality_fail():
    """Template text should fail strict quality check."""
    text = "\n".join(["[TODO: fill in]"] * 20 + ["one real line"])
    passed, msg = check_strict_quality(text)
    assert not passed
