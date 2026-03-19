from __future__ import annotations

from typing import List

from .models import JsonDict
from .utils import unique


def available_cv_variants(profile: JsonDict) -> List[str]:
    variants = profile.get("notes_for_cv_generation", {}).get("cv_variants", {})
    if not isinstance(variants, dict):
        return []
    return [name for name, config in variants.items() if isinstance(name, str) and isinstance(config, dict)]


def resolve_cv_variant(profile: JsonDict, variant_name: str | None) -> JsonDict:
    if not variant_name:
        return {}

    variants = profile.get("notes_for_cv_generation", {}).get("cv_variants", {})
    if not isinstance(variants, dict):
        return {}

    variant = variants.get(variant_name)
    if not isinstance(variant, dict):
        return {}
    return variant


def variant_terms(profile: JsonDict, variant_name: str | None) -> List[str]:
    variant = resolve_cv_variant(profile, variant_name)
    if not variant:
        return []

    terms = []
    title = variant.get("title")
    if isinstance(title, str) and title.strip():
        terms.append(title.strip())

    for key in ["keywords", "preferred_roles"]:
        for item in variant.get(key, []) or []:
            if isinstance(item, str) and item.strip():
                terms.append(item.strip())

    return unique(terms)
