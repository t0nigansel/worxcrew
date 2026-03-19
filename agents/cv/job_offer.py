from __future__ import annotations

from collections import Counter
import re
from typing import List, Set

from .models import JobAnalysis, SourceBundle
from .utils import flatten_strings, normalize_text, tokenize, unique
from .variants import resolve_cv_variant, variant_terms


STOPWORDS: Set[str] = {
    "and",
    "are",
    "das",
    "dem",
    "den",
    "der",
    "die",
    "ein",
    "eine",
    "einer",
    "eines",
    "fuer",
    "fur",
    "im",
    "in",
    "ist",
    "mit",
    "oder",
    "our",
    "team",
    "the",
    "und",
    "von",
    "wir",
    "zu",
}

GERMAN_MARKERS: Set[str] = {
    "der",
    "die",
    "das",
    "und",
    "mit",
    "fuer",
    "für",
    "erfahrung",
    "wichtig",
    "umgebung",
    "tests",
}

ENGLISH_MARKERS: Set[str] = {
    "experience",
    "responsibilities",
    "requirements",
    "testing",
    "engineer",
    "with",
    "performance",
}

TITLE_HINTS: Set[str] = {
    "ai",
    "analyst",
    "appsec",
    "automation",
    "consultant",
    "developer",
    "engineer",
    "manager",
    "qa",
    "security",
    "specialist",
    "tester",
}

TITLE_CONTEXT_HINTS: Set[str] = {
    "aktuell suchen wir",
    "wir suchen",
    "suchen wir",
    "for a",
    "for an",
    "looking for",
}

TITLE_NOISE_PREFIXES: Set[str] = {
    "aktuell suchen wir",
    "bei stellen",
    "da wir",
    "dein aufgabengebiet",
    "dein profil",
    "die hamburg commercial bank",
    "fuer diese konstante weiterentwicklung",
    "im sinne",
    "unser angebot",
    "willkommen bei",
    "wir freuen uns",
    "wir setzen uns",
    "wir sind",
}


def candidate_terms(bundle: SourceBundle, variant_name: str | None = None) -> List[str]:
    profile = bundle.profile
    candidates = []
    candidates.extend(profile.get("branding", {}).get("focus_areas", []))
    candidates.extend(profile.get("notes_for_cv_generation", {}).get("positioning_keywords", []))
    candidates.extend(profile.get("notes_for_cv_generation", {}).get("preferred_roles", []))
    candidates.extend(variant_terms(profile, variant_name))
    candidates.extend(flatten_strings(profile.get("skills", {})))

    for project in bundle.projects:
        candidates.append(project.get("name", ""))
        candidates.append(project.get("role", ""))
        candidates.extend(project.get("tools", []))
        candidates.append(project.get("methodology", ""))

    for certification in bundle.certifications:
        candidates.append(certification.get("name", ""))
        candidates.extend(certification.get("skills", []))

    return unique(candidate.strip() for candidate in candidates if candidate and candidate.strip())


def detect_language(text: str) -> str:
    lowered = text.lower()
    tokens = set(tokenize(text))
    german_score = sum(1 for marker in GERMAN_MARKERS if normalize_text(marker) in tokens)
    english_score = sum(1 for marker in ENGLISH_MARKERS if normalize_text(marker) in tokens)
    if any(char in lowered for char in "äöüß"):
        german_score += 2
    if english_score > german_score:
        return "en"
    return "de"


def _clean_title_candidate(value: str) -> str:
    cleaned = " ".join(value.split()).strip(" -|,:")
    cleaned = re.sub(r"\((?:f/m/d|m/w/d|w/m/d)\)", "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()).strip(" -|,:")


def _extract_title_candidate(cleaned_text: str) -> str:
    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    best_candidate = ""
    best_score = -1

    for index, line in enumerate(lines):
        candidate = _clean_title_candidate(line)
        if not candidate:
            continue

        normalized = normalize_text(candidate)
        if not normalized or any(normalized.startswith(prefix) for prefix in TITLE_NOISE_PREFIXES):
            continue

        token_count = len(normalized.split())
        if token_count < 2 or token_count > 10:
            continue

        score = 0
        if any(hint in normalized.split() for hint in TITLE_HINTS):
            score += 4
        if len(candidate) <= 70:
            score += 1

        previous = normalize_text(lines[index - 1]) if index > 0 else ""
        if any(hint in previous for hint in TITLE_CONTEXT_HINTS):
            score += 5

        if re.search(r"\b(?:f/m/d|m/w/d|w/m/d)\b", line, flags=re.IGNORECASE):
            score += 2

        if ":" in candidate and not any(hint in normalized for hint in TITLE_HINTS):
            score -= 2

        if score > best_score:
            best_candidate = candidate
            best_score = score

    return best_candidate


def analyze_job_offer(text: str, bundle: SourceBundle, variant_name: str | None = None) -> JobAnalysis:
    cleaned_text = text.strip()
    variant = resolve_cv_variant(bundle.profile, variant_name)
    variant_keywords = [
        item.strip()
        for item in (variant.get("keywords", []) or [])
        if isinstance(item, str) and item.strip()
    ]
    variant_roles = [
        item.strip()
        for item in (variant.get("preferred_roles", []) or [])
        if isinstance(item, str) and item.strip()
    ]
    variant_summary_focus = str(variant.get("summary_focus", "") or "").strip()
    variant_title = str(variant.get("title", "") or "").strip()

    if not cleaned_text:
        profile = bundle.profile
        preferred_roles = unique(variant_roles + profile.get("notes_for_cv_generation", {}).get("preferred_roles", []))
        title = variant_title or (
            preferred_roles[0] if preferred_roles else profile.get("branding", {}).get("headline", "Senior Test Engineer")
        )
        base_keywords = profile.get("notes_for_cv_generation", {}).get("positioning_keywords", [])
        keywords = unique(variant_keywords + base_keywords)[:6]
        matched_terms = unique(variant_keywords + keywords)[:10]
        if variant_title:
            summary = (
                f"CV-Variante '{variant_name}' aktiv. Profil wird auf {variant_title} mit Fokus auf "
                f"{', '.join(keywords[:4]) or 'relevante Kernthemen'} ausgerichtet."
            )
        else:
            summary = "Kein Stellenangebot uebergeben. Es wird ein generischer, profilnaher CV erzeugt."
        return JobAnalysis(
            title=title,
            summary=summary,
            keywords=keywords,
            matched_terms=matched_terms,
            raw_text="",
            language="de",
            tone="direct",
            variant=variant_name if variant else None,
        )

    title_candidate = _extract_title_candidate(cleaned_text)
    title_candidate = title_candidate.split(".", 1)[0].strip()
    for separator in [" fuer ", " für ", " with ", " - ", " | ", ","]:
        if separator in title_candidate:
            title_candidate = title_candidate.split(separator, 1)[0].strip()
            break

    preferred_roles = unique(variant_roles + bundle.profile.get("notes_for_cv_generation", {}).get("preferred_roles", []))
    title = title_candidate if 4 <= len(title_candidate) <= 80 else (preferred_roles[0] if preferred_roles else "Tailored Role")

    raw_tokens = [token for token in tokenize(cleaned_text) if token not in STOPWORDS and len(token) > 2]
    token_counts = Counter(raw_tokens)
    variant_term_set = {normalize_text(item) for item in variant_terms(bundle.profile, variant_name)}

    scored_terms = []
    normalized_offer = normalize_text(cleaned_text)
    for candidate in candidate_terms(bundle, variant_name):
        normalized_candidate = normalize_text(candidate)
        if not normalized_candidate:
            continue

        score = 0.0
        if normalized_candidate in normalized_offer:
            score += max(3.0, len(normalized_candidate.split()))

        candidate_tokens = normalized_candidate.split()
        score += sum(token_counts.get(token, 0) for token in candidate_tokens) / 2
        if normalized_candidate in variant_term_set:
            score += 1.5
        if score > 0:
            scored_terms.append((candidate, score))

    scored_terms.sort(key=lambda item: (-item[1], item[0]))
    matched_terms = unique(term for term, _ in scored_terms)[:10]

    preferred_keywords = unique(variant_keywords + matched_terms)[:6]
    if not preferred_keywords:
        preferred_keywords = unique(token for token, count in token_counts.most_common(6) if count > 0)

    summary = (
        f"Stellenprofil '{title}' erkannt. Tailoring fokussiert auf "
        f"{', '.join(preferred_keywords[:4]) or 'relevante Kernthemen'}."
    )
    if variant_summary_focus:
        summary = f"{summary} Variant-Fokus: {variant_summary_focus}."

    return JobAnalysis(
        title=title,
        summary=summary,
        keywords=preferred_keywords,
        matched_terms=matched_terms,
        raw_text=cleaned_text,
        language=detect_language(cleaned_text),
        tone="direct",
        variant=variant_name if variant else None,
    )
