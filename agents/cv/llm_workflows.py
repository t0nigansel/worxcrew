from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Tuple

from .llm import OpenAICompatibleClient
from .job_offer import candidate_terms, detect_language
from .models import CVContent, EvidenceSelection, JobAnalysis, SourceBundle
from .prompting import compose_stage_prompt
from .utils import flatten_strings, normalize_text, truncate_text, unique
from .variants import resolve_cv_variant


def _project_by_id(bundle: SourceBundle) -> Dict[str, Dict[str, Any]]:
    return {project["id"]: project for project in bundle.projects}


def _experience_by_id(bundle: SourceBundle) -> Dict[str, Dict[str, Any]]:
    return {experience["id"]: experience for experience in bundle.profile.get("experience", [])}


def _selected_projects(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, Any]]:
    project_map = _project_by_id(bundle)
    return [project_map[project_id] for project_id in selection.selected_project_ids if project_id in project_map]


def _selected_certifications(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, Any]]:
    certifications = {certification["id"]: certification for certification in bundle.certifications}
    return [certifications[cert_id] for cert_id in selection.selected_certification_ids if cert_id in certifications]


def _sanitize_title(value: str, baseline: JobAnalysis, bundle: SourceBundle) -> str | None:
    cleaned = " ".join(value.split()).strip()
    if not cleaned or len(cleaned) > 80:
        return None

    if baseline.raw_text and normalize_text(cleaned) in normalize_text(baseline.raw_text):
        return cleaned

    preferred_roles = bundle.profile.get("notes_for_cv_generation", {}).get("preferred_roles", [])
    allowed_titles = unique([baseline.title, bundle.profile.get("branding", {}).get("headline", ""), *preferred_roles])
    if normalize_text(cleaned) in {normalize_text(item) for item in allowed_titles if item}:
        return cleaned

    return None


def _sanitize_job_terms(values: Iterable[str], bundle: SourceBundle, baseline: JobAnalysis, limit: int) -> List[str]:
    allowed = candidate_terms(bundle)
    allowed_map = {normalize_text(term): term for term in allowed}
    cleaned: List[str] = []
    for value in values:
        normalized = normalize_text(str(value))
        if normalized in allowed_map:
            cleaned.append(allowed_map[normalized])
            continue
        if baseline.raw_text and normalized and normalized in normalize_text(baseline.raw_text):
            cleaned.append(" ".join(str(value).split()).strip())
    return unique(term for term in cleaned if term)[:limit]


def _sanitize_summary(value: str, fallback: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        return fallback
    return truncate_text(cleaned, 180)


def _source_snapshot(bundle: SourceBundle, selection: EvidenceSelection) -> Dict[str, Any]:
    experience_map = _experience_by_id(bundle)
    return {
        "person": {
            "name": bundle.profile.get("person", {}).get("name", {}),
            "contact": bundle.profile.get("person", {}).get("contact", {}),
            "links": bundle.profile.get("person", {}).get("links", {}),
        },
        "branding": bundle.profile.get("branding", {}),
        "selected_experiences": [
            experience_map[experience_id] for experience_id in selection.selected_experience_ids if experience_id in experience_map
        ],
        "selected_projects": _selected_projects(bundle, selection),
        "selected_certifications": _selected_certifications(bundle, selection),
        "education": bundle.profile.get("education", []),
        "skills": bundle.profile.get("skills", {}),
        "availability": bundle.profile.get("availability", {}),
        "work_preferences": bundle.profile.get("work_preferences", {}),
    }


def _allowed_strength_terms(bundle: SourceBundle, analysis: JobAnalysis, selection: EvidenceSelection) -> List[str]:
    allowed = []
    allowed.extend(analysis.keywords)
    allowed.extend(analysis.matched_terms)
    allowed.extend(bundle.profile.get("notes_for_cv_generation", {}).get("positioning_keywords", []))
    allowed.extend(bundle.profile.get("branding", {}).get("focus_areas", []))
    allowed.extend(flatten_strings(bundle.profile.get("skills", {})))
    for project in _selected_projects(bundle, selection):
        allowed.append(project.get("name", ""))
        allowed.append(project.get("role", ""))
        allowed.extend(project.get("tools", []))
    return unique(term for term in allowed if term)


def _allowed_headlines(bundle: SourceBundle, analysis: JobAnalysis) -> List[str]:
    titles = [analysis.title, bundle.profile.get("branding", {}).get("headline", "")]
    titles.extend(bundle.profile.get("notes_for_cv_generation", {}).get("preferred_roles", []))
    return unique(title for title in titles if title)


def _experience_source_scope(bundle: SourceBundle, selection: EvidenceSelection) -> Dict[str, set[str]]:
    scope: Dict[str, set[str]] = {}
    for experience_id in selection.selected_experience_ids:
        scope[experience_id] = {experience_id}
    for project in _selected_projects(bundle, selection):
        experience_id = project.get("related_experience_id")
        if experience_id:
            scope.setdefault(experience_id, {experience_id}).add(project["id"])
    return scope


def _clip_highlight(text: str) -> str:
    return truncate_text(" ".join(text.split()), 140)


def _clip_summary(text: str) -> str:
    return truncate_text(" ".join(text.split()), 240)


def _clip_goal(text: str) -> str:
    return truncate_text(" ".join(text.split()), 140)


def _sanitize_strengths(values: Iterable[str], bundle: SourceBundle, analysis: JobAnalysis, selection: EvidenceSelection) -> List[str]:
    allowed = _allowed_strength_terms(bundle, analysis, selection)
    allowed_map = {normalize_text(term): term for term in allowed}
    cleaned: List[str] = []
    for value in values:
        normalized = normalize_text(str(value))
        if normalized in allowed_map:
            cleaned.append(allowed_map[normalized])
    return unique(cleaned)[:4]


def _sanitize_headline(value: str, bundle: SourceBundle, analysis: JobAnalysis) -> str | None:
    cleaned = " ".join(value.split()).strip()
    if not cleaned or len(cleaned) > 80:
        return None
    allowed = _allowed_headlines(bundle, analysis)
    if normalize_text(cleaned) in {normalize_text(item) for item in allowed}:
        return cleaned
    if analysis.raw_text and normalize_text(cleaned) in normalize_text(analysis.raw_text):
        return cleaned
    return None


def _apply_profile_update(
    content: CVContent,
    payload: Dict[str, Any],
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> List[str]:
    warnings: List[str] = []
    profile = payload.get("profile") or {}
    if not isinstance(profile, dict):
        return ["LLM profile update ignored because it was not an object."]

    summary = profile.get("summary")
    if isinstance(summary, str) and summary.strip():
        content.body["profile"]["summary"] = _clip_summary(summary)

    goal = profile.get("goal")
    if isinstance(goal, str) and goal.strip():
        content.body["profile"]["goal"] = _clip_goal(goal)

    strengths = profile.get("strengths")
    if isinstance(strengths, list):
        cleaned_strengths = _sanitize_strengths(strengths, bundle, analysis, selection)
        if cleaned_strengths:
            content.body["profile"]["strengths"] = cleaned_strengths
        else:
            warnings.append("LLM strengths were ignored because they were not source-backed.")
    return warnings


def run_job_analyzer_llm(
    client: OpenAICompatibleClient,
    base_dir,
    bundle: SourceBundle,
    baseline_analysis: JobAnalysis,
) -> Tuple[JobAnalysis, Dict[str, Any], List[str]]:
    system_prompt = compose_stage_prompt(base_dir, "job_analyzer")
    user_payload = {
        "task": "Refine the baseline job analysis for the CV pipeline. Keep it compact and source-aware.",
        "job_offer_text": baseline_analysis.raw_text,
        "baseline_analysis": asdict(baseline_analysis),
        "selected_variant": resolve_cv_variant(bundle.profile, baseline_analysis.variant),
        "allowed_source_terms": candidate_terms(bundle, baseline_analysis.variant),
        "allowed_titles": unique(
            [
                baseline_analysis.title,
                bundle.profile.get("branding", {}).get("headline", ""),
                *bundle.profile.get("notes_for_cv_generation", {}).get("preferred_roles", []),
            ]
        ),
        "output_schema": {
            "title": "string",
            "summary": "string",
            "keywords": ["up to 6 strings"],
            "matched_terms": ["up to 10 strings"],
            "language": "de or en",
            "tone": "string",
        },
    }
    llm_payload = client.complete_json(system_prompt, json.dumps(user_payload, ensure_ascii=False, indent=2))

    warnings: List[str] = []
    title = baseline_analysis.title
    raw_title = llm_payload.get("title")
    if isinstance(raw_title, str):
        cleaned_title = _sanitize_title(raw_title, baseline_analysis, bundle)
        if cleaned_title:
            title = cleaned_title
        else:
            warnings.append("LLM job title ignored because it was not allowed.")

    raw_keywords = llm_payload.get("keywords")
    keywords = baseline_analysis.keywords
    if isinstance(raw_keywords, list):
        cleaned_keywords = _sanitize_job_terms(raw_keywords, bundle, baseline_analysis, 6)
        if cleaned_keywords:
            keywords = cleaned_keywords
        else:
            warnings.append("LLM job keywords ignored because they were not allowed.")

    raw_matched_terms = llm_payload.get("matched_terms")
    matched_terms = baseline_analysis.matched_terms
    if isinstance(raw_matched_terms, list):
        cleaned_matched_terms = _sanitize_job_terms(raw_matched_terms, bundle, baseline_analysis, 10)
        if cleaned_matched_terms:
            matched_terms = cleaned_matched_terms
        else:
            warnings.append("LLM matched terms ignored because they were not allowed.")

    if not keywords:
        keywords = matched_terms[:6]
    if not matched_terms:
        matched_terms = keywords[:10]

    summary = baseline_analysis.summary
    raw_summary = llm_payload.get("summary")
    if isinstance(raw_summary, str):
        summary = _sanitize_summary(raw_summary, baseline_analysis.summary)

    raw_language = llm_payload.get("language")
    language = baseline_analysis.language
    if raw_language in {"de", "en"}:
        language = raw_language
    else:
        language = detect_language(baseline_analysis.raw_text)

    raw_tone = llm_payload.get("tone")
    tone = baseline_analysis.tone
    if isinstance(raw_tone, str) and raw_tone.strip():
        tone = truncate_text(" ".join(raw_tone.split()).strip(), 24)

    analysis = JobAnalysis(
        title=title,
        summary=summary,
        keywords=keywords,
        matched_terms=matched_terms,
        raw_text=baseline_analysis.raw_text,
        language=language,
        tone=tone,
        variant=baseline_analysis.variant,
    )
    return analysis, llm_payload, warnings


def _apply_experience_updates(
    content: CVContent,
    payload: Dict[str, Any],
    bundle: SourceBundle,
    selection: EvidenceSelection,
) -> List[str]:
    warnings: List[str] = []
    scope = _experience_source_scope(bundle, selection)
    updates = payload.get("experience_updates") or []
    if not isinstance(updates, list):
        return warnings

    update_map = {}
    for item in updates:
        if not isinstance(item, dict):
            continue
        experience_id = item.get("experience_id")
        if isinstance(experience_id, str):
            update_map[experience_id] = item

    for experience in content.body.get("experiences", []):
        experience_id = experience.get("experience_id")
        if experience_id not in update_map:
            continue

        raw_highlights = update_map[experience_id].get("highlights") or []
        if not isinstance(raw_highlights, list):
            continue

        cleaned_highlights = []
        for highlight in raw_highlights[:2]:
            if not isinstance(highlight, dict):
                continue
            source_id = highlight.get("source_id")
            text = highlight.get("text")
            if not isinstance(source_id, str) or not isinstance(text, str):
                continue
            if source_id not in scope.get(experience_id, set()):
                warnings.append(f"LLM highlight for {experience_id} ignored unknown source {source_id}.")
                continue
            cleaned_highlights.append({"source_id": source_id, "text": _clip_highlight(text)})

        if cleaned_highlights:
            experience["highlights"] = cleaned_highlights

    return warnings


def run_writer_llm(
    client: OpenAICompatibleClient,
    base_dir,
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
    baseline_content: CVContent,
) -> Tuple[CVContent, Dict[str, Any], List[str]]:
    system_prompt = compose_stage_prompt(base_dir, "cv_writer", include_design_reference=True)
    user_payload = {
        "task": "Revise the baseline CV content to better match the job offer without changing facts.",
        "job_analysis": asdict(analysis),
        "baseline_cv": {
            "frontmatter": baseline_content.frontmatter,
            "body": {
                "headline": baseline_content.body["headline"],
                "profile": baseline_content.body["profile"],
                "experiences": baseline_content.body["experiences"],
            },
        },
        "source_snapshot": _source_snapshot(bundle, selection),
        "allowed_headlines": _allowed_headlines(bundle, analysis),
        "allowed_strength_terms": _allowed_strength_terms(bundle, analysis, selection),
        "output_schema": {
            "headline": "string or omit",
            "profile": {
                "summary": "string",
                "strengths": ["up to 4 strings"],
                "goal": "string",
            },
            "experience_updates": [
                {
                    "experience_id": "string",
                    "highlights": [
                        {"source_id": "string from supplied sources", "text": "string"},
                    ],
                }
            ],
        },
    }
    llm_payload = client.complete_json(system_prompt, json.dumps(user_payload, ensure_ascii=False, indent=2))

    content = deepcopy(baseline_content)
    warnings = _apply_profile_update(content, llm_payload, bundle, analysis, selection)
    warnings.extend(_apply_experience_updates(content, llm_payload, bundle, selection))

    headline = llm_payload.get("headline")
    if isinstance(headline, str):
        cleaned_headline = _sanitize_headline(headline, bundle, analysis)
        if cleaned_headline:
            content.frontmatter["headline"] = cleaned_headline
            content.frontmatter["job_title"] = cleaned_headline
            content.body["headline"] = cleaned_headline
        else:
            warnings.append("LLM headline ignored because it was not allowed.")

    return content, llm_payload, warnings


def run_fact_checker_llm(
    client: OpenAICompatibleClient,
    base_dir,
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
    content: CVContent,
) -> Tuple[CVContent, Dict[str, Any], List[str]]:
    system_prompt = compose_stage_prompt(base_dir, "fact_checker")
    user_payload = {
        "task": "Review the current CV content for unsupported wording and return corrected content only when needed.",
        "job_analysis": asdict(analysis),
        "current_cv": {
            "frontmatter": content.frontmatter,
            "body": {
                "headline": content.body["headline"],
                "profile": content.body["profile"],
                "experiences": content.body["experiences"],
            },
        },
        "source_snapshot": _source_snapshot(bundle, selection),
        "rules": [
            "Use only the supplied source ids.",
            "Keep experience ordering stable.",
            "Correct unsupported wording rather than adding new claims.",
            "Return corrections even when the document already looks valid.",
        ],
        "output_schema": {
            "passed": "boolean",
            "corrections": ["strings"],
            "headline": "string or omit",
            "profile": {
                "summary": "string",
                "strengths": ["up to 4 strings"],
                "goal": "string",
            },
            "experience_updates": [
                {
                    "experience_id": "string",
                    "highlights": [
                        {"source_id": "string from supplied sources", "text": "string"},
                    ],
                }
            ],
        },
    }
    llm_payload = client.complete_json(system_prompt, json.dumps(user_payload, ensure_ascii=False, indent=2))

    revised = deepcopy(content)
    warnings = _apply_profile_update(revised, llm_payload, bundle, analysis, selection)
    warnings.extend(_apply_experience_updates(revised, llm_payload, bundle, selection))

    headline = llm_payload.get("headline")
    if isinstance(headline, str):
        cleaned_headline = _sanitize_headline(headline, bundle, analysis)
        if cleaned_headline:
            revised.frontmatter["headline"] = cleaned_headline
            revised.frontmatter["job_title"] = cleaned_headline
            revised.body["headline"] = cleaned_headline
        else:
            warnings.append("Fact-checker LLM headline ignored because it was not allowed.")

    return revised, llm_payload, warnings
