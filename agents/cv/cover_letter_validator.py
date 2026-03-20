from __future__ import annotations

from typing import List, Tuple

from .cover_letter import render_cover_letter_markdown
from .models import CVContent, SourceBundle, ValidationReport
from .utils import split_frontmatter


def _known_source_ids(bundle: SourceBundle) -> set[str]:
    ids = {project["id"] for project in bundle.projects}
    ids.update(certification["id"] for certification in bundle.certifications)
    return ids


def validate_cover_letter(bundle: SourceBundle, content: CVContent) -> Tuple[CVContent, ValidationReport]:
    known_ids = _known_source_ids(bundle)
    corrections: List[str] = []

    for key in ["selected_project_ids", "selected_certification_ids"]:
        filtered_ids = [item for item in content.frontmatter.get(key, []) if item in known_ids]
        if filtered_ids != content.frontmatter.get(key, []):
            content.frontmatter[key] = filtered_ids
            corrections.append(f"Unbekannte Referenzen aus {key} entfernt.")

    for key in ["fit_points", "certification_points"]:
        cleaned_items = []
        for item in content.body.get(key, []):
            source_id = item.get("source_id")
            if source_id in known_ids:
                cleaned_items.append(item)
            else:
                corrections.append(f"Punkt mit unbekannter Quelle '{source_id}' entfernt.")
        content.body[key] = cleaned_items

    expected_markdown = render_cover_letter_markdown(content.frontmatter, content.body)
    if content.markdown != expected_markdown:
        content.markdown = expected_markdown
        corrections.append("Anschreiben-Markdown auf kanonische Darstellung zurueckgesetzt.")

    frontmatter, _ = split_frontmatter(content.markdown)
    if frontmatter.get("validated") is not True:
        content.frontmatter["validated"] = True
        content.markdown = render_cover_letter_markdown(content.frontmatter, content.body)

    return content, ValidationReport(passed=True, corrections=corrections)
