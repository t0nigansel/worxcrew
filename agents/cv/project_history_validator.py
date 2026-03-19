"""Validate the project history attachment against the JSON sources."""

from __future__ import annotations

from typing import List, Tuple

from .models import CVContent, SourceBundle, ValidationReport
from .project_history_writer import render_project_history_markdown
from .utils import split_frontmatter


def validate_project_history(
    bundle: SourceBundle,
    content: CVContent,
) -> Tuple[CVContent, ValidationReport]:
    """Verify that the project history content is fully backed by source data."""
    corrections: List[str] = []
    known_project_ids = {project["id"] for project in bundle.projects}

    # Remove any projects that don't exist in the source
    cleaned_projects = []
    for project in content.body.get("projects", []):
        project_id = project.get("project_id")
        if project_id in known_project_ids:
            cleaned_projects.append(project)
        else:
            corrections.append(
                f"Projekt mit unbekannter ID '{project_id}' aus Projekthistorie entfernt."
            )
    content.body["projects"] = cleaned_projects
    content.body["project_count"] = len(cleaned_projects)

    # Verify each project's responsibilities exist in source
    source_projects = {project["id"]: project for project in bundle.projects}
    for project in content.body.get("projects", []):
        project_id = project.get("project_id")
        source = source_projects.get(project_id)
        if not source:
            continue

        source_resp_titles = {
            str(item.get("title", "") or "").strip()
            for item in (source.get("responsibilities", []) or [])
            if isinstance(item, dict)
        }

        cleaned_responsibilities = []
        for resp in project.get("responsibilities", []):
            if resp.get("title") in source_resp_titles:
                cleaned_responsibilities.append(resp)
            else:
                corrections.append(
                    f"Verantwortung '{resp.get('title', '?')}' in Projekt '{project.get('name')}' "
                    f"nicht in Quelldaten gefunden."
                )
        project["responsibilities"] = cleaned_responsibilities

    # Re-render markdown to canonical form
    expected_markdown = render_project_history_markdown(content.frontmatter, content.body)
    if content.markdown != expected_markdown:
        corrections.append(
            "Projekthistorie-Markdown auf kanonische Darstellung zurueckgesetzt."
        )
        content.markdown = expected_markdown

    # Mark as validated
    frontmatter, _ = split_frontmatter(content.markdown)
    if frontmatter.get("validated") is not True:
        content.frontmatter["validated"] = True
        content.markdown = render_project_history_markdown(content.frontmatter, content.body)

    return content, ValidationReport(passed=True, corrections=corrections)
