"""Prompt externalization for the ResearchClaw pipeline.

All 23 stage prompts are defined here as defaults and can be overridden
via a user-provided YAML file.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _render(template: str, variables: dict[str, str]) -> str:
    """Replace ``{var_name}`` placeholders with *variables* values."""

    def _replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(variables[key]) if key in variables else match.group(0)

    return re.sub(r"\{(\w+)\}", _replacer, template)


@dataclass(frozen=True)
class RenderedPrompt:
    """Fully rendered prompt ready for ``llm.chat()``."""
    system: str
    user: str
    json_mode: bool = False
    max_tokens: int | None = None


SECTION_WORD_TARGETS: dict[str, tuple[int, int]] = {
    "abstract": (180, 220),
    "introduction": (800, 1000),
    "related work": (600, 800),
    "method": (1000, 1500),
    "experiments": (800, 1200),
    "results": (600, 800),
    "discussion": (400, 600),
    "limitations": (200, 300),
    "conclusion": (200, 300),
    "broader impact": (200, 400),
}

_SECTION_TARGET_ALIASES: dict[str, str] = {
    "methods": "method",
    "methodology": "method",
    "proposed method": "method",
    "approach": "method",
    "experimental setup": "experiments",
    "experimental results": "results",
    "results and discussion": "results",
    "results and analysis": "results",
    "conclusions": "conclusion",
    "conclusion and future work": "conclusion",
    "summary": "conclusion",
    "background": "related work",
    "literature review": "related work",
    "prior work": "related work",
    "limitation": "limitations",
    "limitations and future work": "limitations",
    "broader impacts": "broader impact",
    "societal impact": "broader impact",
    "ethical considerations": "broader impact",
}

# ---------------------------------------------------------------------------
# Default prompts
# ---------------------------------------------------------------------------

_DEFAULT_BLOCKS: dict[str, str] = {
    "topic_constraint": (
        "Stay strictly within the research topic: {topic}. "
        "Do not deviate to unrelated areas."
    ),
    "compute_budget": (
        "Hardware tier: {hardware_tier}. {hardware_warning} "
        "Design experiments that fit within these constraints."
    ),
    "anti_fabrication": (
        "CRITICAL: Do NOT fabricate citations, results, or data. "
        "Only reference papers you have evidence for. "
        "If unsure, explicitly state the limitation."
    ),
    "anti_disclaimer": (
        "Do NOT include disclaimers like 'As an AI' or 'I cannot'. "
        "Write as a researcher presenting findings."
    ),
}

_DEFAULT_SUB_PROMPTS: dict[str, dict[str, Any]] = {
    "code_repair": {
        "system": "You are an expert Python debugging assistant.",
        "user": (
            "The following experiment code failed with this error:\n\n"
            "```\n{error}\n```\n\n"
            "Original code:\n```python\n{code}\n```\n\n"
            "Fix the code. Return ONLY the corrected Python code, no explanation."
        ),
    },
    "hypothesis_debate": {
        "system": "You are a critical research reviewer.",
        "user": (
            "Evaluate these hypotheses for the topic '{topic}':\n\n"
            "{hypotheses}\n\n"
            "For each hypothesis, provide:\n"
            "1. Strengths\n2. Weaknesses\n3. Testability score (1-10)\n"
            "4. Recommendation: KEEP, MODIFY, or DROP"
        ),
    },
}

_DEFAULT_STAGES: dict[str, dict[str, Any]] = {
    "topic_init": {
        "system": (
            "You are an expert research planner. Generate a SMART research goal "
            "statement. Consider the hardware capabilities available."
        ),
        "user": (
            "Research topic: {topic}\n"
            "Domains: {domains}\n"
            "Hardware: {hardware_tier} ({hardware_warning})\n\n"
            "Generate a SMART (Specific, Measurable, Achievable, Relevant, Time-bound) "
            "research goal. Include:\n"
            "1. Clear problem statement\n"
            "2. Specific objectives\n"
            "3. Expected contributions\n"
            "4. Scope constraints based on available hardware\n"
            "5. Success criteria"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "problem_decompose": {
        "system": "You are an expert at breaking down research problems into sub-questions.",
        "user": (
            "Research goal:\n{goal}\n\n"
            "Topic: {topic}\n\n"
            "Decompose this into >=3 prioritized research sub-questions. "
            "For each sub-question:\n"
            "1. State the question clearly\n"
            "2. Explain why it matters\n"
            "3. Identify what evidence would answer it\n"
            "4. Assign priority (High/Medium/Low)"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "search_strategy": {
        "system": "You are a research librarian expert in academic paper discovery.",
        "user": (
            "Problem tree:\n{problem_tree}\n\n"
            "Topic: {topic}\n"
            "Target papers per day: {daily_papers}\n\n"
            "Create a search strategy in YAML format with:\n"
            "- search_queries: list of specific search queries\n"
            "- sources: [openalex, semantic_scholar, arxiv]\n"
            "- inclusion_criteria: what makes a paper relevant\n"
            "- exclusion_criteria: what to filter out\n"
            "- date_range: preferred publication years"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "literature_screen": {
        "system": (
            "You are a systematic review expert. Screen papers for relevance and quality."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Candidate papers:\n{candidates}\n\n"
            "Screen each paper. Return a JSON array of papers that pass both:\n"
            "1. Relevance: directly related to the topic\n"
            "2. Quality: published in reputable venue or has significant citations\n\n"
            "For each selected paper, include: title, authors, year, venue, relevance_score (1-10)."
        ),
        "json_mode": True,
        "max_tokens": 4096,
    },
    "knowledge_extract": {
        "system": "You are a research analyst creating structured knowledge cards.",
        "user": (
            "Topic: {topic}\n\n"
            "Paper:\n{paper}\n\n"
            "Create a knowledge card with:\n"
            "- Key findings\n"
            "- Methods used\n"
            "- Datasets and benchmarks\n"
            "- Limitations noted\n"
            "- How this relates to our topic\n"
            "- Potential gaps this paper reveals"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "synthesis": {
        "system": "You are a research synthesizer identifying patterns across papers.",
        "user": (
            "Topic: {topic}\n\n"
            "Knowledge cards:\n{cards}\n\n"
            "Synthesize the literature:\n"
            "1. Identify major theme clusters\n"
            "2. Map methodological approaches\n"
            "3. Identify >=2 research gaps\n"
            "4. Note conflicting findings\n"
            "5. Summarize the state of the art"
        ),
        "json_mode": False,
        "max_tokens": 4096,
    },
    "hypothesis_gen": {
        "system": "You are a creative research scientist generating testable hypotheses.",
        "user": (
            "Topic: {topic}\n\n"
            "Synthesis:\n{synthesis}\n\n"
            "Generate >=2 falsifiable research hypotheses:\n"
            "For each:\n"
            "1. State the hypothesis clearly\n"
            "2. Explain the theoretical basis\n"
            "3. Describe how to test it\n"
            "4. Predict expected outcomes\n"
            "5. Identify potential confounds"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "experiment_design": {
        "system": "You are an experimental methodology expert.",
        "user": (
            "Topic: {topic}\n\n"
            "Hypotheses:\n{hypotheses}\n\n"
            "Hardware:\n{hardware}\n\n"
            "Design experiments in YAML format:\n"
            "- baselines: list of baseline methods\n"
            "- proposed_method: description\n"
            "- ablations: what to ablate\n"
            "- metrics: evaluation metrics\n"
            "- datasets: what data to use\n"
            "- hyperparameters: key settings\n"
            "- expected_runtime: estimate"
        ),
        "json_mode": False,
        "max_tokens": 4096,
    },
    "code_generation": {
        "system": (
            "You are an expert Python ML engineer. Write clean, runnable experiment code. "
            "The code must be self-contained and produce numeric results to stdout."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Experiment plan:\n{exp_plan}\n\n"
            "Hardware:\n{hardware}\n\n"
            "Write a complete Python experiment script that:\n"
            "1. Implements the proposed method and baselines\n"
            "2. Runs all experiments\n"
            "3. Prints results as 'metric_name: value' lines\n"
            "4. Handles the available hardware (CPU/GPU)\n"
            "5. Uses only standard ML libraries (numpy, sklearn, scipy, torch)\n\n"
            "Return ONLY the Python code."
        ),
        "json_mode": False,
        "max_tokens": 8192,
    },
    "resource_planning": {
        "system": "You are a compute resource planner.",
        "user": (
            "Experiment plan:\n{exp_plan}\n\n"
            "Create a JSON resource schedule with:\n"
            "- runs: array of {{name, estimated_time_sec, gpu_required, memory_mb}}\n"
            "- total_estimated_time_sec\n"
            "- parallelizable: boolean"
        ),
        "json_mode": True,
        "max_tokens": 1024,
    },
    "iterative_refine": {
        "system": "You are an experiment optimization expert.",
        "user": (
            "Topic: {topic}\n"
            "Iteration: {iteration}/{max_iterations}\n\n"
            "Current results:\n{results}\n\n"
            "Analyze the results and decide:\n"
            "1. Are results satisfactory? (say 'converged' if yes)\n"
            "2. What specific changes would improve results?\n"
            "3. What hyperparameters should be adjusted?"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "result_analysis": {
        "system": "You are a statistical analysis expert for ML experiments.",
        "user": (
            "Topic: {topic}\n\n"
            "Experiment results:\n{results}\n\n"
            "Provide a thorough analysis:\n"
            "1. Summary statistics for all metrics\n"
            "2. Comparison of proposed method vs baselines\n"
            "3. Statistical significance assessment\n"
            "4. Key findings and insights\n"
            "5. Limitations of the experiments"
        ),
        "json_mode": False,
        "max_tokens": 4096,
    },
    "research_decision": {
        "system": (
            "You are a research director making evidence-based decisions. "
            "You must choose: PROCEED (results are good), REFINE (tweak experiments), "
            "or PIVOT (new direction needed)."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Analysis:\n{analysis}\n\n"
            "Make a decision:\n"
            "1. State your decision: PROCEED, REFINE, or PIVOT\n"
            "2. Provide evidence-based justification\n"
            "3. If REFINE: specify what to change\n"
            "4. If PIVOT: specify new direction"
        ),
        "json_mode": False,
        "max_tokens": 2048,
    },
    "paper_outline": {
        "system": "You are an academic paper architect.",
        "user": (
            "Topic: {topic}\n\n"
            "Analysis:\n{analysis}\n\n"
            "Decision:\n{decision}\n\n"
            "Create a detailed paper outline with:\n"
            "- Abstract (180-220 words)\n"
            "- Introduction\n"
            "- Related Work\n"
            "- Method\n"
            "- Experiments\n"
            "- Results\n"
            "- Discussion\n"
            "- Limitations\n"
            "- Conclusion\n\n"
            "For each section, provide bullet points of key content."
        ),
        "json_mode": False,
        "max_tokens": 4096,
    },
    "paper_draft": {
        "system": (
            "You are an expert academic writer. Write a complete research paper. "
            "Do NOT use placeholder text, templates, or TODO markers. "
            "Every section must contain real, substantive content. "
            "Do NOT include disclaimers about being an AI."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Outline:\n{outline}\n\n"
            "Experimental analysis:\n{analysis}\n\n"
            "Write the complete paper (5000-6500 words) with all sections fully written. "
            "Include specific results, methods, and analysis. "
            "Use LaTeX-style citations like \\cite{{author2024}}."
        ),
        "json_mode": False,
        "max_tokens": 16384,
    },
    "peer_review": {
        "system": (
            "You are a conference reviewer providing constructive feedback. "
            "Review from multiple perspectives: methodology, novelty, clarity, significance."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Paper draft:\n{draft}\n\n"
            "Provide reviews from >=2 perspectives:\n"
            "For each reviewer:\n"
            "1. Summary of the paper\n"
            "2. Strengths (>=3)\n"
            "3. Weaknesses (>=3)\n"
            "4. Questions for authors\n"
            "5. Score (1-10) across: novelty, clarity, significance, soundness\n"
            "6. Specific actionable recommendations"
        ),
        "json_mode": False,
        "max_tokens": 8192,
    },
    "paper_revision": {
        "system": (
            "You are the paper's author addressing reviewer feedback. "
            "Revise the paper to address all review comments while maintaining quality."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Original draft:\n{draft}\n\n"
            "Reviews:\n{reviews}\n\n"
            "Revise the paper:\n"
            "1. Address every reviewer comment\n"
            "2. Strengthen weak areas identified\n"
            "3. Add missing details or analysis\n"
            "4. Improve clarity where noted\n"
            "5. Do NOT add placeholder text"
        ),
        "json_mode": False,
        "max_tokens": 16384,
    },
    "knowledge_archive": {
        "system": "You are a research knowledge manager creating retrospectives.",
        "user": (
            "Topic: {topic}\n\n"
            "Create a research retrospective covering:\n"
            "1. Key decisions made and their rationale\n"
            "2. What worked well\n"
            "3. What could be improved\n"
            "4. Lessons learned\n"
            "5. Suggestions for follow-up research\n"
            "6. Reproducibility notes"
        ),
        "json_mode": False,
        "max_tokens": 4096,
    },
    "export_bibtex": {
        "system": (
            "You are a BibTeX expert. Generate valid BibTeX entries. "
            "CRITICAL: Only include citations that appear in the paper. "
            "Do NOT fabricate any references."
        ),
        "user": (
            "Topic: {topic}\n\n"
            "Paper:\n{paper}\n\n"
            "Extract all citations from the paper and generate valid BibTeX entries. "
            "Only include references that are actually cited in the text. "
            "Use standard BibTeX format (@article, @inproceedings, etc.)."
        ),
        "json_mode": False,
        "max_tokens": 4096,
    },
}


class PromptManager:
    """Central registry for pipeline prompts with optional YAML overrides."""

    def __init__(self, overrides_path: str | Path | None = None) -> None:
        self._stages: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _DEFAULT_STAGES.items()
        }
        self._blocks: dict[str, str] = dict(_DEFAULT_BLOCKS)
        self._sub_prompts: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _DEFAULT_SUB_PROMPTS.items()
        }
        if overrides_path:
            self._load_overrides(Path(overrides_path))

    def _load_overrides(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Prompts file not found: %s — using defaults", path)
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            logger.warning("Bad prompts YAML %s: %s — using defaults", path, exc)
            return

        for stage_name, stage_data in (data.get("stages") or {}).items():
            if stage_name in self._stages and isinstance(stage_data, dict):
                self._stages[stage_name].update(stage_data)
            else:
                logger.warning("Unknown stage in prompts file: %s", stage_name)

        for block_name, block_text in (data.get("blocks") or {}).items():
            if isinstance(block_text, str):
                self._blocks[block_name] = block_text

        for sub_name, sub_data in (data.get("sub_prompts") or {}).items():
            if sub_name in self._sub_prompts and isinstance(sub_data, dict):
                self._sub_prompts[sub_name].update(sub_data)

        logger.info("Loaded prompt overrides from %s", path)

    def for_stage(
        self, stage: str, *, evolution_overlay: str = "", **kwargs: Any,
    ) -> RenderedPrompt:
        entry = self._stages[stage]
        kw = {k: str(v) for k, v in kwargs.items()}
        user_text = _render(entry["user"], kw)
        if evolution_overlay:
            user_text = f"{user_text}\n\n{evolution_overlay}"
        return RenderedPrompt(
            system=_render(entry["system"], kw),
            user=user_text,
            json_mode=entry.get("json_mode", False),
            max_tokens=entry.get("max_tokens"),
        )

    def system(self, stage: str) -> str:
        return self._stages[stage]["system"]

    def user(self, stage: str, **kwargs: Any) -> str:
        return _render(self._stages[stage]["user"], {k: str(v) for k, v in kwargs.items()})

    def json_mode(self, stage: str) -> bool:
        return self._stages[stage].get("json_mode", False)

    def max_tokens(self, stage: str) -> int | None:
        return self._stages[stage].get("max_tokens")

    def block(self, name: str, **kwargs: Any) -> str:
        return _render(self._blocks[name], {k: str(v) for k, v in kwargs.items()})

    def sub_prompt(self, name: str, **kwargs: Any) -> RenderedPrompt:
        entry = self._sub_prompts[name]
        kw = {k: str(v) for k, v in kwargs.items()}
        return RenderedPrompt(system=_render(entry["system"], kw), user=_render(entry["user"], kw))

    def stage_names(self) -> list[str]:
        return list(self._stages.keys())

    def has_stage(self, stage: str) -> bool:
        return stage in self._stages

    def export_yaml(self, path: Path) -> None:
        data: dict[str, Any] = {
            "version": "1.0",
            "blocks": dict(self._blocks),
            "stages": {k: dict(v) for k, v in self._stages.items()},
            "sub_prompts": {k: dict(v) for k, v in self._sub_prompts.items()},
        }
        path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, width=120),
            encoding="utf-8",
        )
