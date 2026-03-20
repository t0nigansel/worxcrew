from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def normalize_text(value: str) -> str:
    lowered = unicodedata.normalize("NFKD", value.lower())
    lowered = "".join(char for char in lowered if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def tokenize(value: str) -> List[str]:
    return [token for token in normalize_text(value).split() if token]


def unique(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def flatten_strings(values: Any) -> List[str]:
    flattened: List[str] = []
    if isinstance(values, str):
        return [values]
    if isinstance(values, dict):
        for value in values.values():
            flattened.extend(flatten_strings(value))
        return flattened
    if isinstance(values, list):
        for value in values:
            flattened.extend(flatten_strings(value))
        return flattened
    return flattened


def month_label(value: str) -> str:
    if not value:
        return ""
    months = {
        "01": "01",
        "02": "02",
        "03": "03",
        "04": "04",
        "05": "05",
        "06": "06",
        "07": "07",
        "08": "08",
        "09": "09",
        "10": "10",
        "11": "11",
        "12": "12",
    }
    if len(value) == 7:
        year, month = value.split("-", 1)
        return f"{months.get(month, month)}/{year}"
    return value


def month_label_long(value: str) -> str:
    if not value:
        return ""
    months = {
        "01": "Januar",
        "02": "Februar",
        "03": "Marz",
        "04": "April",
        "05": "Mai",
        "06": "Juni",
        "07": "Juli",
        "08": "August",
        "09": "September",
        "10": "Oktober",
        "11": "November",
        "12": "Dezember",
    }
    if len(value) >= 7:
        year, month = value.split("-", 1)
        month = month[:2]
        return f"{months.get(month, month)} {year}"
    return value


def age_in_years(first_start: str, reference_year: int | None = None) -> int:
    year = reference_year or date.today().year
    start_year = int(first_start[:4])
    return max(year - start_year, 0)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump_frontmatter(payload: Dict[str, Any]) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()


def split_frontmatter(markdown_text: str) -> tuple[Dict[str, Any], str]:
    if not markdown_text.startswith("---\n"):
        return {}, markdown_text
    _, rest = markdown_text.split("---\n", 1)
    raw_frontmatter, body = rest.split("\n---\n", 1)
    return yaml.safe_load(raw_frontmatter) or {}, body


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = "".join(replacements.get(char, char) for char in value)
    return escaped.replace("\n", " ")


def truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    trimmed = value[: limit - 1].rsplit(" ", 1)[0]
    return f"{trimmed}..."


def make_run_id(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y%m%d-%H%M%S")
