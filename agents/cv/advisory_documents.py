from __future__ import annotations

from typing import Dict, List

from .models import CVContent, EvidenceSelection, JobAnalysis, SourceBundle
from .utils import dump_frontmatter, normalize_text, truncate_text, unique


def _selected_projects(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, object]]:
    project_map = {project["id"]: project for project in bundle.projects}
    return [project_map[project_id] for project_id in selection.selected_project_ids if project_id in project_map][:4]


def _selected_certifications(bundle: SourceBundle, selection: EvidenceSelection) -> List[Dict[str, object]]:
    cert_map = {certification["id"]: certification for certification in bundle.certifications}
    return [
        cert_map[certification_id]
        for certification_id in selection.selected_certification_ids
        if certification_id in cert_map
    ][:4]


def _base_frontmatter(document_type: str, bundle: SourceBundle, analysis: JobAnalysis) -> Dict[str, object]:
    return {
        "document_type": document_type,
        "language": analysis.language,
        "validated": True,
        "person_id": bundle.person_id,
        "full_name": bundle.profile.get("person", {}).get("name", {}).get("full", ""),
        "job_title": analysis.title,
        "variant": analysis.variant or "",
        "advisory": True,
    }


def _render_sections(frontmatter: Dict[str, object], title: str, sections: List[Dict[str, object]]) -> str:
    lines = ["---", dump_frontmatter(frontmatter), "---", "", f"# {title}", ""]
    for section in sections:
        lines.append(f"## {section['title']}")
        lines.append("")
        lines.append(str(section["body"]).strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_interview_prep_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> CVContent:
    projects = _selected_projects(bundle, selection)
    certifications = _selected_certifications(bundle, selection)
    project_names = ", ".join(project.get("name", "") for project in projects[:2] if project.get("name"))
    cert_names = ", ".join(cert.get("name", "") for cert in certifications[:2] if cert.get("name"))
    keyword_focus = ", ".join(analysis.keywords[:3]) or "Ihre Kernkompetenzen"

    questions = [
        {
            "title": "Frage 1",
            "body": (
                f"**Wahrscheinliche Frage:** Wie wuerden Sie Ihren Beitrag in einer Rolle als {analysis.title or 'Fachkraft'} beschreiben?\n\n"
                f"**Warum wahrscheinlich:** Die Ausschreibung legt Gewicht auf {keyword_focus}.\n\n"
                f"**Starke Antwort:** Fokussieren Sie auf konkrete Wirkung, zum Beispiel auf Ergebnisse aus {project_names or 'aktuellen Projekten'}, "
                "und verbinden Sie diese mit messbarer Verbesserung in Qualitaet, Sicherheit oder Automatisierung."
            ),
        },
        {
            "title": "Frage 2",
            "body": (
                f"**Wahrscheinliche Frage:** Wie gehen Sie mit komplexen Qualitaets- oder Security-Risiken im Team um?\n\n"
                f"**Warum wahrscheinlich:** Ihre Profilstaerken und die Variante {analysis.variant or 'default'} deuten auf einen beratenden, strukturierenden Beitrag hin.\n\n"
                f"**Starke Antwort:** Beschreiben Sie einen klaren Ablauf aus Risikoanalyse, Priorisierung, Stakeholder-Abstimmung und Umsetzung. "
                f"Verweisen Sie auf belastbare Referenzen wie {project_names or 'vergleichbare Projekte'}."
            ),
        },
        {
            "title": "Frage 3",
            "body": (
                f"**Wahrscheinliche Frage:** Wie halten Sie Ihr Wissen aktuell und wie uebertragen Sie es in die Praxis?\n\n"
                f"**Warum wahrscheinlich:** Aktuelle Weiterbildungen wie {cert_names or 'Ihre Zertifizierungen'} machen diesen Punkt plausibel.\n\n"
                "**Starke Antwort:** Verbinden Sie Weiterbildung mit einem konkreten Transfer in Projekte, Prozesse oder Standards, statt nur Zertifikate aufzuzaehlen."
            ),
        },
    ]

    frontmatter = _base_frontmatter("interview_prep", bundle, analysis)
    body = {"title": f"Interviewvorbereitung - {analysis.title or 'Zielrolle'}", "sections": questions}
    markdown = _render_sections(frontmatter, body["title"], body["sections"])
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)


def _culture_profile(job_analysis: JobAnalysis) -> Dict[str, str]:
    joined = normalize_text(" ".join([job_analysis.title, job_analysis.summary, *job_analysis.keywords, *job_analysis.matched_terms]))
    if any(marker in joined for marker in ["bank", "finance", "versicherung", "compliance", "audit"]):
        return {
            "label": "konservativ-professionell",
            "outfit": "marineblauer oder dunkelgrauer Anzug, weisses Hemd, dezente Schuhe und kaum Muster",
            "tone": "klassisch, ruhig, praezise",
        }
    if any(marker in joined for marker in ["startup", "product", "scale", "innovation", "ai"]):
        return {
            "label": "modern-tech",
            "outfit": "dunkles Sakko oder gepflegtes Overshirt, helles Hemd oder feines T-Shirt, saubere Ledersneaker oder Loafer",
            "tone": "modern, reduziert, kompetent",
        }
    if any(marker in joined for marker in ["public", "health", "government", "agentur", "amt"]):
        return {
            "label": "serioes-oeffentlich",
            "outfit": "dunkles Sakko, helles Hemd oder Bluse, Stoffhose oder passender Anzug, dezente Farben",
            "tone": "vertrauenswuerdig, klar, unaufgeregt",
        }
    return {
        "label": "business-smart",
        "outfit": "dunkles Sakko, weisses oder hellblaues Hemd, Stoffhose, klassische Schuhe",
        "tone": "professionell, zugaenglich, sauber",
    }


def build_style_guide_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
) -> CVContent:
    presentation = bundle.profile.get("presentation_preferences", {}) or {}
    culture = _culture_profile(analysis)
    preferred_colors = ", ".join(presentation.get("preferred_colors", [])[:3]) or "Navy, Weiss, Grau"
    avoid = ", ".join(presentation.get("avoid", [])[:3]) or "laute Muster und zu sportliche Teile"
    notes = "; ".join(presentation.get("wardrobe_notes", [])[:3]) or "Ein sauberer, klarer Auftritt wirkt am staerksten."

    sections = [
        {
            "title": "Empfohlener Stil",
            "body": (
                f"Die Zielkultur wirkt **{culture['label']}**. Fuer dieses Umfeld passt am besten: "
                f"**{culture['outfit']}**."
            ),
        },
        {
            "title": "Farben und Wirkung",
            "body": (
                f"Bevorzugen Sie {preferred_colors}. Der Gesamteindruck sollte {culture['tone']} wirken. "
                f"Vermeiden Sie {avoid}."
            ),
        },
        {
            "title": "Praktische Hinweise",
            "body": (
                f"{notes} Stimmen Sie Frisur, Schuhe, Uhr und Tasche auf denselben ruhigen Gesamteindruck ab. "
                "Lieber etwas formeller starten und bei Bedarf vor Ort herunterstufen."
            ),
        },
    ]
    frontmatter = _base_frontmatter("style_guide", bundle, analysis)
    body = {"title": f"Styleguide - {analysis.title or 'Zielrolle'}", "sections": sections}
    markdown = _render_sections(frontmatter, body["title"], body["sections"])
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)


def build_learning_path_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> CVContent:
    career = bundle.profile.get("career_preferences", {}) or {}
    target_roles = career.get("target_roles", []) or bundle.profile.get("notes_for_cv_generation", {}).get("preferred_roles", [])
    selected_role = target_roles[0] if target_roles else analysis.title or "naechste Karrierestufe"
    priorities = unique(
        [
            *career.get("priority_focus", []),
            *analysis.keywords[:3],
        ]
    )[:4]
    suggested_certs = unique(
        [
            *career.get("certification_interests", []),
            *(certification.get("name", "") for certification in _selected_certifications(bundle, selection)),
        ]
    )[:4]
    cert_line = ", ".join(item for item in suggested_certs if item) or "zielgerichtete Security- und AI-Zertifizierungen"

    sections = [
        {
            "title": "Naechster sinnvoller Schritt",
            "body": (
                f"Der naechste logische Schritt ist eine Position in Richtung **{selected_role}**. "
                f"Die staerksten Hebel dafuer liegen in {', '.join(priorities) or 'Ihren Kernkompetenzen'}."
            ),
        },
        {
            "title": "Wie Sie dorthin kommen",
            "body": (
                "Bauen Sie gezielt sichtbare Referenzen auf, die fachliche Tiefe und Wirkung kombinieren: "
                "ein belastbares Projektbeispiel, ein klarer fachlicher Schwerpunkt und eine sichtbare Rolle in Standards, Coaching oder Automatisierung."
            ),
        },
        {
            "title": "Hilfreiche Zertifizierungen",
            "body": (
                f"Priorisieren Sie Zertifizierungen oder Lernpfade wie {cert_line}. "
                "Wichtig ist, dass jede Weiterbildung direkt in Projektpraxis oder Positionierung ueberfuehrt wird."
            ),
        },
    ]
    frontmatter = _base_frontmatter("learning_path", bundle, analysis)
    body = {"title": "Learning Path", "sections": sections}
    markdown = _render_sections(frontmatter, body["title"], body["sections"])
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)
