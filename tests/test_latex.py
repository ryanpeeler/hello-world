"""Tests for LaTeX export."""

from researchclaw.export.latex import convert_to_latex, _escape_latex, check_paper_completeness


def test_convert_basic():
    """Basic markdown should convert to LaTeX."""
    md = "# My Paper\n\n## Abstract\n\nThis is the abstract.\n\n## Introduction\n\nHello world."
    latex = convert_to_latex(md, template="neurips2025")
    assert "\\title{My Paper}" in latex
    assert "\\begin{document}" in latex
    assert "\\end{document}" in latex
    assert "\\section{Introduction}" in latex


def test_escape_latex():
    """Special characters should be escaped."""
    assert _escape_latex("a & b") == "a \\& b"
    assert _escape_latex("100%") == "100\\%"
    assert _escape_latex("$10") == "\\$10"


def test_check_paper_completeness():
    """Completeness check should detect missing sections."""
    text = "## Abstract\n\n## Introduction\n\n## Method\n"
    result = check_paper_completeness(text)
    assert result["abstract"] is True
    assert result["introduction"] is True
    assert result["method"] is True
    assert result["conclusion"] is False
