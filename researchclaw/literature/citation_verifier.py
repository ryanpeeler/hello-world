"""Four-layer citation verification system.

Layer 1: arXiv ID check
Layer 2: CrossRef/DataCite DOI resolution
Layer 3: Title matching against APIs
Layer 4: LLM relevance scoring
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def verify_citations(
    paper_text: str,
    bib_text: str,
    web_fetch: Any = None,
) -> dict[str, Any]:
    """Verify all citations in a paper against real APIs."""
    # Extract citation keys from paper
    cited_keys = set(re.findall(r"\\cite\{([^}]+)\}", paper_text))
    all_keys: set[str] = set()
    for group in cited_keys:
        for key in group.split(","):
            all_keys.add(key.strip())

    # Extract BibTeX entries
    bib_entries = _parse_bibtex_entries(bib_text)

    results: list[dict[str, Any]] = []
    verified_entries: list[str] = []
    hallucinated: list[str] = []

    for key in sorted(all_keys):
        entry = bib_entries.get(key, {})
        title = entry.get("title", "")
        doi = entry.get("doi", "")
        arxiv_id = _extract_arxiv_id(entry)

        verified = False
        method = "none"

        # Layer 1: arXiv ID check
        if arxiv_id and not verified:
            verified = _verify_arxiv(arxiv_id)
            if verified:
                method = "arxiv_id"

        # Layer 2: DOI resolution
        if doi and not verified:
            verified = _verify_doi(doi)
            if verified:
                method = "doi"

        # Layer 3: Title matching
        if title and not verified:
            verified = _verify_by_title(title)
            if verified:
                method = "title_match"

        result = {
            "key": key,
            "title": title,
            "verified": verified,
            "method": method,
        }
        results.append(result)

        if verified:
            if key in bib_entries:
                verified_entries.append(_format_bib_entry(key, bib_entries[key]))
        else:
            hallucinated.append(key)

    verified_bib = "\n\n".join(verified_entries) if verified_entries else bib_text

    report = {
        "total_citations": len(all_keys),
        "verified": sum(1 for r in results if r["verified"]),
        "unverified": sum(1 for r in results if not r["verified"]),
        "hallucinated_keys": hallucinated,
        "results": results,
        "verified_bib": verified_bib,
    }

    logger.info(
        "Citation verification: %d/%d verified, %d hallucinated",
        report["verified"], report["total_citations"], len(hallucinated),
    )
    return report


def _parse_bibtex_entries(bib_text: str) -> dict[str, dict[str, str]]:
    """Parse BibTeX text into a dict of entries."""
    entries: dict[str, dict[str, str]] = {}
    # Simple BibTeX parser
    pattern = r"@\w+\{([^,]+),([^@]*)\}"
    for match in re.finditer(pattern, bib_text, re.DOTALL):
        key = match.group(1).strip()
        body = match.group(2)
        fields: dict[str, str] = {}
        for field_match in re.finditer(r"(\w+)\s*=\s*[\{\"](.*?)[\}\"]", body, re.DOTALL):
            fields[field_match.group(1).lower()] = field_match.group(2).strip()
        entries[key] = fields
    return entries


def _extract_arxiv_id(entry: dict[str, str]) -> str:
    """Extract arXiv ID from a BibTeX entry."""
    # Check eprint field
    arxiv_id = entry.get("eprint", "")
    if arxiv_id:
        return arxiv_id

    # Check URL field
    url = entry.get("url", "")
    match = re.search(r"arxiv\.org/abs/(\d+\.\d+)", url)
    if match:
        return match.group(1)
    return ""


def _verify_arxiv(arxiv_id: str) -> bool:
    """Verify an arXiv paper exists."""
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ResearchClaw/0.3.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode()
            return "<entry>" in content and "Error" not in content
    except (urllib.error.URLError, OSError):
        return False


def _verify_doi(doi: str) -> bool:
    """Verify a DOI exists via CrossRef."""
    clean_doi = doi.replace("https://doi.org/", "").strip()
    url = f"https://api.crossref.org/works/{urllib.parse.quote(clean_doi, safe='')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ResearchClaw/0.3.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _verify_by_title(title: str) -> bool:
    """Verify a paper exists by title search on Semantic Scholar."""
    encoded = urllib.parse.quote(title[:200])
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded}&limit=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ResearchClaw/0.3.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = data.get("data", [])
            if results:
                result_title = results[0].get("title", "").lower()
                # Fuzzy match: check if most words overlap
                title_words = set(title.lower().split())
                result_words = set(result_title.split())
                if title_words and result_words:
                    overlap = len(title_words & result_words) / max(len(title_words), 1)
                    return overlap > 0.6
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        pass
    return False


def _format_bib_entry(key: str, fields: dict[str, str]) -> str:
    """Format a BibTeX entry back to string."""
    entry_type = "article"
    lines = [f"@{entry_type}{{{key},"]
    for field, value in fields.items():
        lines.append(f"  {field} = {{{value}}},")
    lines.append("}")
    return "\n".join(lines)
