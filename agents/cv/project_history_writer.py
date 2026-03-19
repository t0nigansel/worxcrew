"""Compose structured content for the project history attachment."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import CVContent, EvidenceSelection, JobAnalysis, SourceBundle
from .utils import dump_frontmatter, month_label, normalize_text, truncate_text, unique
from .writer import _contact_line, _headline, _link_items, _project_badge


def _sort_projects_reverse_chronological(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort projects by period.end descending, then period.start descending."""

    def _sort_key(project: Dict[str, Any]) -> tuple[str, str]:
        period = project.get("period", {}) or {}
        end = str(period.get("end", "") or "")
        start = str(period.get("start", "") or "")
        # Negate by using ~ prefix trick won't work for dates; just reverse sort
        return (end, start)

    return sorted(projects, key=_sort_key, reverse=True)


def _compose_project_entry(
    project: Dict[str, Any],
    analysis: JobAnalysis,
) -> Dict[str, Any]:
    """Build a single project entry with full detail for the history attachment."""
    period = project.get("period", {}) or {}
    start = str(period.get("start", "") or "")
    end = str(period.get("end", "") or "")
    period_label = ""
    if start or end:
        period_label = f"{month_label(start)} - {month_label(end)}".strip(" -")

    responsibilities = []
    for item in project.get("responsibilities", []) or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "") or "").strip()
        description = str(item.get("description", "") or "").strip()
        if title:
            responsibilities.append({"title": title, "description": description})

    tools = project.get("tools", []) or []

    badge_label, badge_tone = _project_badge(project, analysis)

    return {
        "project_id": str(project.get("id", "")),
        "name": str(project.get("name", "")),
        "client": str(project.get("client", "")),
        "role": str(project.get("role", "")),
        "period": period_label,
        "methodology": str(project.get("methodology", "") or ""),
        "system_purpose": str(project.get("system_purpose", "") or "").strip(),
        "description": str(project.get("description", "") or "").strip(),
        "responsibilities": responsibilities,
        "tools": tools,
        "tools_line": ", ".join(tools),
        "badge_label": badge_label,
        "badge_tone": badge_tone,
    }


def compose_project_history(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
) -> Dict[str, Any]:
    """Build the full project history data structure for the attachment."""
    person = bundle.profile.get("person", {})
    sorted_projects = _sort_projects_reverse_chronological(bundle.projects)

    entries = [_compose_project_entry(project, analysis) for project in sorted_projects]

    return {
        "full_name": person.get("name", {}).get("full", ""),
        "headline": _headline(bundle, analysis),
        "contact_line": _contact_line(bundle),
        "links": _link_items(bundle),
        "language": analysis.language,
        "project_count": len(entries),
        "projects": entries,
    }


def build_project_history_content(
    bundle: SourceBundle,
    analysis: JobAnalysis,
    selection: EvidenceSelection,
    layout_name: str = "reference",
) -> CVContent:
    """Build a CVContent object for the project history attachment."""
    person = bundle.profile.get("person", {})
    history = compose_project_history(bundle, analysis, selection)

    frontmatter = {
        "document_type": "project_history",
        "language": analysis.language,
        "validated": False,
        "full_name": person.get("name", {}).get("full", ""),
        "headline": _headline(bundle, analysis),
        "job_title": analysis.title,
        "variant": analysis.variant or "",
        "layout": layout_name or "reference",
    }

    body = history
    body["layout"] = layout_name or "reference"
    body["portrait_path"] = str(bundle.portrait_path)

    markdown = render_project_history_markdown(frontmatter, body)
    return CVContent(frontmatter=frontmatter, body=body, markdown=markdown)


def render_project_history_markdown(
    frontmatter: Dict[str, Any],
    body: Dict[str, Any],
) -> str:
    """Render a markdown representation of the project history."""
    lines = [
        "---",
        dump_frontmatter(frontmatter),
        "---",
        "",
        f"# Projekthistorie — {body['full_name']}",
        "",
        f"**{body['headline']}**",
        "",
        body.get("contact_line", ""),
        "",
    ]

    for project in body.get("projects", []):
        lines.append(f"## {project['name']}")
        lines.append("")

        meta_parts = [
            project.get("client"),
            project.get("role"),
            project.get("period"),
            project.get("methodology"),
        ]
        lines.append(" | ".join(part for part in meta_parts if part))
        lines.append("")

        if project.get("system_purpose"):
            lines.append(f"**Kontext:** {project['system_purpose']}")
            lines.append("")

        if project.get("responsibilities"):
            for resp in project["responsibilities"]:
                lines.append(f"### {resp['title']}")
                if resp.get("description"):
                    lines.append("")
                    lines.append(resp["description"])
                lines.append("")

        if project.get("tools_line"):
            lines.append(f"**Tools:** {project['tools_line']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
