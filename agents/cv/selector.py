from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from .models import EvidenceSelection, JobAnalysis, SourceBundle
from .utils import normalize_text, unique
from .variants import resolve_cv_variant


SKILL_GROUP_LABELS = {
    "testing_tools": "Testtools",
    "security_tools": "Security",
    "programming_languages": "Programmierung",
    "platforms_and_infra": "Infrastruktur & CI/CD",
    "databases": "Datenbanken",
    "methods": "Methoden",
    "test_management_tools": "Testmanagement",
}

SKILL_GROUP_LIMITS = {
    "testing_tools": 8,
    "security_tools": 5,
    "programming_languages": 6,
    "platforms_and_infra": 7,
    "databases": 4,
    "methods": 5,
    "test_management_tools": 4,
}

_OFFENSIVE_SECURITY_TESTING_TOOLS = {"Burp Suite", "OWASP ZAP", "SonarQube"}

SECURITY_APPSEC_GROUPS = [
    {
        "source_keys": ["security_tools"],
        "name": "Offensive Security",
        "limit": 6,
        "extra_from_testing_tools": True,
    },
    {
        "source_keys": ["programming_languages"],
        "name": "Scripting & Automation",
        "limit": 5,
    },
    {
        "source_keys": ["platforms_and_infra"],
        "name": "Cloud & Infra",
        "limit": 5,
    },
    {
        "source_keys": ["methods"],
        "name": "Standards & Compliance",
        "limit": 6,
        "include_standards": True,
    },
    {
        "source_keys": ["testing_tools", "test_management_tools"],
        "name": "Tools & Collaboration",
        "limit": 6,
    },
]


def _text_score(text_parts: Iterable[str], analysis: JobAnalysis) -> float:
    joined = normalize_text(" ".join(part for part in text_parts if part))
    if not joined:
        return 0.0

    score = 0.0
    for keyword in analysis.keywords + analysis.matched_terms:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in joined:
            score += max(2.0, len(normalized_keyword.split()))
    return score


def _project_score(project: Dict[str, object], analysis: JobAnalysis, variant: Dict[str, object]) -> float:
    period = project.get("period", {}) or {}
    recency_bonus = 0.0
    end_value = str(period.get("end", "") or "")
    if end_value.startswith("2026"):
        recency_bonus = 3.0
    elif end_value.startswith("2025") or end_value.startswith("2024"):
        recency_bonus = 2.0
    elif end_value.startswith("2023") or end_value.startswith("2022"):
        recency_bonus = 1.0

    score = _text_score(
        [
            str(project.get("name", "")),
            str(project.get("role", "")),
            str(project.get("description", "")),
            str(project.get("methodology", "")),
            str(project.get("system_purpose", "")),
            " ".join(project.get("tools", []) or []),
        ],
        analysis,
    )

    responsibilities = project.get("responsibilities", []) or []
    score += sum(_text_score([str(item.get("title", "")), str(item.get("description", ""))], analysis) for item in responsibilities)
    preferred_project_ids = set(variant.get("preferred_project_ids", []) or [])
    if project.get("id") in preferred_project_ids:
        score += 8.0

    if analysis.variant == "security_appsec":
        security_text = normalize_text(
            " ".join(
                [
                    str(project.get("name", "")),
                    str(project.get("role", "")),
                    str(project.get("description", "")),
                    str(project.get("methodology", "")),
                    " ".join(project.get("tools", []) or []),
                ]
            )
        )
        for marker in ["security", "owasp", "threat", "sast", "zap", "burp", "pentest"]:
            if marker in security_text:
                score += 1.5
    if analysis.variant == "ai_security_automation":
        ai_text = normalize_text(
            " ".join(
                [
                    str(project.get("name", "")),
                    str(project.get("role", "")),
                    str(project.get("description", "")),
                    str(project.get("methodology", "")),
                    " ".join(project.get("tools", []) or []),
                ]
            )
        )
        for marker in ["ai", "security", "automation", "api", "workflow", "threat", "sast", "agent"]:
            if marker in ai_text:
                score += 1.5
    return score + recency_bonus


def _certification_score(certification: Dict[str, object], analysis: JobAnalysis, variant: Dict[str, object]) -> float:
    score = _text_score(
        [
            str(certification.get("name", "")),
            " ".join(certification.get("issuer", []) or []),
            " ".join(certification.get("skills", []) or []),
        ],
        analysis,
    )
    issued = str(certification.get("issued", "") or "")
    if issued.startswith("2025") or issued.startswith("2026"):
        score += 2.0
    elif issued.startswith("2024"):
        score += 1.0
    preferred_certification_ids = set(variant.get("preferred_certification_ids", []) or [])
    if certification.get("id") in preferred_certification_ids:
        score += 6.0

    if analysis.variant == "security_appsec":
        security_text = normalize_text(
            " ".join(
                [
                    str(certification.get("name", "")),
                    " ".join(certification.get("skills", []) or []),
                ]
            )
        )
        for marker in ["security", "ethical hacker", "secure software", "cybersecurity", "owasp"]:
            if marker in security_text:
                score += 1.5
    if analysis.variant == "ai_security_automation":
        ai_text = normalize_text(
            " ".join(
                [
                    str(certification.get("name", "")),
                    " ".join(certification.get("skills", []) or []),
                ]
            )
        )
        for marker in ["ai", "llm", "agent", "chatgpt", "security", "cybersecurity", "prompt"]:
            if marker in ai_text:
                score += 1.5
    return score


def _classification_terms(analysis: JobAnalysis) -> List[str]:
    return [normalize_text(keyword) for keyword in analysis.keywords + analysis.matched_terms]


def _certification_groups(bundle: SourceBundle, selected_ids: List[str], analysis: JobAnalysis) -> List[Dict[str, object]]:
    order = {cert_id: index for index, cert_id in enumerate(selected_ids)}
    selected = [certification for certification in bundle.certifications if certification.get("id") in selected_ids]
    selected.sort(key=lambda certification: order.get(certification.get("id"), 999))
    groups = defaultdict(list)
    ai_terms = {"ai", "llm", "agent", "chatgpt", "prompt", "red team", "red teaming"}

    for certification in selected:
        name = normalize_text(str(certification.get("name", "")))
        skills = normalize_text(" ".join(certification.get("skills", []) or []))
        joined = f"{name} {skills}"
        if any(term in joined for term in ai_terms):
            group_name = "AI Red Teaming & Cloud" if analysis.variant == "security_appsec" else "AI Security & AI Testing"
        elif "scrum" in joined or "ux" in joined or "data" in joined:
            group_name = "Weitere"
        else:
            group_name = "Security & Ethical Hacking" if analysis.variant == "security_appsec" else "Testing & Security"

        issued = certification.get("issued")
        label = certification.get("name", "")
        if issued:
            label = f"{label} ({issued[:4]})"
        groups[group_name].append({"label": label, "source_id": certification.get("id")})

    ordered_groups = []
    if analysis.variant == "security_appsec":
        group_order = ["Security & Ethical Hacking", "AI Red Teaming & Cloud", "Weitere"]
    elif analysis.variant == "ai_security_automation":
        group_order = ["AI Security & AI Testing", "Testing & Security", "Weitere"]
    else:
        group_order = ["Testing & Security", "AI Security & AI Testing", "Weitere"]

    for group_name in group_order:
        items = groups.get(group_name, [])
        if items:
            if analysis.variant == "security_appsec" and group_name == "AI Red Teaming & Cloud":
                pass  # include AI group for security_appsec
            if analysis.variant == "security_appsec":
                group_limit = 5 if group_name == "Security & Ethical Hacking" else 3
            elif analysis.variant == "ai_security_automation":
                group_limit = 4 if group_name == "AI Security & AI Testing" else 3
            else:
                group_limit = 3 if group_name != "Weitere" else 2
            ordered_groups.append({"name": group_name, "items": items[:group_limit]})
    return ordered_groups


def _security_appsec_technology_groups(bundle: SourceBundle) -> List[Dict[str, object]]:
    profile_skills = bundle.profile.get("skills", {})
    standards = bundle.profile.get("branding", {}).get("standards_and_frameworks", [])
    used: set[str] = set()
    groups = []
    for spec in SECURITY_APPSEC_GROUPS:
        items: List[str] = []
        for key in spec["source_keys"]:
            items.extend(profile_skills.get(key, []))
        if spec.get("extra_from_testing_tools"):
            items.extend(t for t in profile_skills.get("testing_tools", []) if t in _OFFENSIVE_SECURITY_TESTING_TOOLS)
        if spec.get("include_standards"):
            items.extend(standards)
        deduped = [item for item in unique(items) if item not in used][:spec["limit"]]
        used.update(deduped)
        groups.append({"name": spec["name"], "items": deduped})
    return groups


def _technology_groups(
    bundle: SourceBundle,
    selected_projects: List[Dict[str, object]],
    analysis: JobAnalysis,
    variant: Dict[str, object],
) -> List[Dict[str, object]]:
    if analysis.variant == "security_appsec":
        return _security_appsec_technology_groups(bundle)
    profile_skills = bundle.profile.get("skills", {})
    groups: List[Dict[str, object]] = []

    extra_test_tools = []
    for project in selected_projects:
        extra_test_tools.extend(project.get("tools", []) or [])

    ordered_keys = list(SKILL_GROUP_LABELS.keys())
    variant_priority = [key for key in variant.get("technology_group_priority", []) or [] if key in SKILL_GROUP_LABELS]
    if variant_priority:
        ordered_keys = unique(variant_priority + ordered_keys)

    for source_key in ordered_keys:
        label = SKILL_GROUP_LABELS[source_key]
        base_items = list(profile_skills.get(source_key, []))
        if source_key == "testing_tools":
            base_items.extend(extra_test_tools)
        if source_key == "methods":
            base_items.extend(bundle.profile.get("branding", {}).get("standards_and_frameworks", []))
        groups.append({"name": label, "items": unique(base_items)[: SKILL_GROUP_LIMITS[source_key]]})

    ai_items = []
    normalized_matches = [normalize_text(keyword) for keyword in analysis.keywords + analysis.matched_terms]
    if any("ai" in keyword for keyword in normalized_matches):
        ai_items.extend(["AI Security", "AI Agents"])
    if any("llm" in keyword for keyword in normalized_matches):
        ai_items.extend(["LLM Security", "Prompt Injection Testing"])
    if ai_items:
        ai_items.extend(["Red Teaming", "LLM-gestuetzte Testplanung"])
        groups.insert(2, {"name": "AI & LLM Security", "items": unique(ai_items)[:4]})

    return groups


def select_evidence(bundle: SourceBundle, analysis: JobAnalysis) -> EvidenceSelection:
    variant = resolve_cv_variant(bundle.profile, analysis.variant)
    project_scores = {project["id"]: _project_score(project, analysis, variant) for project in bundle.projects}
    ranked_projects = sorted(bundle.projects, key=lambda project: (-project_scores[project["id"]], project["name"]))
    project_limit = 6 if analysis.variant in {"ai_security_automation", "security_appsec"} else 5
    selected_projects = ranked_projects[:project_limit]

    certification_scores = {
        certification["id"]: _certification_score(certification, analysis, variant) for certification in bundle.certifications
    }
    ranked_certifications = sorted(
        bundle.certifications,
        key=lambda certification: (-certification_scores[certification["id"]], certification["name"]),
    )
    certification_limit = 6 if analysis.variant == "security_appsec" else 7
    selected_certifications = ranked_certifications[:certification_limit]

    selected_experience_ids = unique(
        project.get("related_experience_id") for project in selected_projects if project.get("related_experience_id")
    )
    if not selected_experience_ids:
        selected_experience_ids = [experience["id"] for experience in bundle.profile.get("experience", [])[:4]]

    selected_clients = unique(project.get("client") for project in selected_projects if project.get("client"))[:6]

    return EvidenceSelection(
        selected_project_ids=[project["id"] for project in selected_projects],
        selected_certification_ids=[certification["id"] for certification in selected_certifications],
        selected_experience_ids=selected_experience_ids,
        selected_clients=selected_clients,
        technology_groups=_technology_groups(bundle, selected_projects, analysis, variant),
        certification_groups=_certification_groups(
            bundle,
            [certification["id"] for certification in selected_certifications],
            analysis,
        ),
        project_scores=project_scores,
        certification_scores=certification_scores,
    )
