from __future__ import annotations

from typing import Dict, List, Tuple

from .models import CVContent, SourceBundle, ValidationReport
from .utils import split_frontmatter
from .writer import render_markdown


def _known_source_ids(bundle: SourceBundle) -> set[str]:
    ids = set()
    ids.update(experience["id"] for experience in bundle.profile.get("experience", []))
    ids.update(education["id"] for education in bundle.profile.get("education", []))
    ids.update(project["id"] for project in bundle.projects)
    ids.update(certification["id"] for certification in bundle.certifications)
    return ids


def validate_cv_content(bundle: SourceBundle, content: CVContent) -> Tuple[CVContent, ValidationReport]:
    corrections: List[str] = []
    known_ids = _known_source_ids(bundle)

    for key in ["selected_project_ids", "selected_certification_ids", "selected_experience_ids"]:
        filtered_ids = [item for item in content.frontmatter.get(key, []) if item in known_ids]
        if filtered_ids != content.frontmatter.get(key, []):
            corrections.append(f"Unbekannte Referenzen aus {key} entfernt.")
            content.frontmatter[key] = filtered_ids

    for experience in content.body.get("experiences", []):
        cleaned_highlights = []
        for highlight in experience.get("highlights", []):
            source_id = highlight.get("source_id")
            if source_id in known_ids:
                cleaned_highlights.append(highlight)
            else:
                corrections.append(f"Highlight mit unbekannter Quelle '{source_id}' entfernt.")
        experience["highlights"] = cleaned_highlights

    expected_markdown = render_markdown(content.frontmatter, content.body)
    if content.markdown != expected_markdown:
        corrections.append("Markdown auf kanonische, quellengebundene Darstellung zurueckgesetzt.")
        content.markdown = expected_markdown

    frontmatter, _ = split_frontmatter(content.markdown)
    if frontmatter.get("validated") is not True:
        content.frontmatter["validated"] = True
        content.markdown = render_markdown(content.frontmatter, content.body)

    return content, ValidationReport(passed=True, corrections=corrections)
