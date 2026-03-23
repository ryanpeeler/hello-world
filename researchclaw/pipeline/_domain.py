"""Domain-specific pipeline configuration."""

from __future__ import annotations

from typing import Any

DOMAIN_DEFAULTS: dict[str, dict[str, Any]] = {
    "ml": {
        "search_sources": ["arxiv", "semantic_scholar", "openalex"],
        "categories": ["cs.LG", "cs.AI", "cs.CL", "cs.CV", "stat.ML"],
        "key_venues": ["NeurIPS", "ICML", "ICLR", "AAAI", "CVPR"],
    },
    "nlp": {
        "search_sources": ["arxiv", "semantic_scholar"],
        "categories": ["cs.CL", "cs.AI"],
        "key_venues": ["ACL", "EMNLP", "NAACL", "COLING"],
    },
    "cv": {
        "search_sources": ["arxiv", "semantic_scholar"],
        "categories": ["cs.CV", "cs.AI"],
        "key_venues": ["CVPR", "ICCV", "ECCV"],
    },
    "bio": {
        "search_sources": ["openalex", "semantic_scholar"],
        "categories": ["q-bio", "cs.AI"],
        "key_venues": ["Nature", "Science", "PNAS", "Cell"],
    },
}


def get_domain_config(domain: str) -> dict[str, Any]:
    """Return domain-specific configuration defaults."""
    return DOMAIN_DEFAULTS.get(domain, DOMAIN_DEFAULTS["ml"])
