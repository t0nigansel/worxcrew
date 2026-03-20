from __future__ import annotations

from typing import Dict, List

from .models import CVContent, EvidenceSelection, JobAnalysis, SourceBundle
from .utils import dump_frontmatter, truncate_text


def _selected_projects(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, object]]:
    project_map = {project["id"]: project for project in bundle.projects}
    return [project_map[project_id] for project_id in selection.selected_project_ids if project_id in project_map][:3]


def _selected_certifications(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, object]]:
    cert_map = {certification["id"]: certification for certification in bundle.certifications}
    return [
        cert_map[certification_id]
        for certification_id in selection.selected_certification_ids
        if certification_id in cert_map
    ][:2]


def build_cover_letter_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> CVContent:
    person = bundle.profile.get("person", {})
    company_hint = analysis.title or "Ihr Team"
    projects = _selected_projects(bundle, selection)
    certifications = _selected_certifications(bundle, selection)
    keywords = analysis.keywords[:3]

    opening = (
        f"mit grossem Interesse bewerbe ich mich auf die Position als {analysis.title or 'passende Fachrolle'}. "
        f"Mein Profil verbindet Qualitaetssicherung, Security Testing und praxisnahe Automatisierung mit einem "
        f"klaren Bezug zu {', '.join(keywords) or 'den Anforderungen Ihrer Ausschreibung'}."
    )

    fit_points = []
    for project in projects:
        fit_points.append(
            {
                "source_id": project["id"],
                "text": truncate_text(
                    f"{project.get('name', '')}: {project.get('role', '')} mit Fokus auf "
                    f"{project.get('description', '') or project.get('system_purpose', '')}",
                    180,
                ),
            }
        )

    certification_points = []
    for certification in certifications:
        certification_points.append(
            {
                "source_id": certification["id"],
                "text": truncate_text(
                    f"{certification.get('name', '')} unterstreicht meinen Fokus auf "
                    f"{', '.join(certification.get('skills', [])[:3]) or 'relevante Fachthemen'}.",
                    160,
                ),
            }
        )

    closing = (
        "Gerne moechte ich in einem persoenlichen Gespraech erlaeutern, wie ich meine Erfahrung in "
        "Teststrategie, Security und Automatisierung in Ihr Umfeld einbringen kann."
    )

    full_name = person.get("name", {}).get("full", "")
    frontmatter = {
        "document_type": "cover_letter",
        "language": analysis.language,
        "validated": False,
        "full_name": full_name,
        "headline": analysis.title or bundle.profile.get("branding", {}).get("headline", ""),
        "job_title": analysis.title,
        "variant": analysis.variant or "",
        "selected_project_ids": selection.selected_project_ids,
        "selected_certification_ids": selection.selected_certification_ids,
    }
    body = {
        "full_name": full_name,
        "job_title": analysis.title,
        "opening": opening,
        "fit_points": fit_points,
        "certification_points": certification_points,
        "closing": closing,
    }
    markdown = render_cover_letter_markdown(frontmatter, body)
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)


def render_cover_letter_markdown(frontmatter: Dict[str, object], body: Dict[str, object]) -> str:
    lines = [
        "---",
        dump_frontmatter(frontmatter),
        "---",
        "",
        f"# Anschreiben - {body['full_name']}",
        "",
        body["opening"],
        "",
        "## Warum ich gut passe",
        "",
    ]

    for item in body.get("fit_points", []):
        lines.append(f"<!-- source: {item['source_id']} -->")
        lines.append(f"- {item['text']}")

    if body.get("certification_points"):
        lines.extend(["", "## Relevante Zertifizierungen", ""])
        for item in body["certification_points"]:
            lines.append(f"<!-- source: {item['source_id']} -->")
            lines.append(f"- {item['text']}")

    lines.extend(["", "## Abschluss", "", body["closing"], ""])
    return "\n".join(lines).strip() + "\n"
