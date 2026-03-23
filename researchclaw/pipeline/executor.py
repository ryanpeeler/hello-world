"""Stage executor — dispatches each pipeline stage to its implementation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.pipeline.stages import Stage

logger = logging.getLogger(__name__)


def execute_stage(
    *,
    stage: Stage,
    run_dir: Path,
    run_id: str,
    config: RCConfig,
    adapters: AdapterBundle,
    kb_root: Path | None = None,
) -> dict[str, Any]:
    """Execute a single pipeline stage and return its result dict."""

    stage_dir = run_dir / f"stage_{int(stage):02d}_{stage.name.lower()}"
    stage_dir.mkdir(parents=True, exist_ok=True)

    from researchclaw.llm import create_llm_client
    from researchclaw.prompts import PromptManager

    llm = create_llm_client(config)
    pm = PromptManager()

    dispatch: dict[Stage, Any] = {
        Stage.TOPIC_INIT: _exec_topic_init,
        Stage.PROBLEM_DECOMPOSE: _exec_problem_decompose,
        Stage.SEARCH_STRATEGY: _exec_search_strategy,
        Stage.LITERATURE_COLLECT: _exec_literature_collect,
        Stage.LITERATURE_SCREEN: _exec_literature_screen,
        Stage.KNOWLEDGE_EXTRACT: _exec_knowledge_extract,
        Stage.SYNTHESIS: _exec_synthesis,
        Stage.HYPOTHESIS_GEN: _exec_hypothesis_gen,
        Stage.EXPERIMENT_DESIGN: _exec_experiment_design,
        Stage.CODE_GENERATION: _exec_code_generation,
        Stage.RESOURCE_PLANNING: _exec_resource_planning,
        Stage.EXPERIMENT_RUN: _exec_experiment_run,
        Stage.ITERATIVE_REFINE: _exec_iterative_refine,
        Stage.RESULT_ANALYSIS: _exec_result_analysis,
        Stage.RESEARCH_DECISION: _exec_research_decision,
        Stage.PAPER_OUTLINE: _exec_paper_outline,
        Stage.PAPER_DRAFT: _exec_paper_draft,
        Stage.PEER_REVIEW: _exec_peer_review,
        Stage.PAPER_REVISION: _exec_paper_revision,
        Stage.QUALITY_GATE: _exec_quality_gate,
        Stage.KNOWLEDGE_ARCHIVE: _exec_knowledge_archive,
        Stage.EXPORT_PUBLISH: _exec_export_publish,
        Stage.CITATION_VERIFY: _exec_citation_verify,
    }

    handler = dispatch.get(stage)
    if handler is None:
        raise ValueError(f"No handler for stage {stage.name}")

    return handler(
        run_dir=run_dir,
        stage_dir=stage_dir,
        config=config,
        llm=llm,
        pm=pm,
        adapters=adapters,
        kb_root=kb_root,
    )


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------


def _llm_call(llm: Any, pm: Any, stage_name: str, run_dir: Path, **kwargs: Any) -> str:
    """Helper: call LLM with stage prompt and write output."""
    prompt = pm.for_stage(stage_name, **kwargs)
    resp = llm.chat(
        [{"role": "user", "content": prompt.user}],
        system=prompt.system,
        json_mode=prompt.json_mode,
        max_tokens=prompt.max_tokens,
        strip_thinking=True,
    )
    return resp.content


def _write_artifact(run_dir: Path, name: str, content: str) -> Path:
    """Write an artifact file."""
    path = run_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _exec_topic_init(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 1: Topic initialization — generate SMART goal."""
    from researchclaw.hardware import detect_hardware

    hw = detect_hardware()
    _write_artifact(run_dir, "hardware_profile.json", json.dumps(hw.to_dict(), indent=2))

    content = _llm_call(
        llm, pm, "topic_init", run_dir,
        topic=config.research.topic,
        domains=", ".join(config.research.domains),
        hardware_tier=hw.tier,
        hardware_warning=hw.warning,
    )
    _write_artifact(run_dir, "goal.md", content)
    return {"goal": content, "hardware": hw.to_dict()}


def _exec_problem_decompose(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 2: Problem decomposition."""
    goal = (run_dir / "goal.md").read_text(encoding="utf-8")
    content = _llm_call(llm, pm, "problem_decompose", run_dir, goal=goal, topic=config.research.topic)
    _write_artifact(run_dir, "problem_tree.md", content)
    return {"problem_tree": content}


def _exec_search_strategy(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 3: Search strategy generation."""
    problem_tree = (run_dir / "problem_tree.md").read_text(encoding="utf-8")
    content = _llm_call(
        llm, pm, "search_strategy", run_dir,
        problem_tree=problem_tree, topic=config.research.topic,
        daily_papers=str(config.research.daily_papers),
    )
    _write_artifact(run_dir, "search_plan.yaml", content)
    _write_artifact(run_dir, "sources.json", json.dumps({"sources": ["openalex", "semantic_scholar", "arxiv"]}))
    _write_artifact(run_dir, "queries.json", json.dumps({"queries": [config.research.topic]}))
    return {"search_plan": content}


def _exec_literature_collect(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, adapters: AdapterBundle, **kw: Any) -> dict:
    """Stage 4: Literature collection from multiple sources."""
    from researchclaw.literature.collector import collect_papers

    search_plan_path = run_dir / "search_plan.yaml"
    candidates = collect_papers(
        topic=config.research.topic,
        search_plan_path=search_plan_path,
        max_papers=config.research.daily_papers,
    )

    candidates_path = run_dir / "candidates.jsonl"
    with candidates_path.open("w", encoding="utf-8") as f:
        for paper in candidates:
            f.write(json.dumps(paper) + "\n")

    return {"candidates_count": len(candidates)}


def _exec_literature_screen(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 5: Literature screening (GATE)."""
    candidates_path = run_dir / "candidates.jsonl"
    candidates = []
    if candidates_path.exists():
        for line in candidates_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                candidates.append(json.loads(line))

    content = _llm_call(
        llm, pm, "literature_screen", run_dir,
        candidates=json.dumps(candidates[:20], indent=2),
        topic=config.research.topic,
    )

    shortlist_path = run_dir / "shortlist.jsonl"
    # Parse LLM response for selected papers, or write all candidates as shortlist
    try:
        selected = json.loads(content)
        if isinstance(selected, list):
            with shortlist_path.open("w", encoding="utf-8") as f:
                for paper in selected:
                    f.write(json.dumps(paper) + "\n")
        else:
            shortlist_path.write_text(content, encoding="utf-8")
    except json.JSONDecodeError:
        with shortlist_path.open("w", encoding="utf-8") as f:
            for paper in candidates:
                f.write(json.dumps(paper) + "\n")

    return {"shortlist_count": len(candidates)}


def _exec_knowledge_extract(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 6: Knowledge extraction from shortlisted papers."""
    shortlist_path = run_dir / "shortlist.jsonl"
    papers = []
    if shortlist_path.exists():
        for line in shortlist_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                papers.append(json.loads(line))

    cards_dir = run_dir / "cards"
    cards_dir.mkdir(exist_ok=True)

    for i, paper in enumerate(papers):
        title = paper.get("title", f"paper_{i}")
        content = _llm_call(
            llm, pm, "knowledge_extract", run_dir,
            paper=json.dumps(paper, indent=2), topic=config.research.topic,
        )
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in title[:60])
        _write_artifact(run_dir, f"cards/{safe_name}.md", content)

    return {"cards_count": len(papers)}


def _exec_synthesis(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 7: Knowledge synthesis."""
    cards_dir = run_dir / "cards"
    cards_text = ""
    if cards_dir.exists():
        for card_file in sorted(cards_dir.glob("*.md")):
            cards_text += f"\n## {card_file.stem}\n{card_file.read_text(encoding='utf-8')}\n"

    content = _llm_call(llm, pm, "synthesis", run_dir, cards=cards_text, topic=config.research.topic)
    _write_artifact(run_dir, "synthesis.md", content)
    return {"synthesis": content}


def _exec_hypothesis_gen(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 8: Hypothesis generation."""
    synthesis = (run_dir / "synthesis.md").read_text(encoding="utf-8")
    content = _llm_call(llm, pm, "hypothesis_gen", run_dir, synthesis=synthesis, topic=config.research.topic)
    _write_artifact(run_dir, "hypotheses.md", content)
    return {"hypotheses": content}


def _exec_experiment_design(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 9: Experiment design (GATE)."""
    hypotheses = (run_dir / "hypotheses.md").read_text(encoding="utf-8")
    hw_path = run_dir / "hardware_profile.json"
    hw_info = hw_path.read_text(encoding="utf-8") if hw_path.exists() else "{}"

    content = _llm_call(
        llm, pm, "experiment_design", run_dir,
        hypotheses=hypotheses, topic=config.research.topic,
        hardware=hw_info,
    )
    _write_artifact(run_dir, "exp_plan.yaml", content)
    return {"exp_plan": content}


def _exec_code_generation(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 10: Code generation for experiments."""
    exp_plan = (run_dir / "exp_plan.yaml").read_text(encoding="utf-8")
    hw_path = run_dir / "hardware_profile.json"
    hw_info = hw_path.read_text(encoding="utf-8") if hw_path.exists() else "{}"

    content = _llm_call(
        llm, pm, "code_generation", run_dir,
        exp_plan=exp_plan, topic=config.research.topic,
        hardware=hw_info,
    )

    experiment_dir = run_dir / "experiment"
    experiment_dir.mkdir(exist_ok=True)
    _write_artifact(run_dir, "experiment/run_experiment.py", content)
    _write_artifact(run_dir, "experiment_spec.md", f"# Experiment Specification\n\n{exp_plan}")
    return {"code": content}


def _exec_resource_planning(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 11: Resource planning."""
    exp_plan = (run_dir / "exp_plan.yaml").read_text(encoding="utf-8")
    content = _llm_call(llm, pm, "resource_planning", run_dir, exp_plan=exp_plan)

    try:
        schedule = json.loads(content)
    except json.JSONDecodeError:
        schedule = {"runs": [{"name": "main", "estimated_time_sec": 300}]}

    _write_artifact(run_dir, "schedule.json", json.dumps(schedule, indent=2))
    return {"schedule": schedule}


def _exec_experiment_run(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 12: Execute experiments."""
    from researchclaw.experiment.sandbox import run_sandbox_experiment

    experiment_dir = run_dir / "experiment"
    runs_dir = run_dir / "runs"
    runs_dir.mkdir(exist_ok=True)

    results = run_sandbox_experiment(
        experiment_dir=experiment_dir,
        runs_dir=runs_dir,
        config=config,
    )
    return {"runs": results}


def _exec_iterative_refine(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 13: Iterative refinement."""
    runs_dir = run_dir / "runs"
    refinement_log: list[dict[str, Any]] = []

    max_iterations = config.experiment.sandbox.max_iterations
    for iteration in range(max_iterations):
        # Check if results are satisfactory
        latest_results = ""
        for result_file in sorted(runs_dir.glob("*.json")):
            latest_results += result_file.read_text(encoding="utf-8") + "\n"

        if not latest_results.strip():
            break

        content = _llm_call(
            llm, pm, "iterative_refine", run_dir,
            results=latest_results, iteration=str(iteration + 1),
            max_iterations=str(max_iterations), topic=config.research.topic,
        )

        refinement_log.append({
            "iteration": iteration + 1,
            "action": content[:200],
            "converged": "converged" in content.lower() or "satisfactory" in content.lower(),
        })

        if refinement_log[-1]["converged"]:
            break

    _write_artifact(run_dir, "refinement_log.json", json.dumps(refinement_log, indent=2))

    # Copy final experiment state
    final_dir = run_dir / "experiment_final"
    experiment_dir = run_dir / "experiment"
    if experiment_dir.exists():
        import shutil
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.copytree(experiment_dir, final_dir)

    return {"iterations": len(refinement_log), "converged": bool(refinement_log and refinement_log[-1].get("converged"))}


def _exec_result_analysis(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 14: Result analysis."""
    runs_dir = run_dir / "runs"
    results_text = ""
    for f in sorted(runs_dir.glob("*")) if runs_dir.exists() else []:
        if f.is_file():
            results_text += f"\n## {f.name}\n{f.read_text(encoding='utf-8')}\n"

    content = _llm_call(
        llm, pm, "result_analysis", run_dir,
        results=results_text, topic=config.research.topic,
    )
    _write_artifact(run_dir, "analysis.md", content)
    return {"analysis": content}


def _exec_research_decision(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 15: Research decision (PROCEED/REFINE/PIVOT)."""
    analysis = (run_dir / "analysis.md").read_text(encoding="utf-8")
    content = _llm_call(
        llm, pm, "research_decision", run_dir,
        analysis=analysis, topic=config.research.topic,
    )
    _write_artifact(run_dir, "decision.md", content)
    return {"decision": content}


def _exec_paper_outline(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 16: Paper outline."""
    analysis = (run_dir / "analysis.md").read_text(encoding="utf-8") if (run_dir / "analysis.md").exists() else ""
    decision = (run_dir / "decision.md").read_text(encoding="utf-8") if (run_dir / "decision.md").exists() else ""

    content = _llm_call(
        llm, pm, "paper_outline", run_dir,
        analysis=analysis, decision=decision, topic=config.research.topic,
    )
    _write_artifact(run_dir, "outline.md", content)
    return {"outline": content}


def _exec_paper_draft(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 17: Paper draft."""
    outline = (run_dir / "outline.md").read_text(encoding="utf-8")
    analysis = (run_dir / "analysis.md").read_text(encoding="utf-8") if (run_dir / "analysis.md").exists() else ""

    content = _llm_call(
        llm, pm, "paper_draft", run_dir,
        outline=outline, analysis=analysis, topic=config.research.topic,
    )
    _write_artifact(run_dir, "paper_draft.md", content)
    return {"draft": content}


def _exec_peer_review(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 18: Simulated peer review."""
    draft = (run_dir / "paper_draft.md").read_text(encoding="utf-8")
    content = _llm_call(llm, pm, "peer_review", run_dir, draft=draft, topic=config.research.topic)
    _write_artifact(run_dir, "reviews.md", content)
    return {"reviews": content}


def _exec_paper_revision(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 19: Paper revision."""
    draft = (run_dir / "paper_draft.md").read_text(encoding="utf-8")
    reviews = (run_dir / "reviews.md").read_text(encoding="utf-8")
    content = _llm_call(
        llm, pm, "paper_revision", run_dir,
        draft=draft, reviews=reviews, topic=config.research.topic,
    )
    _write_artifact(run_dir, "paper_revised.md", content)
    return {"revised": content}


def _exec_quality_gate(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 20: Quality gate (GATE)."""
    from researchclaw.quality import assess_quality

    revised_path = run_dir / "paper_revised.md"
    text = revised_path.read_text(encoding="utf-8") if revised_path.exists() else ""
    report = assess_quality(text)

    quality_data = report.to_dict()
    quality_data["passed"] = not report.has_template_content
    _write_artifact(run_dir, "quality_report.json", json.dumps(quality_data, indent=2))
    return quality_data


def _exec_knowledge_archive(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, kb_root: Path | None = None, **kw: Any) -> dict:
    """Stage 21: Knowledge archival."""
    content = _llm_call(
        llm, pm, "knowledge_archive", run_dir,
        topic=config.research.topic,
    )
    _write_artifact(run_dir, "archive.md", content)

    bundle_index = {
        "run_dir": str(run_dir),
        "topic": config.research.topic,
        "artifacts": [str(p.relative_to(run_dir)) for p in run_dir.rglob("*") if p.is_file()],
    }
    _write_artifact(run_dir, "bundle_index.json", json.dumps(bundle_index, indent=2))

    # Copy to knowledge base if configured
    if kb_root:
        kb_root.mkdir(parents=True, exist_ok=True)
        archive_dest = kb_root / f"{run_dir.name}_archive.md"
        archive_dest.write_text(content, encoding="utf-8")

    return {"archived": True}


def _exec_export_publish(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, **kw: Any) -> dict:
    """Stage 22: Export and publish."""
    from researchclaw.export.latex import convert_to_latex

    revised_path = run_dir / "paper_revised.md"
    if not revised_path.exists():
        revised_path = run_dir / "paper_draft.md"

    paper_text = revised_path.read_text(encoding="utf-8") if revised_path.exists() else ""

    # Write final markdown
    _write_artifact(run_dir, "paper_final.md", paper_text)

    # Generate LaTeX
    latex_content = convert_to_latex(paper_text, template=config.export.format)
    _write_artifact(run_dir, "paper.tex", latex_content)

    # Generate BibTeX
    bib_content = _llm_call(
        llm, pm, "export_bibtex", run_dir,
        paper=paper_text, topic=config.research.topic,
    )
    _write_artifact(run_dir, "references.bib", bib_content)

    # Copy experiment code
    code_dir = run_dir / "code"
    code_dir.mkdir(exist_ok=True)
    experiment_dir = run_dir / "experiment_final"
    if not experiment_dir.exists():
        experiment_dir = run_dir / "experiment"
    if experiment_dir.exists():
        import shutil
        shutil.copytree(experiment_dir, code_dir, dirs_exist_ok=True)

    return {"exported": True, "format": config.export.format}


def _exec_citation_verify(*, run_dir: Path, config: RCConfig, llm: Any, pm: Any, adapters: AdapterBundle, **kw: Any) -> dict:
    """Stage 23: Citation verification."""
    from researchclaw.literature.citation_verifier import verify_citations

    paper_path = run_dir / "paper_final.md"
    bib_path = run_dir / "references.bib"

    paper_text = paper_path.read_text(encoding="utf-8") if paper_path.exists() else ""
    bib_text = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""

    report = verify_citations(paper_text, bib_text, web_fetch=adapters.web_fetch)

    _write_artifact(run_dir, "verification_report.json", json.dumps(report, indent=2))

    # Write verified BibTeX
    verified_bib = report.get("verified_bib", bib_text)
    _write_artifact(run_dir, "references_verified.bib", verified_bib)

    return report
