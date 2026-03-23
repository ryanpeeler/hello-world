"""Multi-source literature collector — OpenAlex, Semantic Scholar, arXiv."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def collect_papers(
    topic: str,
    search_plan_path: Path | None = None,
    max_papers: int = 10,
) -> list[dict[str, Any]]:
    """Collect papers from multiple academic sources."""
    papers: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    # Try each source, gracefully degrade if unavailable
    for source_fn in [_search_openalex, _search_semantic_scholar, _search_arxiv]:
        try:
            results = source_fn(topic, max_papers=max_papers)
            for paper in results:
                title = paper.get("title", "").lower().strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    papers.append(paper)
        except Exception as exc:
            logger.warning("Source %s failed: %s", source_fn.__name__, exc)

    logger.info("Collected %d unique papers for topic: %s", len(papers), topic)
    return papers[:max_papers]


def _search_openalex(topic: str, max_papers: int = 10) -> list[dict[str, Any]]:
    """Search OpenAlex for papers."""
    encoded = urllib.parse.quote(topic)
    url = (
        f"https://api.openalex.org/works?"
        f"search={encoded}&per-page={max_papers}"
        f"&sort=relevance_score:desc"
    )

    req = urllib.request.Request(
        url, headers={"User-Agent": "ResearchClaw/0.3.1 (mailto:research@example.com)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("OpenAlex search failed: %s", exc)
        return []

    papers = []
    for work in data.get("results", []):
        authors = [
            a.get("author", {}).get("display_name", "Unknown")
            for a in work.get("authorships", [])[:5]
        ]
        papers.append({
            "source": "openalex",
            "title": work.get("title", ""),
            "authors": authors,
            "year": work.get("publication_year"),
            "doi": work.get("doi", ""),
            "url": work.get("id", ""),
            "cited_by_count": work.get("cited_by_count", 0),
            "abstract": (work.get("abstract_inverted_index") or {}).__class__.__name__,
        })
    return papers


def _search_semantic_scholar(topic: str, max_papers: int = 10) -> list[dict[str, Any]]:
    """Search Semantic Scholar for papers."""
    encoded = urllib.parse.quote(topic)
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search?"
        f"query={encoded}&limit={max_papers}"
        f"&fields=title,authors,year,citationCount,externalIds,abstract,venue"
    )

    req = urllib.request.Request(url, headers={"User-Agent": "ResearchClaw/0.3.1"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("Semantic Scholar search failed: %s", exc)
        return []

    papers = []
    for paper_data in data.get("data", []):
        authors = [a.get("name", "Unknown") for a in paper_data.get("authors", [])[:5]]
        ext_ids = paper_data.get("externalIds", {}) or {}
        papers.append({
            "source": "semantic_scholar",
            "title": paper_data.get("title", ""),
            "authors": authors,
            "year": paper_data.get("year"),
            "doi": ext_ids.get("DOI", ""),
            "arxiv_id": ext_ids.get("ArXiv", ""),
            "cited_by_count": paper_data.get("citationCount", 0),
            "venue": paper_data.get("venue", ""),
            "abstract": (paper_data.get("abstract") or "")[:500],
        })
    return papers


def _search_arxiv(topic: str, max_papers: int = 10) -> list[dict[str, Any]]:
    """Search arXiv for papers."""
    try:
        import arxiv
    except ImportError:
        logger.warning("arxiv package not installed, skipping arXiv search")
        return []

    try:
        search = arxiv.Search(
            query=topic,
            max_results=max_papers,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        papers = []
        for result in search.results():
            papers.append({
                "source": "arxiv",
                "title": result.title,
                "authors": [a.name for a in result.authors[:5]],
                "year": result.published.year if result.published else None,
                "arxiv_id": result.entry_id.split("/")[-1] if result.entry_id else "",
                "url": result.entry_id or "",
                "abstract": (result.summary or "")[:500],
                "categories": list(result.categories) if result.categories else [],
            })
        return papers
    except Exception as exc:
        logger.warning("arXiv search failed: %s", exc)
        return []
