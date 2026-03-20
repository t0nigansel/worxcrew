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


def build_interview_questions(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> List[Dict[str, object]]:
    projects = _selected_projects(bundle, selection)
    certifications = _selected_certifications(bundle, selection)
    project_names = ", ".join(project.get("name", "") for project in projects[:2] if project.get("name"))
    cert_names = ", ".join(cert.get("name", "") for cert in certifications[:2] if cert.get("name"))
    keyword_focus = ", ".join(analysis.keywords[:3]) or "Ihre Kernkompetenzen"

    return [
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


def _company_signal_profile(analysis: JobAnalysis) -> Dict[str, str]:
    joined = normalize_text(
        " ".join([analysis.title, analysis.summary, analysis.raw_text, *analysis.keywords, *analysis.matched_terms])
    )

    regulated_markers = [
        "bank", "finance", "versicherung", "insur", "compliance", "audit", "risk", "regulator", "aufsicht",
        "governance",
    ]
    growth_markers = [
        "startup", "product", "platform", "scale", "saas", "innovation", "growth", "roadmap",
    ]
    enterprise_markers = [
        "transformation", "stakeholder", "matrix", "governance", "enterprise", "programm", "portfolio",
    ]

    if any(marker in joined for marker in regulated_markers):
        return {
            "context": "Die Stellenanzeige deutet auf ein reguliertes, risiko-sensitives Umfeld mit hoher Nachvollziehbarkeit hin.",
            "priorities": "Wahrscheinliche Prioritaeten: Stabilitaet, Compliance, Risiko-Reduktion, belastbare Prozesse und klare Verantwortlichkeiten.",
            "stakeholders": "Wahrscheinliche Stakeholder: Hiring Manager, Fachbereich, Security/Compliance und ggf. Audit-nahe Rollen.",
            "tone": "Voraussichtlicher Interviewton: strukturiert, formal, evidenzbasiert und risiko-orientiert.",
        }
    if any(marker in joined for marker in growth_markers):
        return {
            "context": "Die Stellenanzeige deutet auf ein produktnahes Wachstumsumfeld mit schneller Iteration hin.",
            "priorities": "Wahrscheinliche Prioritaeten: Time-to-Value, Produktwirkung, pragmatische Automatisierung und Teamgeschwindigkeit.",
            "stakeholders": "Wahrscheinliche Stakeholder: Engineering Lead, Product Manager und ggf. Plattform-/Security-Verantwortliche.",
            "tone": "Voraussichtlicher Interviewton: direkt, loesungsorientiert, impact-fokussiert.",
        }
    if any(marker in joined for marker in enterprise_markers):
        return {
            "context": "Die Stellenanzeige deutet auf ein groesseres Unternehmensumfeld mit mehreren Abstimmungsachsen hin.",
            "priorities": "Wahrscheinliche Prioritaeten: bereichsuebergreifende Abstimmung, Governance-Fit, planbare Delivery und nachhaltige Architektur.",
            "stakeholders": "Wahrscheinliche Stakeholder: Team Lead, Programm-/Projektverantwortliche, Architektur und angrenzende Fachbereiche.",
            "tone": "Voraussichtlicher Interviewton: professionell, stakeholder-orientiert, auf Skalierbarkeit und Umsetzbarkeit fokussiert.",
        }
    return {
        "context": "Die Stellenanzeige deutet auf ein klassisches Delivery-Umfeld mit Bedarf an fachlicher Tiefe und Zusammenarbeit hin.",
        "priorities": "Wahrscheinliche Prioritaeten: verlaessliche Umsetzung, technische Qualitaet, Zusammenarbeit und sichtbare Ergebniswirkung.",
        "stakeholders": "Wahrscheinliche Stakeholder: Hiring Manager, direkte Teamkollegen und relevante Schnittstellen im Delivery-Prozess.",
        "tone": "Voraussichtlicher Interviewton: professionell, fachlich, praxisnah.",
    }


def _profile_fit_points(bundle: SourceBundle, analysis: JobAnalysis, selection: EvidenceSelection) -> List[str]:
    projects = _selected_projects(bundle, selection)
    certifications = _selected_certifications(bundle, selection)

    project_names = [str(project.get("name", "")).strip() for project in projects if project.get("name")]
    cert_names = [str(certification.get("name", "")).strip() for certification in certifications if certification.get("name")]
    focus_areas = [
        str(item).strip()
        for item in (bundle.profile.get("branding", {}).get("focus_areas", []) or [])
        if str(item).strip()
    ]
    keywords = [str(item).strip() for item in analysis.keywords if str(item).strip()]

    points: List[str] = []
    if project_names:
        points.append(f"Verknuepfen Sie Ihre Wirkung mit konkreten Referenzen aus {', '.join(project_names[:2])}.")
    if focus_areas:
        points.append(f"Positionieren Sie sich klar ueber Ihre Staerken in {', '.join(focus_areas[:2])}.")
    if cert_names:
        points.append(f"Nutzen Sie Weiterbildungen wie {', '.join(cert_names[:2])} als Beleg fuer aktualisierte Fachpraxis.")
    if keywords:
        points.append(f"Spiegeln Sie die Anforderungssprache der Anzeige durch klare Beispiele zu {', '.join(keywords[:2])}.")

    while len(points) < 3:
        points.append("Nutzen Sie kurze, messbare Projektbeispiele und benennen Sie den konkreten Ergebnisbeitrag.")
    return points[:3]


def build_company_briefing(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> List[Dict[str, object]]:
    profile = _company_signal_profile(analysis)
    fit_points = _profile_fit_points(bundle, analysis, selection)

    return [
        {
            "title": "Company Briefing - Kontext",
            "body": (
                "Diese Einschaetzung ist aus der Stellenanzeige und Ihrem Profil abgeleitet "
                "(ohne externe Unternehmensrecherche).\n\n"
                f"{profile['context']}"
            ),
        },
        {
            "title": "Company Briefing - Prioritaeten",
            "body": profile["priorities"],
        },
        {
            "title": "Company Briefing - Stakeholder",
            "body": profile["stakeholders"],
        },
        {
            "title": "Company Briefing - Interviewton",
            "body": profile["tone"],
        },
        {
            "title": "Company Briefing - So sollten Sie sich positionieren",
            "body": "\n".join([
                "Betonen Sie im Gespraech diese drei Punkte:",
                "",
                *(f"- {point}" for point in fit_points),
            ]),
        },
    ]


def build_interview_prep_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> CVContent:
    questions = build_interview_questions(bundle, analysis, selection)
    company_briefing = build_company_briefing(bundle, analysis, selection)
    sections = [*questions, *company_briefing]

    frontmatter = _base_frontmatter("interview_prep", bundle, analysis)
    body = {"title": f"Interviewvorbereitung - {analysis.title or 'Zielrolle'}", "sections": sections}
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
    priority_line = ", ".join(priorities) or "Ihren Kernkompetenzen"

    sections = [
        {
            "title": "Route 1 - Tech-Expert Track",
            "body": (
                f"**Naechste Rolle:** Principal Engineer / Staff Engineer in Richtung **{selected_role}**.\n\n"
                f"**Wie Sie dorthin kommen:** Positionieren Sie sich als tiefes technisches Rueckgrat mit Fokus auf {priority_line}. "
                "Uebernehmen Sie Architekturverantwortung, technische Leitplanken und schwierige Delivery-Entscheidungen.\n\n"
                f"**Hilfreiche Zertifizierungen:** {cert_line} (mit Schwerpunkt auf Architektur, Cloud und Security)."
            ),
        },
        {
            "title": "Route 2 - Management Track",
            "body": (
                f"**Naechste Rolle:** Engineering Manager / Team Lead mit Bruecke zwischen Technik und Business.\n\n"
                "**Wie Sie dorthin kommen:** Verstaerken Sie People- und Stakeholder-Fuehrung: Roadmaps priorisieren, "
                "Team-Entwicklung steuern, Hiring/Coaching sichtbar uebernehmen und Delivery-Risiken frueh moderieren.\n\n"
                "**Hilfreiche Zertifizierungen:** Scrum.org, PRINCE2/PMP, ITIL oder Leadership-Programme (komplementaer zu Ihrer Technik-Story)."
            ),
        },
        {
            "title": "Route 3 - Specialization Track",
            "body": (
                f"**Naechste Rolle:** Spezialist in einem klaren Vertikalthema (z. B. AppSec, AI Security, Platform Automation oder Performance Engineering).\n\n"
                f"**Wie Sie dorthin kommen:** Waehlen Sie ein Thema aus {priority_line} als klare Nische und bauen Sie dort eine sichtbare Referenzspur "
                "(Best Practices, interne Standards, Fachbeitraege, wiederholbare Projekt-Blueprints).\n\n"
                f"**Hilfreiche Zertifizierungen:** {cert_line}; priorisieren Sie nur Zertifikate mit direktem Transfer in reale Projektwirkung."
            ),
        },
    ]
    frontmatter = _base_frontmatter("learning_path", bundle, analysis)
    body = {"title": "Learning Path", "sections": sections}
    markdown = _render_sections(frontmatter, body["title"], body["sections"])
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)
