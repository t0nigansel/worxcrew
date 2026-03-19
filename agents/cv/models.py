from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


JsonDict = Dict[str, Any]


@dataclass
class SourceBundle:
    data_dir: Path
    profile: JsonDict
    projects: List[JsonDict]
    certifications: List[JsonDict]
    portrait_path: Path


@dataclass
class JobAnalysis:
    title: str
    summary: str
    keywords: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    raw_text: str = ""
    language: str = "de"
    tone: str = "direct"
    variant: Optional[str] = None


@dataclass
class EvidenceSelection:
    selected_project_ids: List[str]
    selected_certification_ids: List[str]
    selected_experience_ids: List[str]
    selected_clients: List[str]
    technology_groups: List[JsonDict]
    certification_groups: List[JsonDict]
    project_scores: Dict[str, float]
    certification_scores: Dict[str, float]


@dataclass
class CVContent:
    frontmatter: JsonDict
    body: JsonDict
    markdown: str


@dataclass
class ValidationReport:
    passed: bool
    corrections: List[str] = field(default_factory=list)
    markdown_path: Optional[Path] = None
