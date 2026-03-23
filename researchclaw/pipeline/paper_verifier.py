"""Paper quality verification — anti-fabrication and completeness checks."""

from __future__ import annotations

import re
from typing import Any

from researchclaw.prompts import SECTION_WORD_TARGETS, _SECTION_TARGET_ALIASES
from researchclaw.quality import assess_quality


def verify_paper(text: str) -> dict[str, Any]:
    """Run comprehensive quality checks on a paper draft."""
    results: dict[str, Any] = {}

    # 1. Template content detection
    quality = assess_quality(text)
    results["template_check"] = {
        "passed": not quality.has_template_content,
        "template_ratio": quality.template_ratio,
        "match_count": quality.match_count,
    }

    # 2. Section completeness
    results["sections"] = _check_sections(text)

    # 3. Word count per section
    results["word_counts"] = _count_section_words(text)

    # 4. Citation check
    results["citations"] = _check_citations(text)

    # 5. Anti-disclaimer check
    results["disclaimers"] = _check_disclaimers(text)

    # Overall
    all_passed = all([
        results["template_check"]["passed"],
        all(results["sections"].values()),
        not results["disclaimers"]["found"],
    ])
    results["overall_passed"] = all_passed

    return results


def _check_sections(text: str) -> dict[str, bool]:
    """Check if all required sections are present."""
    required = set(SECTION_WORD_TARGETS.keys())
    found: set[str] = set()

    for line in text.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            heading = re.sub(r"^#+\s*", "", line).strip().lower()
            canonical = _SECTION_TARGET_ALIASES.get(heading, heading)
            if canonical in required:
                found.add(canonical)

    return {section: section in found for section in sorted(required)}


def _count_section_words(text: str) -> dict[str, int]:
    """Count words in each section."""
    sections: dict[str, int] = {}
    current_section = ""
    current_words = 0

    for line in text.split("\n"):
        if line.startswith("## ") or (line.startswith("# ") and not line.startswith("## ")):
            if current_section:
                sections[current_section] = current_words
            heading = re.sub(r"^#+\s*", "", line).strip().lower()
            current_section = _SECTION_TARGET_ALIASES.get(heading, heading)
            current_words = 0
        else:
            current_words += len(line.split())

    if current_section:
        sections[current_section] = current_words

    return sections


def _check_citations(text: str) -> dict[str, Any]:
    """Check citation usage in the paper."""
    cite_pattern = r"\\cite\{([^}]+)\}"
    matches = re.findall(cite_pattern, text)
    all_keys: set[str] = set()
    for group in matches:
        for key in group.split(","):
            all_keys.add(key.strip())

    return {
        "total_citations": len(all_keys),
        "citation_keys": sorted(all_keys),
    }


def _check_disclaimers(text: str) -> dict[str, Any]:
    """Check for AI disclaimers in the text."""
    disclaimer_patterns = [
        r"(?i)as an ai",
        r"(?i)i am an ai",
        r"(?i)as a language model",
        r"(?i)i cannot",
        r"(?i)i don't have access",
        r"(?i)i'm not able to",
    ]

    found = []
    for pattern in disclaimer_patterns:
        matches = re.findall(pattern, text)
        found.extend(matches)

    return {"found": bool(found), "examples": found[:5]}
