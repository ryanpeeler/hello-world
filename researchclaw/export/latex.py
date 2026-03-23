"""Markdown-to-LaTeX converter with conference templates."""

from __future__ import annotations

import re

# Conference template preambles
_TEMPLATES: dict[str, str] = {
    "neurips2025": r"""\documentclass{article}
\usepackage[preprint]{neurips_2025}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{nicefrac}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{natbib}
""",
    "iclr2026": r"""\documentclass{article}
\usepackage{iclr2026_conference}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{nicefrac}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{natbib}
""",
    "icml2026": r"""\documentclass[accepted]{icml2026}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{nicefrac}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{natbib}
""",
}


def convert_to_latex(markdown: str, template: str = "neurips2025") -> str:
    """Convert a Markdown paper to LaTeX with the specified conference template."""
    preamble = _TEMPLATES.get(template, _TEMPLATES["neurips2025"])

    # Extract title from first H1
    title = "Untitled"
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if title_match:
        title = _escape_latex(title_match.group(1))

    # Build LaTeX document
    lines = [preamble]
    lines.append(f"\\title{{{title}}}")
    lines.append("")
    lines.append("\\author{AutoResearchClaw}")
    lines.append("")
    lines.append("\\begin{document}")
    lines.append("\\maketitle")
    lines.append("")

    # Convert markdown body to LaTeX
    body = _convert_body(markdown)
    lines.append(body)

    lines.append("")
    lines.append("\\bibliographystyle{plainnat}")
    lines.append("\\bibliography{references}")
    lines.append("")
    lines.append("\\end{document}")

    return "\n".join(lines)


def _convert_body(markdown: str) -> str:
    """Convert markdown body to LaTeX."""
    lines = markdown.split("\n")
    output: list[str] = []
    in_code_block = False

    for line in lines:
        # Skip the title line
        if line.startswith("# ") and not line.startswith("## "):
            continue

        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                output.append("\\end{verbatim}")
                in_code_block = False
            else:
                output.append("\\begin{verbatim}")
                in_code_block = True
            continue

        if in_code_block:
            output.append(line)
            continue

        # Headers
        if line.startswith("## "):
            section_name = _escape_latex(line[3:].strip())
            if section_name.lower() == "abstract":
                output.append("\\begin{abstract}")
                output.append("")  # Content follows
                # Find end of abstract (next ## or empty section)
                continue
            output.append(f"\\section{{{section_name}}}")
            continue
        if line.startswith("### "):
            output.append(f"\\subsection{{{_escape_latex(line[4:].strip())}}}")
            continue
        if line.startswith("#### "):
            output.append(f"\\subsubsection{{{_escape_latex(line[5:].strip())}}}")
            continue

        # Bold and italic
        converted = line
        converted = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", converted)
        converted = re.sub(r"\*(.+?)\*", r"\\textit{\1}", converted)

        # Citations
        converted = re.sub(r"\\cite\{([^}]+)\}", r"\\citep{\1}", converted)

        # Bullet points
        if converted.strip().startswith("- "):
            converted = "\\item " + _escape_latex(converted.strip()[2:])

        output.append(converted)

    # Close any open abstract
    text = "\n".join(output)
    if "\\begin{abstract}" in text:
        # Find the next \section after abstract and insert \end{abstract}
        text = re.sub(
            r"(\\begin\{abstract\}.*?)(\\section)",
            r"\1\\end{abstract}\n\n\2",
            text,
            count=1,
            flags=re.DOTALL,
        )

    return text


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    specials = {
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    for char, replacement in specials.items():
        text = text.replace(char, replacement)
    return text


def check_paper_completeness(text: str) -> dict[str, bool]:
    """Check if all required sections are present."""
    from researchclaw.prompts import SECTION_WORD_TARGETS, _SECTION_TARGET_ALIASES

    required_sections = set(SECTION_WORD_TARGETS.keys())
    found_sections: set[str] = set()

    for line in text.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            canonical = _SECTION_TARGET_ALIASES.get(section, section)
            if canonical in required_sections:
                found_sections.add(canonical)

    return {section: section in found_sections for section in required_sections}
