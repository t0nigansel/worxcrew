from __future__ import annotations

from typing import Dict, List

from .models import CVContent, EvidenceSelection, JobAnalysis, SourceBundle
from .utils import age_in_years, dump_frontmatter, month_label, month_label_long, normalize_text, truncate_text, unique
from .variants import resolve_cv_variant


def _headline(bundle: SourceBundle, analysis: JobAnalysis) -> str:
    profile_headline = bundle.profile.get("branding", {}).get("headline", "")
    variant = resolve_cv_variant(bundle.profile, analysis.variant)
    variant_headline = str(variant.get("headline", "") or "").strip()
    if variant_headline and not analysis.raw_text:
        return variant_headline
    if analysis.title and analysis.title != "Tailored Role" and (analysis.raw_text or analysis.variant):
        return analysis.title
    return profile_headline or "Senior Test Engineer"


def _contact_line(bundle: SourceBundle) -> str:
    person = bundle.profile.get("person", {})
    location = (person.get("locations") or [{}])[0].get("address", {})
    address = ", ".join(
        part
        for part in [
            location.get("street"),
            location.get("postal_code"),
            location.get("city"),
        ]
        if part
    )
    email = (person.get("contact", {}).get("emails") or [""])[0]
    phone = (person.get("contact", {}).get("phones") or [""])[0]
    return f"{address} | {phone} | {email}"


def _link_items(bundle: SourceBundle) -> List[Dict[str, str]]:
    links = bundle.profile.get("person", {}).get("links", {})
    items = []
    for label, key in [("LinkedIn", "linkedin"), ("Website", "website"), ("GitHub", "github")]:
        url = links.get(key)
        if url:
            items.append({"label": label, "url": url})
    return items


def _selected_projects(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, object]]:
    project_ids = set(selection.selected_project_ids)
    ranked = [project for project in bundle.projects if project.get("id") in project_ids]
    order = {project_id: index for index, project_id in enumerate(selection.selected_project_ids)}
    ranked.sort(key=lambda project: order.get(project["id"], 999))
    return ranked


def _selected_certifications(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, object]]:
    certification_ids = set(selection.selected_certification_ids)
    ranked = [certification for certification in bundle.certifications if certification.get("id") in certification_ids]
    order = {certification_id: index for index, certification_id in enumerate(selection.selected_certification_ids)}
    ranked.sort(key=lambda certification: order.get(certification["id"], 999))
    return ranked


def _responsibility_priority(project: Dict[str, object], responsibility: Dict[str, object], analysis: JobAnalysis) -> int:
    title = str(responsibility.get("title", "") or "")
    description = str(responsibility.get("description", "") or "")
    joined = normalize_text(" ".join([str(project.get("name", "")), title, description]))
    score = 0

    for keyword in analysis.keywords[:6]:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in joined:
            score += 3

    if analysis.variant == "ai_security_automation":
        for marker, weight in [
            ("ai", 5),
            ("agent", 5),
            ("llm", 5),
            ("prompt", 5),
            ("api", 5),
            ("automation", 4),
            ("automatis", 4),
            ("pipeline", 4),
            ("ci cd", 4),
            ("gitlab", 3),
            ("jenkins", 3),
            ("mentoring", 3),
            ("teamentwicklung", 3),
            ("leitung", 3),
            ("security", 3),
            ("threat", 3),
            ("sast", 4),
            ("kubernetes", 3),
            ("ki", 4),
            ("schulung", 3),
        ]:
            if marker in joined:
                score += weight
    elif analysis.variant == "security_appsec":
        for marker, weight in [
            ("security", 4),
            ("owasp", 5),
            ("pentest", 5),
            ("threat", 3),
            ("sast", 4),
            ("pipeline", 2),
            ("schulung", 2),
        ]:
            if marker in joined:
                score += weight
    else:
        for marker, weight in [("security", 2), ("api", 2), ("automatis", 2), ("ci cd", 2)]:
            if marker in joined:
                score += weight

    return score


def _project_tools(project: Dict[str, object], limit: int = 3) -> str:
    return ", ".join((project.get("tools", []) or [])[:limit])


def _ranked_responsibilities(project: Dict[str, object], analysis: JobAnalysis) -> List[Dict[str, object]]:
    responsibilities = [item for item in (project.get("responsibilities", []) or []) if isinstance(item, dict)]
    return sorted(
        responsibilities,
        key=lambda responsibility: (
            -_responsibility_priority(project, responsibility, analysis),
            str(responsibility.get("title", "")),
        ),
    )


def _projects_by_experience(bundle: SourceBundle, selection: EvidenceSelection) -> Dict[str, List[Dict[str, object]]]:
    mapping: Dict[str, List[Dict[str, object]]] = {}
    for project in _selected_projects(bundle, selection):
        experience_id = project.get("related_experience_id")
        if experience_id:
            mapping.setdefault(experience_id, []).append(project)
    return mapping


def _compose_profile(bundle: SourceBundle, analysis: JobAnalysis, selection: EvidenceSelection) -> Dict[str, object]:
    experiences = bundle.profile.get("experience", [])
    years = age_in_years(experiences[-1]["start"] if experiences else "2010-01")
    variant = resolve_cv_variant(bundle.profile, analysis.variant)
    project_names = [project["name"] for project in _selected_projects(bundle, selection)[:3]]
    certification_names = [certification["name"] for certification in _selected_certifications(bundle, selection)[:3]]
    keywords = analysis.keywords[:4] or bundle.profile.get("notes_for_cv_generation", {}).get("positioning_keywords", [])[:4]
    industries = unique(project.get("client") for project in _selected_projects(bundle, selection) if project.get("client"))

    if analysis.variant == "security_appsec":
        summary = (
            f"Security- und Testingenieur mit rund {years}+ Jahren Erfahrung in Application Security, "
            f"OWASP-orientiertem Testing und CI/CD-naher Qualitaetssicherung. Fokus auf "
            f"{', '.join(keywords[:2]) or 'Security Testing und OWASP'}. "
            f"Referenzen: {', '.join(project_names[:2])}."
        )
        goal = (
            f"Zielsetzung: Remote-Rolle in Security Testing / AppSec mit Fokus auf "
            f"{', '.join(keywords[:3]) or 'OWASP, Threat Modeling und Teststrategie'}."
        )
    elif analysis.variant == "ai_security_automation":
        summary = (
            f"Security- und Testingenieur mit rund {years}+ Jahren Erfahrung in Security Testing, "
            f"Threat Modeling und technischer Automatisierung. Ergaenzt um aktuelle Weiterbildungen zu "
            f"{', '.join(certification_names[:2]) or 'AI Security und agentischen Workflows'}."
        )
        goal = (
            f"Zielsetzung: Remote-Rolle in AI Security / Automation mit Fokus auf "
            f"{', '.join(keywords[:3]) or 'AI Security, Threat Modeling und sichere Workflows'}."
        )
    else:
        summary = (
            f"Testingenieur mit rund {years}+ Jahren Erfahrung in Softwareentwicklung, "
            f"Qualitaetssicherung und Security Testing. Fokus fuer die Zielrolle: "
            f"{', '.join(keywords)}. Relevante Referenzen: {', '.join(project_names)}."
        )
        goal = (
            f"Zielsetzung: {analysis.title} mit Schwerpunkt auf "
            f"{', '.join(keywords[:3]) or 'Teststrategie und Automatisierung'}."
        )

    work_preferences = _work_preferences(bundle)
    summary_limit = 300 if analysis.variant in {"security_appsec", "ai_security_automation"} else 240

    return {
        "summary": truncate_text(summary, summary_limit),
        "strengths": keywords[:4],
        "goal": truncate_text(goal, 140),
        "industries": industries[:5],
        "work_preferences": work_preferences,
        "variant_focus": str(variant.get("summary_focus", "") or "").strip(),
    }


def _project_highlight(project: Dict[str, object], analysis: JobAnalysis) -> str:
    responsibilities = _ranked_responsibilities(project, analysis)
    if analysis.variant in {"security_appsec", "ai_security_automation"} and responsibilities:
        titles = [
            str(item.get("title", "") or "").strip()
            for item in responsibilities[:2]
            if str(item.get("title", "") or "").strip()
        ]
        if titles:
            tools = _project_tools(project)
            text = f"{project['name']}: {'; '.join(titles)}."
            if tools:
                text = f"{text} ({tools})"
            return truncate_text(text, 165 if analysis.variant == "ai_security_automation" else 150)

    tools = _project_tools(project)
    description = truncate_text(str(project.get("description", "")), 100)
    if tools:
        return f"{project['name']}: {description} ({tools})"
    return f"{project['name']}: {description}"


def _compose_featured_projects(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> List[Dict[str, object]]:
    order = {project_id: index for index, project_id in enumerate(selection.selected_project_ids)}
    projects = sorted(_selected_projects(bundle, selection), key=lambda project: order.get(str(project.get("id", "")), 999))

    featured = []
    project_limit = 6 if analysis.variant == "security_appsec" else 3
    for project in projects[:project_limit]:
        responsibilities = _ranked_responsibilities(project, analysis)
        summary_parts = [
            str(item.get("title", "") or "").strip()
            for item in responsibilities[:2]
            if str(item.get("title", "") or "").strip()
        ]
        summary = "; ".join(summary_parts)
        if not summary:
            summary = truncate_text(str(project.get("description", "")), 120)

        detail_points = [
            str(item.get("title", "") or "").strip()
            for item in responsibilities[:3]
            if str(item.get("title", "") or "").strip()
        ]
        context = truncate_text(
            str(project.get("system_purpose", "") or project.get("description", "") or ""),
            185 if analysis.variant == "ai_security_automation" else 160,
        )

        period = project.get("period", {}) or {}
        period_label = ""
        start = str(period.get("start", "") or "")
        end = str(period.get("end", "") or "")
        if start or end:
            period_label = f"{month_label(start)} - {month_label(end)}".strip(" -")

        badge_label, badge_tone = _project_badge(project, analysis)

        featured.append(
            {
                "project_id": str(project.get("id", "")),
                "name": str(project.get("name", "")),
                "client": str(project.get("client", "")),
                "role": str(project.get("role", "")),
                "period": period_label,
                "summary": truncate_text(summary, 150),
                "context": context,
                "detail_points": detail_points,
                "tools": _project_tools(project, limit=4),
                "badge_label": badge_label,
                "badge_tone": badge_tone,
            }
        )

    return featured


def _project_badge(project: Dict[str, object], analysis: JobAnalysis) -> tuple[str, str]:
    text = normalize_text(
        " ".join(
            [
                str(project.get("name", "") or ""),
                str(project.get("role", "") or ""),
                str(project.get("description", "") or ""),
                str(project.get("system_purpose", "") or ""),
                " ".join(str(item.get("title", "") or "") for item in (project.get("responsibilities", []) or []) if isinstance(item, dict)),
            ]
        )
    )

    if analysis.variant == "security_appsec":
        name_lower = str(project.get("name", "")).lower()
        role_lower = str(project.get("role", "")).lower()
        methodology_lower = str(project.get("methodology", "") or "").lower()
        if "api" in name_lower:
            return ("API", "badge-neutral")
        elif "pentest" in name_lower or "pentest" in role_lower or "black" in methodology_lower:
            return ("Black-Box", "badge-security")
        elif "security" in name_lower:
            return ("Security", "badge-automation")
        elif any(m in text for m in ["sast", "owasp", "threat", "security", "pentest"]):
            return ("White-Box", "badge-neutral")
        else:
            return ("Security", "badge-security")

    badge_rules = [
        (("llm", "agent", "prompt", "ai", "ki"), ("AI", "badge-ai")),
        (("pentest", "security", "owasp", "sast", "threat"), ("Security", "badge-security")),
        (("performance", "last", "load", "jmeter", "kubernetes"), ("Performance", "badge-performance")),
        (("automation", "automatis", "pipeline", "ci cd", "gitlab", "jenkins", "selenium", "cypress"), ("Automation", "badge-automation")),
    ]

    for markers, badge in badge_rules:
        if any(marker in text for marker in markers):
            return badge

    if analysis.variant == "ai_security_automation":
        return ("Automation", "badge-automation")
    if analysis.variant == "security_appsec":
        return ("Security", "badge-security")
    return ("Delivery", "badge-neutral")


def _experience_project_priority(
    project: Dict[str, object],
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> tuple[int, int, str]:
    text = normalize_text(
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
    score = 0

    for keyword in analysis.keywords[:6]:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in text:
            score += 3

    if analysis.variant == "ai_security_automation":
        marker_weights = [
            ("ai", 5),
            ("api", 5),
            ("automation", 4),
            ("automatis", 4),
            ("pipeline", 4),
            ("security", 3),
            ("agent", 4),
            ("threat", 3),
            ("sast", 4),
            ("kubernetes", 3),
        ]
    elif analysis.variant == "security_appsec":
        marker_weights = [
            ("pentest", 5),
            ("sast", 4),
            ("security", 3),
            ("owasp", 3),
            ("threat", 2),
        ]
    else:
        marker_weights = [
            ("security", 2),
            ("api", 2),
            ("automatis", 2),
            ("ci cd", 2),
        ]

    for marker, points in marker_weights:
        if marker in text:
            score += points

    selection_rank = selection.selected_project_ids.index(project["id"]) if project["id"] in selection.selected_project_ids else 999
    period = project.get("period", {}) or {}
    end_value = str(period.get("end", "") or "")
    return (-score, selection_rank, f"~{end_value}" if end_value else "~")


def _compose_experiences(bundle: SourceBundle, analysis: JobAnalysis, selection: EvidenceSelection) -> List[Dict[str, object]]:
    entries = []

    for experience in bundle.profile.get("experience", []):
        projects = [
            project
            for project in bundle.projects
            if project.get("related_experience_id") == experience["id"]
        ]
        ranked_projects = sorted(projects, key=lambda project: _experience_project_priority(project, analysis, selection))

        raw_roles = unique(
            str(project.get("role", "")).strip()
            for project in ranked_projects
            if str(project.get("role", "")).strip()
        )
        roles_held = _split_and_deduplicate_roles(raw_roles, limit=2)
        project_names = [str(project.get("name", "")).strip() for project in ranked_projects[:4] if str(project.get("name", "")).strip()]
        summary_points = [
            str(item).strip()
            for item in (experience.get("summary", []) or [])
            if str(item).strip()
        ]
        focus_text = truncate_text(" · ".join(summary_points[:3]), 135)
        source_ids = [experience["id"]] + [str(project.get("id", "")) for project in ranked_projects[:4] if str(project.get("id", "")).strip()]

        entries.append(
            {
                "experience_id": experience["id"],
                "role": experience["role"],
                "company": experience["company"],
                "period": f"{month_label(experience['start'])} - {month_label(experience['end'])}",
                "roles_held": roles_held,
                "project_names": project_names[:4],
                "focus_text": focus_text,
                "source_ids": source_ids,
            }
        )
    return entries


def _compose_sidebar(bundle: SourceBundle, selection: EvidenceSelection) -> Dict[str, object]:
    education = []
    for item in bundle.profile.get("education", []):
        education.append(
            {
                "institution": item["institution"],
                "program": item["program"],
                "period": f"{item['start'][:4]} - {item['end'][:4]}",
                "source_id": item["id"],
            }
        )

    availability = bundle.profile.get("availability", {}).get("available_from")
    languages = [
        {"name": item["name"], "level": item["level"]}
        for item in bundle.profile.get("languages", [])
        if item.get("name")
    ]
    branding = bundle.profile.get("branding", {}) or {}
    work_preferences = _work_preferences(bundle)
    focus_areas = [
        str(item).strip()
        for item in (branding.get("focus_areas", []) or [])
        if str(item).strip()
    ]
    standards = [
        str(item).strip()
        for item in (branding.get("standards_and_frameworks", []) or [])
        if str(item).strip()
    ]

    return {
        "focus_areas": focus_areas[:4],
        "standards": standards[:4],
        "work_preferences": work_preferences,
        "technology_groups": selection.technology_groups,
        "certification_groups": selection.certification_groups,
        "education": education,
        "languages": languages,
        "clients": selection.selected_clients,
        "availability": month_label_long(availability) if availability else "",
    }


def _work_preferences(bundle: SourceBundle) -> str:
    preferences = bundle.profile.get("work_preferences", {}) or {}
    parts = []
    if preferences.get("remote_only"):
        parts.append("100% Remote")

    travel = str(preferences.get("travel_willingness", "") or "").strip().lower()
    if travel == "none":
        parts.append("Keine Reisebereitschaft")
    elif travel:
        parts.append(str(preferences.get("travel_willingness")))

    return " | ".join(parts)


def _compose_footer_keywords(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> List[str]:
    """Build footer keywords from JSON data: technologies, certs, and analysis keywords."""
    seen: set = set()
    keywords: List[str] = []

    def _add(term: str) -> None:
        normalized = term.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            keywords.append(f"#{term.strip()}")

    # Analysis keywords first (job-relevant)
    for kw in analysis.keywords:
        _add(kw)

    # Technology items from sidebar
    for group in selection.technology_groups:
        for item in group.get("items", []):
            _add(item)

    # Certification short names
    for group in selection.certification_groups:
        for item in group.get("items", []):
            label = str(item.get("label", ""))
            # Extract the cert name (before the year in parentheses)
            if "(" in label:
                name = label[:label.rfind("(")].strip()
            else:
                name = label.strip()
            _add(name)

    # Profile positioning keywords
    for kw in bundle.profile.get("notes_for_cv_generation", {}).get("positioning_keywords", []):
        _add(kw)

    return keywords[:15]  # Limit to fit footer


def _split_and_deduplicate_roles(roles: List[str], limit: int = 2) -> List[str]:
    """Split composite roles like 'Security Tester / Test Manager' and deduplicate."""
    individual: List[str] = []
    seen: set = set()
    for role in roles:
        # Split on ' / ' to separate composite role strings
        parts = [part.strip() for part in role.replace(" / ", " / ").split(" / ")]
        for part in parts:
            normalized = part.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                individual.append(part.strip())
    return individual[:limit]


def build_cv_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
    layout_name: str = "reference",
) -> CVContent:
    person = bundle.profile.get("person", {})
    experiences = _compose_experiences(bundle, analysis, selection)
    frontmatter = {
        "document_type": "cv",
        "language": "de",
        "validated": False,
        "full_name": person.get("name", {}).get("full", ""),
        "headline": _headline(bundle, analysis),
        "job_title": analysis.title,
        "variant": analysis.variant or "",
        "layout": layout_name or "reference",
        "selected_project_ids": selection.selected_project_ids,
        "selected_certification_ids": selection.selected_certification_ids,
        "selected_experience_ids": selection.selected_experience_ids,
    }

    body = {
        "layout": layout_name or "reference",
        "full_name": person.get("name", {}).get("full", ""),
        "headline": _headline(bundle, analysis),
        "contact_line": _contact_line(bundle),
        "links": _link_items(bundle),
        "profile": _compose_profile(bundle, analysis, selection),
        "featured_projects": _compose_featured_projects(bundle, analysis, selection),
        "experiences": experiences,
        "sidebar": _compose_sidebar(bundle, selection),
        "portrait_path": str(bundle.portrait_path),
        "footer_keywords": _compose_footer_keywords(bundle, analysis, selection),
    }

    markdown = render_markdown(frontmatter, body)
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)


def render_markdown(frontmatter: Dict[str, object], body: Dict[str, object]) -> str:
    profile = body["profile"]
    sidebar = body["sidebar"]
    lines = [
        "---",
        dump_frontmatter(frontmatter),
        "---",
        "",
        f"# {body['full_name']}",
        "",
        f"**{body['headline']}**",
        "",
        body["contact_line"],
        "",
        " | ".join(f"[{item['label']}]({item['url']})" for item in body["links"]),
        "",
        "## Profil",
        "",
        profile["summary"],
        "",
        f"**Schwerpunkte:** {', '.join(profile['strengths'])}",
        "",
        profile["goal"],
        "",
    ]

    if profile.get("work_preferences"):
        lines.extend([f"**Arbeitsmodell:** {profile['work_preferences']}", ""])

    lines.extend(
        [
            f"**Branchenerfahrung:** {', '.join(profile['industries'])}",
            "",
        ]
    )

    if body.get("featured_projects"):
        lines.extend(["## Ausgewaehlte Projekte", ""])
        for item in body["featured_projects"]:
            lines.append(f"<!-- source: {item['project_id']} -->")
            lines.append(f"### {item['name']}")
            lines.append("")
            meta_parts = [item["client"], item["role"], item["period"]]
            lines.append(" | ".join(part for part in meta_parts if part))
            lines.append("")
            if item.get("context"):
                lines.append(f"- Kontext: {item['context']}")
            lines.append(f"- Fokus: {item['summary']}")
            for detail in item.get("detail_points", []):
                lines.append(f"- Detail: {detail}")
            if item.get("tools"):
                lines.append(f"- Tools: {item['tools']}")
            lines.append("")

    lines.extend(["## Berufserfahrung", ""])
    for experience in body["experiences"]:
        lines.append(f"<!-- source: {', '.join(experience.get('source_ids', []))} -->")
        lines.extend(
            [
                f"### {experience['company']}",
                "",
                f"{experience['role']} | {experience['period']}",
                "",
            ]
        )
        if experience.get("roles_held"):
            lines.append(f"- Rollen: {', '.join(experience['roles_held'])}")
        if experience.get("project_names"):
            lines.append(f"- Projekte: {', '.join(experience['project_names'])}")
        if experience.get("focus_text"):
            lines.append(f"- Schwerpunkte: {experience['focus_text']}")
        lines.append("")

    lines.extend(["## Technologien", ""])
    for group in sidebar["technology_groups"]:
        lines.append(f"### {group['name']}")
        lines.append("")
        lines.append(", ".join(group["items"]))
        lines.append("")

    if sidebar.get("focus_areas"):
        lines.extend(["## Fokus", ""])
        for item in sidebar["focus_areas"]:
            lines.append(f"- {item}")
        lines.append("")

    if sidebar.get("standards"):
        lines.extend(["## Standards", ""])
        for item in sidebar["standards"]:
            lines.append(f"- {item}")
        lines.append("")

    if sidebar.get("work_preferences"):
        lines.extend(["## Arbeitsmodell", "", sidebar["work_preferences"], ""])

    lines.extend(["## Zertifizierungen", ""])
    for group in sidebar["certification_groups"]:
        lines.append(f"### {group['name']}")
        lines.append("")
        for item in group["items"]:
            lines.append(f"<!-- source: {item['source_id']} -->")
            lines.append(f"- {item['label']}")
        lines.append("")

    lines.extend(["## Ausbildung", ""])
    for education in sidebar["education"]:
        lines.append(f"<!-- source: {education['source_id']} -->")
        lines.append(f"- {education['institution']} | {education['program']} | {education['period']}")
    lines.append("")

    lines.extend(
        [
            "## Ausgewaehlte Kunden",
            "",
            ", ".join(sidebar["clients"]),
            "",
        ]
    )

    if sidebar["availability"]:
        lines.extend([f"**Verfuegbar ab:** {sidebar['availability']}", ""])

    if sidebar.get("languages"):
        lines.extend(["## Sprachen", ""])
        for lang in sidebar["languages"]:
            lines.append(f"- {lang['name']} – {lang['level']}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
