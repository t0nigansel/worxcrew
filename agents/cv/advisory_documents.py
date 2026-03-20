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


def _content_language(analysis: JobAnalysis) -> str:
    return "en" if analysis.language == "en" else "de"


def _culture_profile(job_analysis: JobAnalysis, language: str) -> Dict[str, str]:
    joined = normalize_text(" ".join([job_analysis.title, job_analysis.summary, *job_analysis.keywords, *job_analysis.matched_terms]))
    if any(marker in joined for marker in ["bank", "finance", "versicherung", "compliance", "audit"]):
        if language == "en":
            return {
                "label": "conservative-professional",
                "outfit": "navy or dark-gray suit, white shirt, subtle shoes, and minimal patterns",
                "tone": "classic, calm, precise",
            }
        return {
            "label": "konservativ-professionell",
            "outfit": "marineblauer oder dunkelgrauer Anzug, weisses Hemd, dezente Schuhe und kaum Muster",
            "tone": "klassisch, ruhig, praezise",
        }
    if any(marker in joined for marker in ["startup", "product", "scale", "innovation", "ai"]):
        if language == "en":
            return {
                "label": "modern-tech",
                "outfit": "dark blazer or clean overshirt, light shirt or quality T-shirt, and neat leather sneakers or loafers",
                "tone": "modern, focused, competent",
            }
        return {
            "label": "modern-technisch",
            "outfit": "dunkles Sakko oder gepflegtes Overshirt, helles Hemd oder feines T-Shirt, saubere Ledersneaker oder Loafer",
            "tone": "modern, reduziert, kompetent",
        }
    if any(marker in joined for marker in ["public", "health", "government", "agentur", "amt"]):
        if language == "en":
            return {
                "label": "public-service formal",
                "outfit": "dark blazer, light shirt or blouse, tailored trousers or matching suit, and subtle colors",
                "tone": "trustworthy, clear, composed",
            }
        return {
            "label": "serioes-oeffentlich",
            "outfit": "dunkles Sakko, helles Hemd oder Bluse, Stoffhose oder passender Anzug, dezente Farben",
            "tone": "vertrauenswuerdig, klar, unaufgeregt",
        }
    if language == "en":
        return {
            "label": "business-smart",
            "outfit": "dark blazer, white or light-blue shirt, tailored trousers, and classic shoes",
            "tone": "professional, approachable, polished",
        }
    return {
        "label": "business-formell",
        "outfit": "dunkles Sakko, weisses oder hellblaues Hemd, Stoffhose, klassische Schuhe",
        "tone": "professionell, zugaenglich, sauber",
    }


def build_style_guide_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
) -> CVContent:
    language = _content_language(analysis)
    presentation = bundle.profile.get("presentation_preferences", {}) or {}
    culture = _culture_profile(analysis, language)

    if language == "en":
        preferred_colors = ", ".join(presentation.get("preferred_colors", [])[:3]) or "Navy, white, gray"
        avoid = ", ".join(presentation.get("avoid", [])[:3]) or "loud patterns and overly sporty pieces"
        notes = "; ".join(presentation.get("wardrobe_notes", [])[:3]) or "A clean, coherent appearance has the strongest effect."
        sections = [
            {
                "title": "Recommended Style",
                "body": (
                    f"The target culture appears **{culture['label']}**. The best fit for this environment is: "
                    f"**{culture['outfit']}**."
                ),
            },
            {
                "title": "Colors and Impression",
                "body": (
                    f"Prefer {preferred_colors}. Your overall presence should feel {culture['tone']}. "
                    f"Avoid {avoid}."
                ),
            },
            {
                "title": "Practical Notes",
                "body": (
                    f"{notes} Align hairstyle, shoes, watch, and bag to the same calm overall impression. "
                    "Start slightly more formal and dial down only if the on-site context suggests it."
                ),
            },
        ]
        title = f"Style Guide - {analysis.title or 'Target Role'}"
    else:
        preferred_colors = ", ".join(presentation.get("preferred_colors", [])[:3]) or "Marineblau, Weiss, Grau"
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
        title = f"Styleguide - {analysis.title or 'Zielrolle'}"

    frontmatter = _base_frontmatter("style_guide", bundle, analysis)
    body = {"title": title, "sections": sections}
    markdown = _render_sections(frontmatter, body["title"], body["sections"])
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)


def _pick_three_certifications(cert_pool: List[str], keyword_markers: List[str], defaults: List[str]) -> List[str]:
    preferred = [
        certification
        for certification in cert_pool
        if any(marker in normalize_text(certification) for marker in keyword_markers)
    ]
    selected = unique([*preferred, *defaults])
    for item in defaults:
        if len(selected) >= 3:
            break
        if item not in selected:
            selected.append(item)
    return selected[:3]


def build_learning_path_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> CVContent:
    language = _content_language(analysis)
    career = bundle.profile.get("career_preferences", {}) or {}
    target_roles = career.get("target_roles", []) or bundle.profile.get("notes_for_cv_generation", {}).get("preferred_roles", [])
    selected_role = target_roles[0] if target_roles else analysis.title or "naechste Karrierestufe"
    priorities = unique(
        [
            *career.get("priority_focus", []),
            *analysis.keywords[:4],
        ]
    )[:4]
    cert_pool = unique(
        [
            *career.get("certification_interests", []),
            *(certification.get("name", "") for certification in _selected_certifications(bundle, selection)),
            *(certification.get("name", "") for certification in bundle.certifications),
        ],
    )
    cert_pool = [item for item in cert_pool if str(item).strip()]
    priority_line = ", ".join(priorities[:3]) or ("Ihren Kernkompetenzen" if language == "de" else "your core strengths")
    selected_projects = _selected_projects(bundle, selection)
    project_names = [str(project.get("name", "")).strip() for project in selected_projects if project.get("name")]
    project_line = ", ".join(project_names[:2]) or (
        "vergleichbaren Projekten" if language == "de" else "comparable projects"
    )

    joined = normalize_text(" ".join([analysis.title, analysis.summary, *analysis.keywords, *analysis.matched_terms]))
    specialization_key = "performance"
    if any(marker in joined for marker in ["security", "appsec", "owasp", "threat", "compliance"]):
        specialization_key = "security"
    elif any(marker in joined for marker in ["ai", "ml", "llm", "machine learning", "data"]):
        specialization_key = "ai"
    elif any(marker in joined for marker in ["platform", "devops", "cloud", "kubernetes"]):
        specialization_key = "platform"

    if language == "en":
        specialization_label_map = {
            "security": "Security Engineering",
            "ai": "AI Engineering",
            "platform": "Platform Engineering",
            "performance": "Performance Engineering",
        }
        specialization_defaults_map = {
            "security": ["CCSP", "GIAC GWAPT", "Kubernetes and Cloud Native Security Associate (KCSA)"],
            "ai": ["Microsoft Azure AI Engineer Associate", "Databricks Data Engineer Associate", "NVIDIA Generative AI Associate"],
            "platform": ["Certified Kubernetes Administrator (CKA)", "HashiCorp Terraform Associate", "AWS DevOps Engineer - Professional"],
            "performance": ["Google Professional Cloud DevOps Engineer", "AWS Solutions Architect - Professional", "Linux Foundation CKA"],
        }
    else:
        specialization_label_map = {
            "security": "Security Engineering",
            "ai": "AI Engineering",
            "platform": "Platform Engineering",
            "performance": "Performance Engineering",
        }
        specialization_defaults_map = {
            "security": ["CCSP", "GIAC GWAPT", "Kubernetes and Cloud Native Security Associate (KCSA)"],
            "ai": ["Microsoft Azure AI Engineer Associate", "Databricks Data Engineer Associate", "NVIDIA Generative AI Associate"],
            "platform": ["Certified Kubernetes Administrator (CKA)", "HashiCorp Terraform Associate", "AWS DevOps Engineer - Professional"],
            "performance": ["Google Professional Cloud DevOps Engineer", "AWS Solutions Architect - Professional", "Linux Foundation CKA"],
        }

    tech_certs = _pick_three_certifications(
        cert_pool,
        ["cloud", "aws", "azure", "kubernetes", "architecture", "security", "devops"],
        ["AWS Solutions Architect - Professional", "Certified Kubernetes Administrator (CKA)", "Google Professional Cloud Architect"],
    )
    management_certs = _pick_three_certifications(
        cert_pool,
        ["scrum", "prince", "itil", "pmp", "lead", "management"],
        ["Professional Scrum Master I (PSM I)", "PRINCE2 Foundation", "ITIL 4 Foundation"],
    )
    specialization_certs = _pick_three_certifications(
        cert_pool,
        [specialization_key, "security", "ai", "platform", "performance", "devops", "cloud"],
        specialization_defaults_map[specialization_key],
    )
    specialization_label = specialization_label_map[specialization_key]

    if language == "en":
        sections = [
            {
                "title": "Path 1 - Tech Expert Track",
                "body": (
                    f"**High-level role description:** Senior technical role (Principal/Staff level) with ownership of architecture and difficult delivery decisions for **{selected_role}**.\n\n"
                    f"**Why the candidate fits:** Strong project evidence from {project_line} and alignment with target priorities such as {priority_line}.\n\n"
                    "**To-do list:**\n"
                    "- Skills to build: Architecture communication for non-technical stakeholders, platform economics, strategic roadmap framing.\n"
                    "- Skills to strengthen: System design, cloud security, automation depth, mentoring by technical example.\n"
                    "- Can be deprioritized: Broad administrative leadership tasks without direct technical leverage.\n\n"
                    "**Three useful certifications for this path:**\n"
                    f"1. {tech_certs[0]}\n"
                    f"2. {tech_certs[1]}\n"
                    f"3. {tech_certs[2]}"
                ),
            },
            {
                "title": "Path 2 - Management Track",
                "body": (
                    "**High-level role description:** Engineering Manager / Team Lead role focused on people leadership, prioritization, and cross-functional delivery.\n\n"
                    f"**Why the candidate fits:** The profile indicates practical delivery leadership and stakeholder communication in contexts similar to {project_line}.\n\n"
                    "**To-do list:**\n"
                    "- Skills to build: Hiring and coaching framework, structured feedback cycles, budget and capacity planning.\n"
                    "- Skills to strengthen: Stakeholder alignment, roadmap trade-off decisions, delivery risk management.\n"
                    "- Can be deprioritized: Deep low-level specialization that does not improve team outcomes.\n\n"
                    "**Three useful certifications for this path:**\n"
                    f"1. {management_certs[0]}\n"
                    f"2. {management_certs[1]}\n"
                    f"3. {management_certs[2]}"
                ),
            },
            {
                "title": f"Path 3 - Specialization Track ({specialization_label})",
                "body": (
                    f"**High-level role description:** Specialist role with clear ownership in **{specialization_label}** and measurable impact on quality, risk, or speed.\n\n"
                    f"**Why the candidate fits:** Existing strengths and project evidence indicate that a focused specialization around {priority_line} is realistic.\n\n"
                    "**To-do list:**\n"
                    "- Skills to build: Deeper domain methods, reusable specialist patterns, and visible thought leadership.\n"
                    "- Skills to strengthen: Toolchain mastery in the chosen domain and reproducible delivery blueprints.\n"
                    "- Can be deprioritized: Generalist breadth that does not support the specialization target.\n\n"
                    "**Three useful certifications for this path:**\n"
                    f"1. {specialization_certs[0]}\n"
                    f"2. {specialization_certs[1]}\n"
                    f"3. {specialization_certs[2]}"
                ),
            },
        ]
        title = "Career Paths"
    else:
        sections = [
            {
                "title": "Pfad 1 - Tech-Expertenpfad",
                "body": (
                    f"**Grobe Jobbeschreibung:** Senior-technische Rolle (Principal/Staff) mit Verantwortung fuer Architektur und schwierige Delivery-Entscheidungen in Richtung **{selected_role}**.\n\n"
                    f"**Warum der Kandidat dazu passt:** Belastbare Projektreferenzen aus {project_line} und ein klarer Fit zu Prioritaeten wie {priority_line}.\n\n"
                    "**ToDo-Liste:**\n"
                    "- Skills aufbauen: Architekturkommunikation fuer nicht-technische Stakeholder, Plattformoekonomie, strategische Roadmap-Argumentation.\n"
                    "- Skills staerken: Systemdesign, Cloud-Security, Automatisierungstiefe, Mentoring ueber technische Fuehrung.\n"
                    "- Kann vernachlaessigt werden: Breite administrative Fuehrungsaufgaben ohne direkten technischen Hebel.\n\n"
                    "**3 sinnvolle Zertifizierungen fuer diesen Pfad:**\n"
                    f"1. {tech_certs[0]}\n"
                    f"2. {tech_certs[1]}\n"
                    f"3. {tech_certs[2]}"
                ),
            },
            {
                "title": "Pfad 2 - Managementpfad",
                "body": (
                    "**Grobe Jobbeschreibung:** Engineering Manager / Team Lead mit Fokus auf People Leadership, Priorisierung und bereichsuebergreifende Delivery.\n\n"
                    f"**Warum der Kandidat dazu passt:** Das Profil zeigt wiederkehrend Delivery-Verantwortung und Stakeholder-Kommunikation in Umfeldern wie {project_line}.\n\n"
                    "**ToDo-Liste:**\n"
                    "- Skills aufbauen: Hiring- und Coaching-Framework, strukturierte Feedback-Zyklen, Budget- und Kapazitaetsplanung.\n"
                    "- Skills staerken: Stakeholder-Abstimmung, Roadmap-Trade-offs, aktives Delivery-Risikomanagement.\n"
                    "- Kann vernachlaessigt werden: Tiefe Low-Level-Spezialisierung ohne Beitrag zur Teamwirkung.\n\n"
                    "**3 sinnvolle Zertifizierungen fuer diesen Pfad:**\n"
                    f"1. {management_certs[0]}\n"
                    f"2. {management_certs[1]}\n"
                    f"3. {management_certs[2]}"
                ),
            },
            {
                "title": f"Pfad 3 - Spezialisierungspfad ({specialization_label})",
                "body": (
                    f"**Grobe Jobbeschreibung:** Spezialistenrolle mit klarer Ownership in **{specialization_label}** und messbarem Beitrag zu Qualitaet, Risiko oder Geschwindigkeit.\n\n"
                    f"**Warum der Kandidat dazu passt:** Vorhandene Staerken und Projekterfahrung zeigen, dass eine fokussierte Spezialisierung rund um {priority_line} realistisch ist.\n\n"
                    "**ToDo-Liste:**\n"
                    "- Skills aufbauen: Tiefere Domainenmethodik, wiederverwendbare Spezialistenmuster, sichtbare fachliche Positionierung.\n"
                    "- Skills staerken: Toolchain-Beherrschung im Schwerpunkt und reproduzierbare Delivery-Blueprints.\n"
                    "- Kann vernachlaessigt werden: Generalistische Breite ohne direkten Beitrag zum Spezialisierungsziel.\n\n"
                    "**3 sinnvolle Zertifizierungen fuer diesen Pfad:**\n"
                    f"1. {specialization_certs[0]}\n"
                    f"2. {specialization_certs[1]}\n"
                    f"3. {specialization_certs[2]}"
                ),
            },
        ]
        title = "Learning Path"

    frontmatter = _base_frontmatter("learning_path", bundle, analysis)
    body = {"title": title, "sections": sections}
    markdown = _render_sections(frontmatter, body["title"], body["sections"])
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)
