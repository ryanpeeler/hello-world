"""Writing quality guidelines for paper generation."""

from __future__ import annotations

WRITING_RULES: list[str] = [
    "Do NOT use placeholder text, TODO markers, or template language.",
    "Do NOT include disclaimers about being an AI or limitations of AI.",
    "Write in active voice where possible.",
    "Use precise, specific language — avoid vague qualifiers.",
    "Every claim must be supported by evidence or citation.",
    "Use LaTeX-style citations: \\cite{key}.",
    "Tables and figures must have descriptive captions.",
    "Each section must contain substantive, original content.",
    "Abstract should be 180-220 words, self-contained.",
    "Introduction must clearly state the problem, motivation, and contributions.",
    "Related work must compare and contrast, not just list.",
    "Method section must be detailed enough to reproduce.",
    "Results must include quantitative comparisons and statistical significance.",
    "Discussion must interpret results and address limitations.",
    "Conclusion must summarize contributions and suggest future work.",
]


def get_writing_guide() -> str:
    """Return the full writing guide as a formatted string."""
    lines = ["# Academic Paper Writing Guidelines", ""]
    for i, rule in enumerate(WRITING_RULES, 1):
        lines.append(f"{i}. {rule}")
    return "\n".join(lines)
