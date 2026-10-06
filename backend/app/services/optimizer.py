from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    Application,
    CandidateProfileRecord,
    GenerationEvent,
    ResumeArtifact,
)
from app.schemas.cv import CandidateProfile, JobProfile, ProjectLink
from app.schemas.resume import GeneratedResume, ResumeLink
from app.services.ats_validator import validate as deterministic_ats_validate
from app.services.llm import evaluate_ats, generate_resume
from app.services.prompt_engine import build_optimization_prompt
from app.services.semantic_matcher import semantic_job_match
from app.services.generation_service import _apply_github_repository_evidence, _apply_link_evidence, _contact_line_from_evidence, _restore_project_links


def _hybrid_evaluate(job, candidate, resume):
    resume_eval = resume.model_dump()
    ats = evaluate_ats(
        job.model_dump(),
        resume_eval,
        candidate.model_dump(exclude={"raw_text"}),
    )
    gemini_score = float(ats.get("score", 0) or 0)

    semantic = None
    try:
        semantic = semantic_job_match(job.model_dump(), resume_eval)
    except Exception:
        semantic = None

    deterministic = deterministic_ats_validate(resume, job, candidate)
    semantic_score = float(semantic.get("overall", deterministic["score"])) if semantic else float(deterministic["score"])

    hybrid = round(
        0.55 * gemini_score
        + 0.30 * semantic_score
        + 0.15 * float(deterministic["score"]),
        1,
    )

    ats["gemini_score"] = round(gemini_score, 1)
    ats["semantic_match_score"] = round(semantic_score, 1)
    ats["semantic_skill_score"] = semantic.get("skills") if semantic else None
    ats["semantic_responsibility_score"] = semantic.get("responsibilities") if semantic else None
    ats["deterministic_score"] = deterministic["score"]
    ats["deterministic_checks"] = {
        "keyword_coverage": deterministic["keyword_coverage"],
        "section_score": deterministic["section_score"],
        "link_coverage": deterministic["link_coverage"],
        "warnings": deterministic["warnings"],
    }
    ats["score"] = hybrid
    return ats


def optimize_resume(
    db: Session,
    application: Application,
    current_artifact: ResumeArtifact,
    target_score: float = 85.0,
    max_iterations: int = 2,
):
    max_iterations = max(1, min(2, int(max_iterations)))
    target_score = max(60.0, min(95.0, float(target_score)))

    job = JobProfile.model_validate(application.job_json)

    if application.candidate_profile_id:
        profile = (
            db.query(CandidateProfileRecord)
            .filter_by(
                id=application.candidate_profile_id,
                user_id=application.user_id,
            )
            .first()
        )
        if not profile:
            raise ValueError("Candidate profile not found.")
        candidate = CandidateProfile.model_validate(profile.profile_json)
    else:
        candidate = CandidateProfile.model_validate(application.candidate_json or {})

    _apply_github_repository_evidence(candidate)

    current_resume = GeneratedResume.model_validate(current_artifact.resume_json)
    current_ats = current_artifact.ats_json or {}
    best_score = float(current_ats.get("score", 0) or 0)
    best_resume = current_resume
    best_ats = current_ats
    iterations = 0

    if best_score >= target_score:
        return current_artifact, {
            "target_score": target_score,
            "before_score": best_score,
            "after_score": best_score,
            "iterations": 0,
            "improved": False,
            "reason": "Already above target.",
        }

    for iteration in range(1, max_iterations + 1):
        iterations = iteration
        prompt = build_optimization_prompt(
            job.model_dump(),
            candidate.model_dump(exclude={"raw_text"}),
            best_resume.model_dump(),
            best_ats,
        )
        raw = generate_resume(prompt)
        revised = GeneratedResume.model_validate(raw)

        revised.contact_line = _contact_line_from_evidence(
            candidate,
            revised.contact_line,
        )
        _restore_project_links(revised, candidate)
        revised.professional_links = [
            ResumeLink(label="LinkedIn", url=candidate.contact.linkedin),
            ResumeLink(label="GitHub", url=candidate.contact.github),
            ResumeLink(label="Portfolio", url=candidate.contact.portfolio),
        ]
        revised.professional_links = [x for x in revised.professional_links if x.url]

        revised_ats = _hybrid_evaluate(job, candidate, revised)
        revised_score = float(revised_ats.get("score", 0) or 0)

        if revised_score > best_score:
            best_resume = revised
            best_ats = revised_ats
            best_score = revised_score

        if best_score >= target_score:
            break

    if best_score <= float(current_ats.get("score", 0) or 0):
        return current_artifact, {
            "target_score": target_score,
            "before_score": float(current_ats.get("score", 0) or 0),
            "after_score": float(current_ats.get("score", 0) or 0),
            "iterations": iterations,
            "improved": False,
            "reason": "No truthful revision improved the measured score.",
        }

    options = (
        current_artifact.resume_json.get("_render_options", {})
        if isinstance(current_artifact.resume_json, dict)
        else {}
    )
    resume_payload = best_resume.model_dump()
    resume_payload["_render_options"] = options

    before_score = float(current_ats.get("score", 0) or 0)
    best_ats["optimization"] = {
        "target_score": target_score,
        "before_score": before_score,
        "after_score": best_score,
        "iterations": iterations,
        "improved": True,
        "reason": "Targeted evidence-preserving AI optimization.",
    }

    new_artifact = ResumeArtifact(
        application_id=current_artifact.application_id,
        version=current_artifact.version + 1,
        resume_json=resume_payload,
        ats_json=best_ats,
        prompt_version_id=current_artifact.prompt_version_id,
        prompt_key=current_artifact.prompt_key,
        template_key=current_artifact.template_key,
    )
    db.add(new_artifact)
    db.flush()

    return new_artifact, best_ats["optimization"]
